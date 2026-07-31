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
from services.covers import Covers
from services.db import Database
from services.llm import Llm
from services.storage import SpacesStorage
from services.tts import Tts, to_speakable

logger = logging.getLogger(__name__)
_APP_DIR = Path(__file__).resolve().parent.parent
# Global Editorial Policy (ADR-0010) is a hard system preamble on every column.
# The system prompt is LANGUAGE-AWARE: a Spanish-framed system that opens with
# "Eres un columnista…" primes Spanish output, and deepseek-v4-flash then returns
# empty/degraded content when the body is asked for in English (12/14 EN columns
# came back blank on 2026-07-30). Give EN columns an English frame + an explicit
# "write in English" directive; the (Spanish) policy rides along as guidance.
_POLICY = global_policy()
_SYSTEM_BY_LANG = {
    "es": ("Eres un columnista editorial profesional de un medio de pago, sin "
           "publicidad. Sigue las instrucciones al pie de la letra. Escribe SIEMPRE "
           "en español.\n\nPOLÍTICA EDITORIAL GLOBAL (obligatoria):\n" + _POLICY),
    "en": ("You are a professional editorial columnist for a paid, ad-free news "
           "outlet. Follow the instructions to the letter, and write the ENTIRE "
           "column — headline and body — in natural, native English.\n\nGLOBAL "
           "EDITORIAL POLICY (mandatory — apply it fully; it is written in Spanish, "
           "but your column MUST be in English):\n" + _POLICY),
}


def _system_for(language: str) -> str:
    return _SYSTEM_BY_LANG.get(language, _SYSTEM_BY_LANG["es"])


_LANG_NAMES = {"es": "español", "en": "English"}
# Floor for a publishable column body. A real column is ~2–4 k chars (a 450–600
# word piece); anything under this is an empty/truncated LLM hiccup — skip it
# rather than publish a broken stub (e.g. the 62-char crime/es of 2026-07-30).
_MIN_BODY_CHARS = 300


class Application:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db = Database(cfg.database)
        self.llm = Llm(cfg.llm)
        self.tts = Tts(cfg.tts)
        self.storage = SpacesStorage(cfg.spaces)
        self._template = (_APP_DIR / cfg.editorial.persona_dir / "editorial.md").read_text("utf-8")
        _cover_tpl = (_APP_DIR / cfg.editorial.persona_dir / "cover.md").read_text("utf-8")
        self.covers = Covers(cfg.covers, _cover_tpl)

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
        """First non-empty line = headline; the rest = body. An empty /
        whitespace-only LLM response yields ("", "") instead of an IndexError —
        the caller drops thin output rather than crashing the whole batch."""
        lines = text.strip().splitlines()
        i = next((k for k, ln in enumerate(lines) if ln.strip()), None)
        if i is None:
            return "", ""
        headline = lines[i].strip().lstrip("#").strip().strip('"').removeprefix("Titular:").strip()
        body = "\n".join(lines[i + 1:]).strip()
        return headline, (body or text.strip())

    async def generate_theme(self, theme: str, language: str,
                             edition_date: date_cls, dry_run: bool = False) -> dict | None:
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
        text = await self.llm.complete(system=_system_for(language), user=prompt)
        headline, body = self._split(text)
        # Drop empty/truncated generations — a blank or one-sentence stub must
        # not be published as a column (and must not crash the batch). The next
        # daily run or a manual re-run fills the gap.
        if not headline or len(body) < _MIN_BODY_CHARS:
            logger.warning("EDITORIAL skip %s/%s — thin output (headline=%r, %d body chars)",
                           theme, language, headline[:50], len(body))
            return None
        event_ids = [e["event_id"] for e in events]
        # provenance for the Phase-2 SLM: the method label + the input events
        input_context = {
            "method_persona": mp.role,
            "events": [{"event_id": e["event_id"], "headline": e["headline"],
                        "excerpt": e["excerpt"]} for e in events],
        }

        payload = {"theme": theme, "language": language, "edition_date": edition_date,
                   "headline": headline, "body_md": body}

        if dry_run:
            print(f"\n===== {name} ({theme}/{language}) · method={mp.role!r} · "
                  f"{len(events)} events · {self.llm.label} =====")
            print(headline + "\n")
            print(body[:600] + ("…" if len(body) > 600 else ""))
            return payload

        await self.db.write_editorial(
            ed_id=str(uuid.uuid4()), theme=theme, language=language,
            edition_date=edition_date, persona=key, headline=headline, body_md=body,
            event_ids=event_ids, model=self.llm.label, input_context=input_context,
            prompt=prompt)
        logger.info("EDITORIAL %s/%s [%s] %d events -> %r",
                    theme, language, self.llm.label, len(events), headline)
        # Audio is synthesized in a concurrent batch AFTER the text loop (not inline)
        # so it parallelizes — see generate_all / _synthesize_batch (ADR-0011).
        return payload

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
            # synth is a blocking call (network or subprocess) — keep it off the loop.
            # Returns the actual voice used (the service reports it — Kokoro randomizes).
            mp3, voice_label = await asyncio.to_thread(self.tts.synthesize, text, language)
            key = f"{self.cfg.tts.key_prefix}/{edition_date}/{theme}-{language}.mp3"
            url = await asyncio.to_thread(self.storage.upload_bytes, mp3, key)
            await self.db.set_editorial_audio(
                theme=theme, language=language, edition_date=edition_date,
                audio_url=url, audio_voice=voice_label)
            logger.info("AUDIO %s/%s [%s] %d KB -> %s",
                        theme, language, voice_label, len(mp3) // 1024, url)
            return True
        except Exception as e:  # noqa: BLE001 — audio is best-effort
            logger.warning("audio synth failed for %s/%s: %s", theme, language, e)
            return False

    async def _synthesize_batch(self, items: list[dict]) -> int:
        """Synthesize+upload audio for a list of editorials CONCURRENTLY, bounded by
        tts.concurrency (ADR-0011). On the shared droplet the batch is CPU-capped by
        run-editorial.sh (--cpus); concurrency>1 fills that slice without oversubscribing
        the box. Best-effort per item — one failure never sinks the batch."""
        if not (self.cfg.tts.enabled and self.storage.configured):
            logger.info("audio batch skipped — TTS disabled or Spaces not configured")
            return 0
        sem = asyncio.Semaphore(max(1, self.cfg.tts.concurrency))

        async def _one(it: dict) -> bool:
            async with sem:
                return await self._synthesize_audio(
                    it["theme"], it["language"], it["edition_date"],
                    it["headline"], it["body_md"])

        results = await asyncio.gather(*[_one(it) for it in items])
        done = sum(1 for r in results if r)
        logger.info("audio batch: %d/%d synthesized (concurrency %d)",
                    done, len(items), self.cfg.tts.concurrency)
        return done

    # ── Covers (ADR-0012) — stylized AI hero per theme/day ──────────────────────

    async def _generate_cover(self, theme: str, edition_date, headline: str) -> bool:
        """gpt-image-1-mini → WebP → Spaces → editorials.cover_url (all langs).
        Best-effort — a failure never blocks the batch."""
        if not (self.covers.available() and self.storage.configured):
            return False
        try:
            img, prompt = await asyncio.to_thread(self.covers.generate, theme, headline)
            key = f"{self.cfg.covers.key_prefix}/{edition_date}/{theme}.webp"
            url = await asyncio.to_thread(self.storage.upload_bytes, img, key, "image/webp")
            await self.db.set_editorial_cover(
                theme=theme, edition_date=edition_date, cover_url=url, cover_prompt=prompt)
            logger.info("COVER %s/%s %d KB -> %s", theme, edition_date, len(img) // 1024, url)
            return True
        except Exception as e:  # noqa: BLE001 — covers are best-effort
            logger.warning("cover gen failed for %s/%s: %s", theme, edition_date, e)
            return False

    async def _cover_batch(self, items: list[dict]) -> int:
        """Generate covers for a list of unique {theme, edition_date, headline},
        enforcing the monthly cost cap (ADR-0012). Sequential — image gen is a remote
        API call, and sequential keeps the spend accounting simple."""
        if not (self.covers.available() and self.storage.configured):
            logger.info("cover batch skipped — covers disabled or Spaces not configured")
            return 0
        unit, cap = self.cfg.covers.unit_cost_usd, self.cfg.covers.monthly_cap_usd
        spent = (await self.db.count_covers_this_month()) * unit
        budget = cap - spent
        max_new = int(budget // unit) if unit > 0 else len(items)
        if max_new <= 0:
            logger.warning("cover cap reached: $%.2f of $%.2f this month — skipping %d",
                           spent, cap, len(items))
            return 0
        if max_new < len(items):
            logger.warning("cover cap: budget for %d of %d covers this run ($%.2f/$%.2f spent)",
                           max_new, len(items), spent, cap)
        done = 0
        for it in items:
            if done >= max_new:
                logger.warning("cover cap hit mid-run — stopped after %d (capped)", done)
                break
            if await self._generate_cover(it["theme"], it["edition_date"], it["headline"]):
                done += 1
        logger.info("cover batch: %d generated (cap $%.2f/mo, ~$%.3f/img)", done, cap, unit)
        return done

    async def generate_all(self, edition_date: date_cls, dry_run: bool = False) -> int:
        written: list[dict] = []
        for language in self.cfg.editorial.languages:
            for theme in PERSONAS:
                try:
                    r = await self.generate_theme(theme, language, edition_date, dry_run)
                except Exception as e:  # noqa: BLE001 — one bad theme must NEVER abort the batch
                    logger.exception("EDITORIAL failed %s/%s (%s) — continuing", theme, language, e)
                    continue
                if r:
                    written.append(r)
        logger.info("EDITORIAL batch done: %d columns for %s", len(written), edition_date)
        if written and not dry_run:
            await self._synthesize_batch(written)   # voice today's columns (concurrent)
            await self._cover_batch(self._unique_theme_days(written))  # one cover/theme/day
            await self._notify_outlook_ready()
        return len(written)

    @staticmethod
    def _unique_theme_days(written: list[dict]) -> list[dict]:
        """Collapse the written columns to one {theme, edition_date, headline} per
        theme/day for cover generation — preferring the English headline for the
        image prompt (covers are language-neutral)."""
        by_key: dict[tuple, dict] = {}
        for it in written:
            k = (it["theme"], it["edition_date"])
            if k not in by_key or it["language"] == "en":
                by_key[k] = {"theme": it["theme"], "edition_date": it["edition_date"],
                             "headline": it["headline"]}
        return list(by_key.values())

    async def synthesize_missing(self, limit: int = 500) -> int:
        """Backfill audio for existing editorials that have none yet (ADR-0011) —
        idempotent, so it's the 'generate once' guarantee for rows written before
        TTS existed. Returns the count synthesized."""
        if not (self.cfg.tts.enabled and self.storage.configured):
            logger.info("synthesize-missing: TTS disabled or Spaces not configured — nothing to do")
            return 0
        rows = await self.db.fetch_editorials_missing_audio(
            limit, self.cfg.editorial.languages)
        logger.info("synthesize-missing: %d editorial(s) without audio", len(rows))
        return await self._synthesize_batch(rows)

    async def cover_missing(self, limit: int = 200) -> int:
        """Backfill covers for existing theme/days that have none yet (ADR-0012) —
        idempotent + monthly-cost-capped. Returns the count generated."""
        if not (self.covers.available() and self.storage.configured):
            logger.info("cover-missing: covers disabled or Spaces not configured — nothing to do")
            return 0
        rows = await self.db.fetch_theme_days_missing_cover(limit)
        logger.info("cover-missing: %d theme/day(s) without a cover", len(rows))
        return await self._cover_batch(rows)

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
