"""Stylized AI hero covers for Outlook columns (ADR-0012).

OpenAI `gpt-image-1-mini` turns a column's theme + headline into a conceptual,
brand-consistent editorial illustration (WebP, ~50 KB). One image per
(theme, edition_date), language-neutral, cached in Spaces.

Deliberately for OPINION columns only, and prompted to be abstract/illustrative —
NO text, NO real people, NO photorealism — so a cover can never be mistaken for a
documentary photo of a real event (the news-integrity + legal guardrail lives in
the prompt, and the exact prompt is stored per row for audit).

Remote API call only — no local compute — so it runs fine in the droplet batch
(unlike Piper). Best-effort + cost-capped by the caller.
"""
from __future__ import annotations

import base64
import logging

from core.config import CoversCfg

logger = logging.getLogger(__name__)

# Theme → palette cue for the prompt (a colour word steers the model better than a
# hex). Mirrors the Reader's per-category accents closely enough to feel of-a-piece.
_THEME_ACCENT = {
    "politics": "crimson red", "business": "deep blue", "technology": "electric violet",
    "sports": "emerald green", "health": "teal", "environment": "forest green",
    "culture": "warm amber", "world": "indigo", "science": "cyan",
    "entertainment": "magenta", "crime": "slate grey", "education": "bright orange",
    "lifestyle": "rose pink", "religion": "antique gold", "disaster": "burnt orange",
}
_DEFAULT_ACCENT = "deep indigo"


class Covers:
    def __init__(self, cfg: CoversCfg, prompt_template: str) -> None:
        self.cfg = cfg
        self._template = prompt_template
        self._client = None  # lazy OpenAI client

    def available(self) -> bool:
        if not self.cfg.enabled:
            return False
        if not self.cfg.api_key:
            logger.info("covers disabled — no OpenAI API key")
            return False
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.cfg.api_key)
            except Exception as e:  # noqa: BLE001 — degrade cleanly
                logger.warning("covers unavailable: OpenAI SDK import/init failed: %s", e)
                return False
        return True

    def build_prompt(self, theme: str, headline: str) -> str:
        accent = _THEME_ACCENT.get(theme, _DEFAULT_ACCENT)
        return (self._template
                .replace("{{theme}}", theme)
                .replace("{{headline}}", (headline or "").strip())
                .replace("{{accent}}", accent))

    def generate(self, theme: str, headline: str) -> tuple[bytes, str]:
        """theme + headline → (WebP bytes, prompt used). Blocking (remote API); the
        caller runs it off the event loop. Raises on failure (caller wraps it)."""
        prompt = self.build_prompt(theme, headline)
        resp = self._client.images.generate(   # type: ignore[union-attr]
            model=self.cfg.model, prompt=prompt, size=self.cfg.size,
            quality=self.cfg.quality, output_format=self.cfg.output_format,
            output_compression=self.cfg.compression, n=1)
        return base64.b64decode(resp.data[0].b64_json), prompt
