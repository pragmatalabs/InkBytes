"""spaCy NER pre-pass (Curator ADR-0032, item 2).

A language-routed, deterministic NER pass that runs BEFORE enrich and hands the
LLM a set of typed `MUST_COVER` entities, so it can't silently under-extract the
principal people / organisations / places. Unlike the legacy Entopics stack this
is **multilingual** (spaCy ships `es_*` / `xx_*` models), closing the EN-only gap.

Design mirrors the triage gate (ADR-0030):
- **Gated** behind `cfg.ner.enabled` — a no-op (`extract → []`) when off.
- **Fail-OPEN** — a missing model, a load failure, or a per-doc timeout returns
  `[]`, and enrich proceeds LLM-only. The pass must never block the pipeline.
- **Bounded + off-loop** — spaCy is synchronous and CPU-heavy, so each call runs
  in a worker thread (`asyncio.to_thread`) and the caller bounds concurrency with
  a semaphore (the `_embed_sem` lesson), so N in-flight articles don't saturate
  the shared box.

Scope notes (from the validated POC, ADR-0032):
- spaCy's models are *high-recall, noisy* — the entities are hints, not ground
  truth; the enrich prompt is told it may correct a type or drop a false
  positive. We keep only the MUST_COVER types and the most frequent surface
  forms per type.
- EVENT stays the LLM's job — spaCy rarely tags the central happening — so we
  don't try to manufacture one here.
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass

from contracts.article_v1 import ArticleV1
from core.config import NerCfg

logger = logging.getLogger(__name__)

# spaCy entity labels → InkBytes entity types. EN models use OntoNotes
# (PERSON/ORG/GPE/LOC/FAC/EVENT…); ES/multilingual use CoNLL (PER/ORG/LOC/MISC).
# Anything not mapped here (DATE, CARDINAL, MISC, NORP, …) is dropped as noise.
_LABEL_MAP: dict[str, str] = {
    "PERSON": "PERSON", "PER": "PERSON",
    "ORG": "ORG",
    "GPE": "LOC", "LOC": "LOC", "FAC": "LOC",
    "EVENT": "EVENT",
}
# Types we surface as MUST_COVER. EVENT is intentionally excluded — spaCy rarely
# tags the central happening, and forcing its sparse hits would mislead the LLM.
_MUST_COVER_TYPES = ("PERSON", "ORG", "LOC")


@dataclass(frozen=True)
class NerEntity:
    name: str
    type: str  # one of _MUST_COVER_TYPES


class NerPrepass:
    name = "ner_prepass"

    def __init__(self, cfg: NerCfg) -> None:
        self.cfg = cfg
        self._nlp: dict[str, object] = {}     # lang → loaded pipeline (lazy)
        self._unavailable: set[str] = set()    # langs whose model failed to load
        if cfg.enabled:
            logger.info(
                "NerPrepass enabled (models=%s, max/type=%d, conc=%d) — "
                "lazy-loaded per language on first use",
                cfg.models, cfg.max_entities_per_type, cfg.max_concurrent,
            )

    # ── model loading ──────────────────────────────────────────────────────
    def _get_pipeline(self, lang: str):
        """Return the loaded spaCy pipeline for *lang*, or None (fail-open).

        Lazy + cached: a language's ~50MB–1GB model is only paid for the first
        time an article of that language appears, and a load failure is recorded
        so we don't retry (and log) on every subsequent article.
        """
        if lang in self._nlp:
            return self._nlp[lang]
        if lang in self._unavailable:
            return None
        model_name = self.cfg.models.get(lang)
        if not model_name:
            self._unavailable.add(lang)  # unsupported language → LLM-only
            return None
        try:
            import spacy  # imported here so a spaCy-less env still boots
            # Only the NER component is needed — disable the rest for speed/memory.
            nlp = spacy.load(model_name, disable=["lemmatizer", "tagger", "parser"])
            self._nlp[lang] = nlp
            logger.info("NerPrepass loaded %s for lang=%s", model_name, lang)
            return nlp
        except Exception as e:  # model not installed / import error
            logger.warning(
                "NerPrepass: model '%s' unavailable for lang=%s — failing open "
                "(LLM-only for this language): %s", model_name, lang, e,
            )
            self._unavailable.add(lang)
            return None

    # ── extraction ─────────────────────────────────────────────────────────
    def _run_sync(self, nlp, text: str) -> list[NerEntity]:
        """Synchronous spaCy call + normalization. Runs in a worker thread."""
        doc = nlp(text)
        # Count surface forms per type so we can keep the most frequent (and
        # dedupe case/whitespace variants).
        buckets: dict[str, Counter] = {t: Counter() for t in _MUST_COVER_TYPES}
        for ent in doc.ents:
            mapped = _LABEL_MAP.get(ent.label_)
            if mapped not in _MUST_COVER_TYPES:
                continue
            name = ent.text.strip()
            if len(name) < 2 or len(name) > 80:
                continue
            buckets[mapped][name] += 1
        out: list[NerEntity] = []
        for t in _MUST_COVER_TYPES:
            for name, _count in buckets[t].most_common(self.cfg.max_entities_per_type):
                out.append(NerEntity(name=name, type=t))
        return out

    async def extract(self, article: ArticleV1) -> list[NerEntity]:
        """Typed MUST_COVER entities for *article*, or [] (gated / fail-open)."""
        if not self.cfg.enabled:
            return []
        nlp = self._get_pipeline((article.language or "").lower())
        if nlp is None:
            return []
        text = f"{article.title}\n\n{article.text or ''}"[: self.cfg.max_chars]
        if not text.strip():
            return []
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._run_sync, nlp, text),
                timeout=self.cfg.timeout_s,
            )
        except Exception as e:  # timeout or any spaCy runtime error
            logger.warning(
                "NER pre-pass error for %s — failing open (LLM-only): %s",
                article.id, e,
            )
            return []


def format_must_cover(entities: list[NerEntity]) -> str:
    """Render entities as a compact `TYPE: a, b, c` block for the enrich prompt.

    Shared by the live pipeline and the dry-run path so they inject identically.
    Returns "" when there's nothing to add.
    """
    if not entities:
        return ""
    by_type: dict[str, list[str]] = {}
    for e in entities:
        by_type.setdefault(e.type, []).append(e.name)
    return "\n".join(f"{t}: {', '.join(names)}" for t, names in by_type.items())
