#!/usr/bin/env python
"""Test the salvaged taxonomy wiring — themes 8→15 + 33-cat bridge (ADR-0032 item 1).

Pure-Python, no API keys / DB / broker needed. Verifies:
  1. The 8 legacy themes are a strict subset of the new 15 (backward-compatible).
  2. EnrichmentResult validates the new themes + a 33-cat + a null category.
  3. The taxonomy loader returns exactly 33 categories.
  4. normalize_category() folds case and rejects off-ontology values.
  5. suggest_category() resolves IPTC / HuffPost / 20NG labels through the bridge.
  6. Drift guard: every category named in prompts/enrich.md exists in the 33-set,
     and _VALID_THEMES matches the contract Theme literal.

Run:
  cd Curator/apps/curator && .venv/bin/python scripts/test_taxonomy_widen.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import get_args

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from contracts.enriched_v1 import EnrichmentResult, Theme  # noqa: E402
from core.api_server import _VALID_THEMES  # noqa: E402
from services import taxonomy  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"{'✓' if cond else '✗'} {msg}")
    if not cond:
        _failures.append(msg)


# 1. Legacy themes ⊂ new themes
LEGACY_8 = {"politics", "business", "technology", "sports",
            "health", "environment", "culture", "world"}
themes = set(get_args(Theme))
check(LEGACY_8 <= themes, f"8 legacy themes ⊆ 15 new themes (new={len(themes)})")
check(len(themes) == 15, "Theme literal has exactly 15 values")

# 2. Contract validates new theme + 33-cat + null category
r1 = EnrichmentResult(theme="science", topic="X", summary_50w="s",
                      sentiment="neutral", factuality=0.5,
                      article_category="Science & Technology")
check(r1.article_category == "Science & Technology", "EnrichmentResult accepts a 33-cat")
r2 = EnrichmentResult(theme="disaster", topic="X", summary_50w="s",
                      sentiment="neutral", factuality=0.5)
check(r2.article_category is None, "article_category defaults to None (abstain)")
try:
    EnrichmentResult(theme="not-a-theme", topic="X", summary_50w="s",
                     sentiment="neutral", factuality=0.5)
    check(False, "rejects an invalid theme")
except Exception:
    check(True, "rejects an invalid theme")

# 3. Loader returns 33
check(len(taxonomy.CATEGORIES_33) == 33, f"loader returns 33 categories (got {len(taxonomy.CATEGORIES_33)})")

# 4. normalize_category — case-fold + reject off-ontology
check(taxonomy.normalize_category("science & technology") == "Science & Technology",
      "normalize_category folds case")
check(taxonomy.normalize_category("  Sports ") == "Sports", "normalize_category trims")
check(taxonomy.normalize_category("Politics & Government") is None,
      "normalize_category rejects off-ontology")
check(taxonomy.normalize_category(None) is None, "normalize_category(None) → None")

# 5. suggest_category — bridge across the three source vocabularies
check(taxonomy.suggest_category("economy, business and finance", None) == "Business & Economy",
      "bridge: IPTC 'economy, business and finance' → Business & Economy")
check(taxonomy.suggest_category("sport", None) == "Sports", "bridge: IPTC 'sport' → Sports")
check(taxonomy.suggest_category("TECH", None) == "Science & Technology",
      "bridge: HuffPost 'TECH' → Science & Technology")
check(taxonomy.suggest_category(None, ["unknownx", "CRIME"]) == "Crime & Justice",
      "bridge: falls through tags to 'CRIME' → Crime & Justice")
check(taxonomy.suggest_category("no-such-section", None) is None,
      "bridge: unknown section → None")

# 6a. Drift guard — prompt categories ⊆ 33-set
prompt = (ROOT / "prompts" / "enrich.md").read_text()
block = prompt.split("article_category", 1)[1].split("Do not invent facts", 1)[0]
# bullet lines list categories separated by · ; pull tokens that look like labels
named = {c.strip() for c in re.split(r"[·\n]", block)
         if c.strip() and c.strip()[0].isupper() and len(c.strip()) < 40}
canon = set(taxonomy.CATEGORIES_33)
unknown = {c for c in named if c in {x for x in named if any(ch in c for ch in "&.")} and c not in canon}
# strict: every dotted/&-bearing label named in the prompt must be canonical
stray = {c for c in named if c not in canon and re.search(r"[&.]", c)}
check(not stray, f"all prompt categories exist in the 33-set (stray={sorted(stray)})")

# 6b. _VALID_THEMES == contract themes
check(set(_VALID_THEMES) == themes, "_VALID_THEMES matches the contract Theme literal")

print()
if _failures:
    print(f"FAILED: {len(_failures)} check(s)")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)
print("ALL PASSED")
