"""Editorial orchestrator (ADR-0008).

For each theme × language on a given edition date: gather the day's published
events for that theme, gate on a minimum count (don't pad thin days), render the
persona prompt, generate the column, parse headline/body, and store it with full
generation provenance (the Phase-2 SLM training pair).
"""
from __future__ import annotations

import logging
import uuid
from datetime import date as date_cls
from pathlib import Path

from core.config import Config
from personas import PERSONAS, persona_for
from services.db import Database
from services.llm import Llm

logger = logging.getLogger(__name__)
_APP_DIR = Path(__file__).resolve().parent.parent
_SYSTEM = ("Eres un columnista editorial profesional de un medio de pago, sin "
           "publicidad. Sigue las instrucciones al pie de la letra.")
_LANG_NAMES = {"es": "español", "en": "English"}


class Application:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db = Database(cfg.database)
        self.llm = Llm(cfg.llm)
        self._template = (_APP_DIR / cfg.editorial.persona_dir / "editorial.md").read_text("utf-8")

    async def start(self) -> None:
        await self.db.connect()

    async def close(self) -> None:
        await self.db.close()

    def _render(self, theme, name, voice, language, edition_date, events) -> str:
        ev = "\n".join(
            f"[{i + 1}] {e['headline']}\n    {(e['excerpt'] or '').strip()}"
            for i, e in enumerate(events))
        return (self._template
                .replace("{{persona_name}}", name)
                .replace("{{voice}}", voice)
                .replace("{{theme}}", theme)
                .replace("{{language_name}}", _LANG_NAMES.get(language, language))
                .replace("{{date}}", str(edition_date))
                .replace("{{events}}", ev))

    @staticmethod
    def _split(text: str) -> tuple[str, str]:
        """First non-empty line = headline; the rest = body."""
        lines = [ln for ln in text.strip().splitlines()]
        i = next((k for k, ln in enumerate(lines) if ln.strip()), 0)
        headline = lines[i].strip().lstrip("#").strip().strip('"').removeprefix("Titular:").strip()
        body = "\n".join(lines[i + 1:]).strip()
        return headline, (body or text.strip())

    async def generate_theme(self, theme: str, language: str,
                             edition_date: date_cls, dry_run: bool = False) -> str | None:
        key, name, voice = persona_for(theme)
        events = await self.db.fetch_theme_events(
            theme, self.cfg.editorial.window_hours, self.cfg.editorial.max_events)
        if len(events) < self.cfg.editorial.min_events:
            logger.info("EDITORIAL skip %s/%s — %d events (< min %d)",
                        theme, language, len(events), self.cfg.editorial.min_events)
            return None

        prompt = self._render(theme, name, voice, language, edition_date, events)
        text = await self.llm.complete(system=_SYSTEM, user=prompt)
        headline, body = self._split(text)
        event_ids = [e["event_id"] for e in events]
        input_context = [{"event_id": e["event_id"], "headline": e["headline"],
                          "excerpt": e["excerpt"]} for e in events]

        if dry_run:
            print(f"\n===== {name} ({theme}/{language}) · {len(events)} events · {self.llm.label} =====")
            print(headline + "\n")
            print(body[:600] + ("…" if len(body) > 600 else ""))
            return headline

        await self.db.write_editorial(
            ed_id=str(uuid.uuid4()), theme=theme, language=language,
            edition_date=edition_date, persona=key, headline=headline, body_md=body,
            event_ids=event_ids, model=self.llm.label, input_context=input_context,
            prompt=prompt)
        logger.info("EDITORIAL %s/%s [%s] %d events -> %r",
                    theme, language, self.llm.label, len(events), headline)
        return headline

    async def generate_all(self, edition_date: date_cls, dry_run: bool = False) -> int:
        n = 0
        for language in self.cfg.editorial.languages:
            for theme in PERSONAS:
                if await self.generate_theme(theme, language, edition_date, dry_run):
                    n += 1
        logger.info("EDITORIAL batch done: %d columns for %s", n, edition_date)
        return n
