"""Salvaged IPTC-grounded news taxonomy (Curator ADR-0032, item 1).

Loads the two vendored artifacts under ``data/taxonomy/`` once at import:

- ``categories_33.json``        — Julian's 33-category ontology (DocTrainer, 2024).
- ``source_category_bridge.json`` — the 634→33 bridge unifying IPTC Media Topics
  (the Reuters/AP wire standard) + HuffPost + 20-Newsgroups source labels.

The pipeline enriches with an LLM, so widening the taxonomy is a prompt +
reference-data change, not a classifier retrain. This module is the single
source for:

- ``CATEGORIES_33`` — the canonical category strings (prompt list == DB values).
- ``normalize_category()`` — map the LLM's free-text pick to a canonical 33 label
  (case-insensitive), or ``None`` if it doesn't match. Keeps ``instructor`` from
  re-prompting on a near-miss while still constraining what lands in the DB.
- ``suggest_category()`` — deterministic bridge lookup from Messor's outlet
  section / tags → a canonical 33 label. Used both as a *strong hint* injected
  into the enrich prompt and as the *fallback* when the model abstains.

Fail-soft by design: a missing/corrupt artifact logs once and degrades to empty
lookups (the pipeline keeps running on the LLM alone) rather than crashing.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# services/taxonomy.py → apps/curator → data/taxonomy/ (mirrors LlmService.load_prompt).
_TAX_DIR = Path(__file__).resolve().parent.parent / "data" / "taxonomy"


def _load() -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Return (canonical_categories, canon_by_lower, bridge_by_lower)."""
    try:
        cats_raw = json.loads((_TAX_DIR / "categories_33.json").read_text())
        bridge_raw = json.loads((_TAX_DIR / "source_category_bridge.json").read_text())
    except (OSError, ValueError) as exc:  # missing file / bad JSON
        logger.warning(
            "taxonomy artifacts unavailable (%s) — category widening disabled, "
            "pipeline continues on the LLM alone", exc,
        )
        return [], {}, {}

    categories = list(cats_raw.get("categories", {}).values())
    canon_by_lower = {c.lower(): c for c in categories}
    # Bridge source labels arrive in mixed case (IPTC lowercase, HuffPost UPPER,
    # 20NG); fold to lowercase so the lookup is case-insensitive. Values are
    # already canonical 33-labels in the artifact.
    bridge_by_lower = {k.lower(): v for k, v in bridge_raw.get("mappings", {}).items()}
    return categories, canon_by_lower, bridge_by_lower


CATEGORIES_33, _CANON_BY_LOWER, _BRIDGE_BY_LOWER = _load()


def normalize_category(value: str | None) -> str | None:
    """Map a free-text category to its canonical 33-set label, else ``None``.

    Case-insensitive exact match — the LLM is asked to echo a label from the
    supplied list, so this mostly corrects casing/whitespace and rejects
    anything off-ontology (which then falls through to the bridge).
    """
    if not value:
        return None
    return _CANON_BY_LOWER.get(value.strip().lower())


def suggest_category(section: str | None, tags: list[str] | None) -> str | None:
    """Deterministic 33-cat suggestion from Messor's outlet section / tags.

    Tries the primary section first, then each tag in order; returns the first
    that resolves through the 634→33 bridge. ``None`` when nothing maps.
    """
    candidates: list[str] = []
    if section:
        candidates.append(section)
    if tags:
        candidates.extend(tags)
    for cand in candidates:
        hit = _BRIDGE_BY_LOWER.get(cand.strip().lower())
        if hit:
            return hit
    return None
