"""Pre-enrich triage gate (ADR-0030).

A small LOCAL model (Hostinger Ollama, OpenAI-compatible /v1) classifies each
to-be-enriched article as keep | junk from its title + lede, so obvious filler
is dropped before the paid DeepSeek enrich call. Stateless, short output — the
one shape the CPU-only box can run across full article volume.

Fail-OPEN: any error, timeout, or unparseable reply returns `keep`. The gate
must never drop a real article because the local model hiccuped.

Near-duplicate detection is deliberately NOT here — that needs corpus context
and is already handled by the content-hash fast-path (ADR-0015/0018) and
embedding clustering. This gate only judges single-article filler.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from contracts.article_v1 import ArticleV1
from core.config import TriageCfg
from services.llm_service import LlmService

logger = logging.getLogger(__name__)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class TriageVerdict:
    verdict: str  # "keep" | "junk" | "error"
    reason: str

    @property
    def drop(self) -> bool:
        return self.verdict == "junk"


class TriageSkill:
    name = "triage"

    # Rolling shadow counters — every _STATS_EVERY verdicts we log a summary so
    # the keep/junk/error mix (and thus the drop-rate denominator) is observable
    # without logging every individual keep.
    _STATS_EVERY = 50

    def __init__(self, cfg: TriageCfg) -> None:
        self.cfg = cfg
        self._client = None
        self._n_keep = 0
        self._n_junk = 0
        self._n_error = 0
        if cfg.enabled:
            from openai import AsyncOpenAI
            base = cfg.base_url or "http://localhost:11434/v1"
            # Ollama ignores the key but the SDK requires a non-empty string.
            self._client = AsyncOpenAI(api_key="ollama", base_url=base)
            logger.info(
                "TriageSkill enabled (model=%s, base=%s, shadow=%s)",
                cfg.model, base, cfg.shadow,
            )
        self._system = LlmService.load_prompt("triage")

    async def run(self, art: ArticleV1) -> TriageVerdict:
        if not self._client:
            return TriageVerdict("keep", "disabled")
        lede = (art.text or "")[:600]
        user = (
            f"OUTLET: {art.outlet.name}\n"
            f"LANG: {art.language}\n"
            f"TITLE: {art.title}\n"
            f"LEDE: {lede}"
        )
        try:
            resp = await self._client.chat.completions.create(
                model=self.cfg.model,
                messages=[
                    {"role": "system", "content": self._system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                max_tokens=120,
                timeout=self.cfg.timeout_s,
            )
            raw = (resp.choices[0].message.content or "").strip()
            m = _JSON_RE.search(raw)
            data = json.loads(m.group(0)) if m else {}
            verdict = str(data.get("verdict", "keep")).lower().strip()
            if verdict not in ("keep", "junk"):
                verdict = "keep"
            reason = str(data.get("reason", ""))[:160]
            self._tally(verdict)
            return TriageVerdict(verdict, reason)
        except Exception as e:
            # Fail OPEN — never drop because the local model errored/timed out.
            logger.warning("TRIAGE error for %s — failing open (keep): %s", art.id, e)
            self._tally("error")
            return TriageVerdict("error", str(e)[:120])

    def _tally(self, verdict: str) -> None:
        if verdict == "junk":
            self._n_junk += 1
        elif verdict == "error":
            self._n_error += 1
        else:
            self._n_keep += 1
        total = self._n_keep + self._n_junk + self._n_error
        if total % self._STATS_EVERY == 0:
            judged = self._n_keep + self._n_junk  # excludes fail-open errors
            drop_pct = (100.0 * self._n_junk / judged) if judged else 0.0
            logger.info(
                "TRIAGE stats: %d judged | keep=%d junk=%d (%.1f%% drop) | errors=%d (fail-open)",
                judged, self._n_keep, self._n_junk, drop_pct, self._n_error,
            )
