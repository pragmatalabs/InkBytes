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

    def __init__(self, cfg: TriageCfg) -> None:
        self.cfg = cfg
        self._client = None
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
            return TriageVerdict(verdict, reason)
        except Exception as e:
            # Fail OPEN — never drop because the local model errored/timed out.
            logger.warning("TRIAGE error for %s — failing open (keep): %s", art.id, e)
            return TriageVerdict("error", str(e)[:120])
