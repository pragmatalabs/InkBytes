#!/usr/bin/env python
"""Test the promotional/commerce content filter (Curator ADR-0020).

FLAG cases: real commerce/affiliate/deal titles seen in the corpus.
KEEP cases: real news headlines that mention brands/shopping events/best-of
            editorial — these must NOT be flagged (precision guard).

Run:
  cd Curator/apps/curator && .venv/bin/python scripts/test_promo_filter.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.promo_filter import is_promotional, promo_reason  # noqa: E402

FLAG = [
    "The 10 best US gifts for new moms, according to a new mom",
    "The 20 best gifts in the US for people who love the outdoors, tested in nature",
    "Sonos review: Are these the best portable speakers that money can buy?",
    "I tried 10 laundry baskets to find the best hamper in the US",
    "I cut up 15 bike locks to find the best in the US. Here are my favorites",
    "Dyson v Bissell: I compared their latest lightweight stick vacs head to head",
    "The best bath towels of 2026 in the US, from fluffy to quick drying – tested",
    "The five best space heaters in the US for a quick fix in a freezing home",
    "Best Running Shoes, Tested and Reviewed (2026): Saucony, Adidas, Hoka",
    "5 Best Smart Speakers (2026): Alexa, Google Assistant, Siri",
    "2 Best Bluetooth Trackers of 2026, Plus Honorable Mentions",
    "24 creative and unexpected Valentine’s Day gifts for him",
    "Apple AirPods Max 2 Just Hit Their First-Ever Record Low After a Surprise Price Cut",
    "Amazon liquida la batería externa Baseus de 145W con un 40% de descuento",
    "El hub USB-C de Anker para MacBook cae un 47% en la liquidación final de Amazon",
    "Guardian Covers Top New Mom Gifts and Sonos Speaker Reviews",  # synthesized headline
    "Apple Vision Pro review: This is the future of computing",
]

KEEP = [
    # News mentioning brands / companies — NOT ads
    "Apple Unveils Siri AI Overhaul at WWDC 2026; Shares Dip",
    "Nvidia and Intel Vie for AI Chip Dominance Amid Market Shifts",
    "OpenAI, Anthropic File for IPOs Amid AI Policy Shifts and Ethical Debates",
    "Bank of America rebaja la calificación de Nubank tras la salida de su CFO",
    "De la noche a la mañana, Stanley Black & Decker Puebla liquida a sus 600 empleados",
    # News ABOUT shopping events — NOT ads
    "Amazon's four-day Prime Day event starts June 23, as shoppers battle inflation",
    "Black Friday: cómo las emociones se convierten en el principal blanco de los fraudes",
    "El fenómeno de las ‘microcompras’ se toma el Black Friday en Colombia",
    "Comprar en línea: lo que todo consumidor debe saber sobre garantías y devoluciones",
    "ChatGPT lanzó 'Shopping Research' la nueva función que permitirá buscar las mejores ofertas",
    # Economic indicators with "record low" — NOT ads
    "Consumer sentiment falls to fresh record low in May as surging gas prices hit outlook",
    "Bitcoin Drops Below $60,000 Amid Strategy Sale and Trader Pessimism",
    # Editorial "best-of" recommendations — NOT product ads
    "Best coffee city in the world? Los Angeles",
    "Alice and Steve to Proud: the seven best shows to stream this week",
    "Summer Reading Roundup: New Books from Patchett, O'Farrell, and More",
    # Plain news
    "Pope Leo draws over a million to mass in Madrid, urges unity",
    "Iran Launches Missiles at Israel, Escalating Regional Tensions",
    "World Cup Fever Drives TV Sales Surge in Argentina and Colombia",
]

passed = failed = 0


def check(label: str, text: str, want_flag: bool) -> None:
    global passed, failed
    r = promo_reason(text)
    got = r is not None
    ok = got == want_flag
    passed += ok
    failed += not ok
    mark = "✓" if ok else "✗ FAIL"
    tag = f"[{r}]" if r else "[clean]"
    print(f"  {mark}  want={'FLAG' if want_flag else 'KEEP':4} {tag:20} {text[:74]}")


def main() -> int:
    print("=== must FLAG (commerce / affiliate / deals) ===")
    for t in FLAG:
        check("flag", t, True)
    print("\n=== must KEEP (news, brands, shopping-events, editorial best-of) ===")
    for t in KEEP:
        check("keep", t, False)
    print()
    if failed:
        print(f"[test] FAIL — {failed} failed, {passed} passed")
        return 1
    print(f"[test] PASS — promo filter ({passed} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
