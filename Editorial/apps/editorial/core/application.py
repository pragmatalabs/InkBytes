"""Editorial orchestrator (ADR-0008).

For each theme × language on a given edition date: gather the day's published
events for that theme, gate on a minimum count (don't pad thin days), render the
persona prompt, generate the column, parse headline/body, and store it with full
generation provenance (the Phase-2 SLM training pair).
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import date as date_cls
from pathlib import Path

from core.config import Config
from personas import PERSONAS, MethodPersona, global_policy, persona_for, roster_for
from services.db import Database
from services.llm import Llm
from services.storage import SpacesStorage
from services.tts import Tts, to_speakable

logger = logging.getLogger(__name__)
_APP_DIR = Path(__file__).resolve().parent.parent
# Global Editorial Policy (ADR-0010) is a hard system preamble on every column.
_SYSTEM = ("Eres un columnista editorial profesional de un medio de pago, sin "
           "publicidad. Sigue las instrucciones al pie de la letra.\n\n"
           "POLÍTICA EDITORIAL GLOBAL (obligatoria):\n" + global_policy())
_LANG_NAMES = {"es": "español", "en": "English"}


class Application:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db = Database(cfg.database)
        self.llm = Llm(cfg.llm)
        self.tts = Tts(cfg.tts)
        self.storage = SpacesStorage(cfg.spaces)
        self._template = (_APP_DIR / cfg.editorial.persona_dir / "editorial.md").read_text("utf-8")

    async def start(self) -> None:
        await self.db.connect()

    async def close(self) -> None:
        await self.db.close()

    def _render(self, theme, method_prompt, language, edition_date, events) -> str:
        ev = "\n".join(
            f"[{i + 1}] {e['headline']}\n    {(e['excerpt'] or '').strip()}"
            for i, e in enumerate(events))
        return (self._template
                .replace("{{method_prompt}}", method_prompt)
                .replace("{{theme}}", theme)
                .replace("{{language_name}}", _LANG_NAMES.get(language, language))
                .replace("{{date}}", str(edition_date))
                .replace("{{events}}", ev))

    async def _select_method(self, theme, roster: list[MethodPersona],
                             events, edition_date) -> int:
        """ADR-0010: pick the method-persona whose method fits the day's reporting
        problem (spec workflow §2). LLM routing; falls back to a daily rotation so
        a routing failure never blocks the column."""
        if len(roster) <= 1:
            return 0
        options = "\n".join(f"{i + 1}. {p.role} — {p.use_when}" for i, p in enumerate(roster))
        heads = "\n".join(f"- {e['headline']}" for e in events[:10])
        routing = (f"Editorial routing for the {theme} column. Choose the ONE "
                   f"reporting method that best fits today's stories.\n\n"
                   f"METHODS:\n{options}\n\nTODAY'S HEADLINES:\n{heads}\n\n"
                   f"Reply with ONLY the method number.")
        try:
            resp = await self.llm.complete(
                system="You route editorial assignments. Reply with a single number only.",
                user=routing)
            m = re.search(r"\d+", resp or "")
            if m:
                idx = int(m.group()) - 1
                if 0 <= idx < len(roster):
                    return idx
        except Exception as e:  # noqa: BLE001 — routing must never block generation
            logger.warning("persona routing failed for %s (%s); rotating", theme, e)
        return edition_date.toordinal() % len(roster)

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
        key, name, _voice = persona_for(theme)   # reader-facing identity (masthead)
        events = await self.db.fetch_theme_events(
            theme, self.cfg.editorial.window_hours, self.cfg.editorial.max_events)
        if len(events) < self.cfg.editorial.min_events:
            logger.info("EDITORIAL skip %s/%s — %d events (< min %d)",
                        theme, language, len(events), self.cfg.editorial.min_events)
            return None

        # ADR-0010: select the internal method-persona by the day's reporting problem
        roster = roster_for(theme)
        mp = roster[await self._select_method(theme, roster, events, edition_date)]

        prompt = self._render(theme, mp.ready_prompt, language, edition_date, events)
        text = await self.llm.complete(system=_SYSTEM, user=prompt)
        headline, body = self._split(text)
        event_ids = [e["event_id"] for e in events]
        # provenance for the Phase-2 SLM: the method label + the input events
        input_context = {
            "method_persona": mp.role,
            "events": [{"event_id": e["event_id"], "headline": e["headline"],
                        "excerpt": e["excerpt"]} for e in events],
        }

        if dry_run:
            print(f"\n===== {name} ({theme}/{language}) · method={mp.role!r} · "
                  f"{len(events)} events · {self.llm.label} =====")
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
        # Voice, generated once (ADR-0011). Best-effort — a TTS/upload failure
        # must never undo a written column.
        await self._synthesize_audio(theme, language, edition_date, headline, body)
        return headline

    async def _synthesize_audio(self, theme: str, language: str, edition_date,
                                headline: str, body_md: str) -> bool:
        """Piper → MP3 → Spaces → editorials.audio_url (ADR-0011). Returns True on
        success. Silently skips when TTS is disabled/unavailable or Spaces isn't
        configured; swallows and logs any error (best-effort, never blocks a batch)."""
        if not self.tts.available(language):
            return False
        if not self.storage.configured:
            logger.info("audio skip %s/%s — Spaces not configured", theme, language)
            return False
        try:
            text = to_speakable(headline, body_md)
            voice = self.tts.voice_id(language) or "unknown"
            # Piper + ffmpeg are blocking subprocesses — keep them off the loop.
            mp3 = await asyncio.to_thread(self.tts.synthesize, text, language)
            key = f"{self.cfg.tts.key_prefix}/{edition_date}/{theme}-{language}.mp3"
            url = await asyncio.to_thread(self.storage.upload_bytes, mp3, key)
            await self.db.set_editorial_audio(
                theme=theme, language=language, edition_date=edition_date,
                audio_url=url, audio_voice=f"piper/{voice}")
            logger.info("AUDIO %s/%s [%s] %d KB -> %s",
                        theme, language, voice, len(mp3) // 1024, url)
            return True
        except Exception as e:  # noqa: BLE001 — audio is best-effort
            logger.warning("audio synth failed for %s/%s: %s", theme, language, e)
            return False

    async def generate_all(self, edition_date: date_cls, dry_run: bool = False) -> int:
        n = 0
        for language in self.cfg.editorial.languages:
            for theme in PERSONAS:
                if await self.generate_theme(theme, language, edition_date, dry_run):
                    n += 1
        logger.info("EDITORIAL batch done: %d columns for %s", n, edition_date)
        if n > 0 and not dry_run:
            await self._notify_outlook_ready()
        return n

    async def synthesize_missing(self, limit: int = 500) -> int:
        """Backfill audio for existing editorials that have none yet (ADR-0011) —
        idempotent, so it's the 'generate once' guarantee for rows written before
        TTS existed. Returns the count synthesized."""
        if not (self.cfg.tts.enabled and self.storage.configured):
            logger.info("synthesize-missing: TTS disabled or Spaces not configured — nothing to do")
            return 0
        langs = self.cfg.editorial.languages
        rows = await self.db.fetch_editorials_missing_audio(limit, langs)
        logger.info("synthesize-missing: %d editorial(s) without audio", len(rows))
        done = 0
        for r in rows:
            if await self._synthesize_audio(
                    r["theme"], r["language"], r["edition_date"],
                    r["headline"], r["body_md"]):
                done += 1
        logger.info("synthesize-missing done: %d/%d synthesized", done, len(rows))
        return done

    @staticmethod
    async def _notify_outlook_ready() -> None:
        """Ping Curator's daily push broadcast (ADR-R-0012) after a real batch.
        Best-effort + token-guarded; a failure never affects generation. Env:
        CURATOR_INTERNAL_URL (default the internal API host) + PUSH_TRIGGER_SECRET."""
        import os
        import urllib.request

        secret = os.getenv("PUSH_TRIGGER_SECRET", "")
        if not secret:
            logger.info("push trigger skipped — PUSH_TRIGGER_SECRET not set")
            return
        base = os.getenv("CURATOR_INTERNAL_URL", "http://inkbytes-curator-api:8060")
        try:
            req = urllib.request.Request(
                f"{base}/push/broadcast-outlook", method="POST",
                headers={"X-Push-Token": secret, "Content-Length": "0"})
            import asyncio
            await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=10).read())
            logger.info("push broadcast triggered")
        except Exception as e:  # noqa: BLE001 — never let push break the batch
            logger.warning("push broadcast trigger failed: %s", e)
