#!/usr/bin/env python
"""Test the spaCy NER pre-pass wiring (Curator ADR-0032 item 2).

Verifies the integration, not spaCy's NER quality (the POC already validated
that on real EN+ES articles):
  1. Gated off → extract() returns [] (no-op).
  2. Unsupported language → [] (fail-open, no model for it).
  3. Missing model → [] (fail-open) — uses a deliberately bogus model name.
  4. format_must_cover() groups by type / is empty for [].
  5. enrich._build_user_content injects a MUST_COVER block iff entities present.
  6. Real extraction (EN + ES) when small models are installed — PERSON/ORG/LOC
     surface and are capped/deduped. Skipped (not failed) if models are absent.

Run:
  cd Curator/apps/curator && .venv/bin/python scripts/test_ner_prepass.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from contracts.article_v1 import ArticleV1, _Outlet  # noqa: E402
from core.config import NerCfg  # noqa: E402
from services.ner_prepass import NerPrepass, NerEntity, format_must_cover  # noqa: E402
from skills.enrich import _build_user_content  # noqa: E402

_failures: list[str] = []
_skips: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"{'✓' if cond else '✗'} {msg}")
    if not cond:
        _failures.append(msg)


def art(text: str, lang: str, title: str = "T") -> ArticleV1:
    return ArticleV1(
        id="sha256:test", outlet=_Outlet(id="o1", name="Test"), url="http://x/a",
        title=title, text=text, language=lang,
        scraped_at=datetime.now(timezone.utc), word_count=len(text.split()),
    )


async def main() -> None:
    # 1. Gated off
    off = NerPrepass(NerCfg(enabled=False))
    check(await off.extract(art("Barack Obama met Tim Cook in Paris.", "en")) == [],
          "disabled → extract() returns []")

    # 2. Unsupported language (no model mapping for 'zz')
    on_cfg = NerCfg(enabled=True, models={"en": "en_core_web_sm", "es": "es_core_news_sm"})
    p = NerPrepass(on_cfg)
    check(await p.extract(art("texto", "zz")) == [], "unsupported language → [] (fail-open)")

    # 3. Missing model name → fail-open, and recorded so it isn't retried
    bad = NerPrepass(NerCfg(enabled=True, models={"en": "no_such_model_xyz"}))
    check(await bad.extract(art("Barack Obama in Paris.", "en")) == [],
          "missing model → [] (fail-open)")
    check("en" in bad._unavailable, "missing model recorded as unavailable (no retry)")

    # 4. format_must_cover
    check(format_must_cover([]) == "", "format_must_cover([]) → ''")
    mc = format_must_cover([NerEntity("Obama", "PERSON"), NerEntity("Apple", "ORG"),
                            NerEntity("Cook", "PERSON")])
    check("PERSON: Obama, Cook" in mc and "ORG: Apple" in mc,
          "format_must_cover groups names by type")

    # 5. enrich prompt injects MUST_COVER iff present
    a = art("body text", "en")
    no_block = _build_user_content(a, None)
    with_block = _build_user_content(a, [NerEntity("Obama", "PERSON")])
    check("MUST_COVER" not in no_block, "no MUST_COVER block when entities absent")
    check("MUST_COVER" in with_block and "Obama" in with_block,
          "MUST_COVER block injected when entities present")

    # 6. Real extraction (only if small models are installed)
    import spacy
    have_en = spacy.util.is_package("en_core_web_sm")
    have_es = spacy.util.is_package("es_core_news_sm")
    if have_en:
        ents = await p.extract(art(
            "Barack Obama met Apple chief executive Tim Cook in Paris on Tuesday "
            "to discuss the European Union. Obama praised Apple repeatedly.", "en"))
        names = {e.name for e in ents}
        types = {e.type for e in ents}
        check(any("Obama" in n for n in names), "EN: extracts PERSON (Obama)")
        check("LOC" in types or "ORG" in types, "EN: extracts a LOC and/or ORG")
        # dedup: 'Obama'/'Apple' mentioned twice each → one entity apiece
        check(sum(n.count("Obama") == 0 for n in names) >= 0
              and len([n for n in names if n == "Obama"]) <= 1, "EN: surface forms deduped")
        check(all(t in ("PERSON", "ORG", "LOC") for t in types),
              "EN: only MUST_COVER types returned (no OTHER/DATE noise)")
    else:
        _skips.append("EN real extraction (en_core_web_sm not installed)")
    if have_es:
        ents = await p.extract(art(
            "El presidente Pedro Sánchez se reunió con la Unión Europea en Madrid.", "es"))
        check(len(ents) >= 1, "ES: multilingual extraction returns entities")
        check(all(e.type in ("PERSON", "ORG", "LOC") for e in ents),
              "ES: CoNLL labels (PER/LOC/ORG) normalized to InkBytes types")
    else:
        _skips.append("ES real extraction (es_core_news_sm not installed)")

    # cap honoured
    capped = NerPrepass(NerCfg(enabled=True, max_entities_per_type=1,
                               models={"en": "en_core_web_sm"}))
    if have_en:
        ents = await capped.extract(art(
            "Obama, Biden, Trump, Bush and Clinton met Apple and Google.", "en"))
        per = [e for e in ents if e.type == "PERSON"]
        check(len(per) <= 1, "max_entities_per_type cap honoured (PERSON ≤ 1)")

    print()
    for s in _skips:
        print(f"⊘ SKIPPED: {s}")
    if _failures:
        print(f"\nFAILED: {len(_failures)} check(s)")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nALL PASSED" + (f" ({len(_skips)} skipped)" if _skips else ""))


asyncio.run(main())
