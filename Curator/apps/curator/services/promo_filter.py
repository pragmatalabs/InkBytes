"""Promotional / commerce content filter — keeps shopping & affiliate pieces out of events.

Some outlets publish affiliate/commerce content alongside news: product-review
roundups ("the best X in the US"), gift guides ("the 10 best gifts for new moms"),
first-person product testing ("I tried 10 laundry baskets…"), and price-drop /
deal posts ("40% descuento", "record low price cut"). These are not news. When a
batch of them clusters, synthesis produces an ad-style page — e.g. "Guardian
Covers Top New Mom Gifts and Sonos Speaker Reviews", built entirely from The
Guardian's shopping vertical.

`is_promotional()` flags such text by deterministic, high-precision patterns so the
Curator pipeline can (a) skip it at ENRICH so it never clusters, and (b) refuse to
publish an ad-style synthesized headline as a backstop (Curator ADR-0020).

Scope is intentional — PRECISION over recall. We target **commerce / affiliate /
product-purchase** content and other-outlet product promos, NOT:
  • ordinary news that mentions a brand        ("Apple Unveils Siri AI Overhaul")
  • news ABOUT a shopping event                ("Black Friday fraud prevention tips",
                                                "el fenómeno de las microcompras")
  • editorial "best-of" recommendations        ("the seven best shows to stream",
                                                "Best coffee city in the world?")
What IS flagged: a specific product + a price/discount action, product reviews,
first-person testing, gift guides, and product listicles.
  FLAG: "The 10 best gifts for new moms", "Sonos review: best speakers money can buy",
        "I tried 10 laundry baskets", "Apple AirPods Max 2 hit record low price cut",
        "Amazon liquida la batería Baseus con un 40% de descuento"
When in doubt the filter KEEPS the item — a stray ad slipping through is cheaper
than dropping real news. Tuned against the live corpus.
"""
from __future__ import annotations

import re

# Product / shopping nouns. A bare "N best …" listicle is only treated as commerce
# when it names one of these (so "best shows/films/songs/cities/recipes" — editorial
# — are kept). EN + ES.
_PRODUCT = (
    r"speakers?|headphones?|earbuds?|earphones?|airpods|shoes?|sneakers?|vacuums?|"
    r"trackers?|chargers?|power\s?bank|powerbank|batería|bateria|laptops?|tablets?|"
    r"smartphones?|monitors?|mattress|hamper|baskets?|blowers?|heaters?|umbrellas?|"
    r"towels?|jackets?|banks?|credit unions?|software|gadgets?|appliances?|blenders?|"
    r"fryer|cameras?|drones?|smartwatch|watches?|routers?|ssd|tv|tvs|televisors?|"
    r"audífonos|altavoz|altavoces|auriculares|zapatillas|tenis|cargador|protein bars?|"
    r"running shoes?|bike locks?|space heaters?|leaf blowers?|rain jackets?|bath towels?"
)

# Explicit price / discount / sale actions — the unambiguous ad signal (EN + ES).
# Deliberately price-ADJACENT to avoid Spanish ambiguity and economic news:
#   • "liquida" alone = layoffs ("liquida a sus 600 empleados") — excluded; we
#     require an accompanying %/precio, which real clearance ads carry.
#   • "rebaja" (singular/verb) = a ratings downgrade — excluded; only the plural
#     sale noun "rebajas" counts.
#   • bare "record low" = an economic indicator ("consumer sentiment record low")
#     — excluded; we require "record/lowest … price".
_PRICE_ACTION = (
    r"\b\d+\s?%\s?(off|de\s+descuento|descuento)\b|\bdescuento\s+del?\b|\bde descuento\b|\b% off\b|"
    r"\bprice cut\b|\blowest price\b|\b(all-time|record)[\s-]low price\b|"
    r"\bprecio\b[^.!?]{0,30}\bmínimo histórico\b|\bmínimo histórico\b[^.!?]{0,20}\bprecio\b|"
    r"\bcae un\s+\d+\s?%|\brebajas\b|\bon sale\b|\bdeal of the day\b|"
    r"\b(best|top)\s+deals?\b|\bshop now\b|\badd to cart\b|\bbuy now\b|"
    r"\bcompra\s+(ya|ahora)\b"
)

# Each entry is (compiled pattern, label). A single match flags the text.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # ── Price / discount / sale ad (specific product implied by the deal) ──────
    (re.compile(_PRICE_ACTION, re.I), "price-deal"),

    # ── Gift guides ────────────────────────────────────────────────────────────
    (re.compile(r"\bgift\s+(guide|guides|ideas?)\b", re.I), "gift-guide"),
    (re.compile(r"\bbest\s+gifts?\b", re.I), "best-gifts"),
    (re.compile(r"\b\d+\s+(?:best\s+)?gifts?\b", re.I), "n-gifts"),
    (re.compile(r"\bgifts?\s+for\b[^.!?]{0,30}\b(mom|dad|her|him|grad|kids?|new mom)\b", re.I), "gifts-for"),

    # ── Product reviews / first-person testing (affiliate hallmark) ────────────
    (re.compile(r"\breview:\s", re.I), "review-colon"),
    (re.compile(r"\b(hands?-on|head[\s-]to[\s-]head)\b[^.!?]{0,30}\breview\b", re.I), "hands-on-review"),
    (re.compile(r"\bI\s+(tried|tested|compared|cut up|bought|reviewed)\b", re.I), "first-person-test"),
    (re.compile(r"\btested and reviewed\b", re.I), "tested-reviewed"),

    # ── "best X to buy / money can buy" (purchase intent, any product) ─────────
    (re.compile(r"\bbest\b[^.!?]{0,45}\b(to buy|money can buy|worth buying|for your money)\b", re.I), "best-buy"),

    # ── Product listicles: "the N best <product>" / "N best <product>" ─────────
    (re.compile(rf"\b(?:the\s+)?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+best\b[^.!?]{{0,40}}\b(?:{_PRODUCT})\b", re.I), "product-listicle"),
    (re.compile(rf"\bbest\b[^.!?]{{0,40}}\b(?:{_PRODUCT})\b[^.!?]{{0,30}}\b(of\s+20\d{{2}}|in the (us|uk))\b", re.I), "best-product-of"),

    # ── Synthesized ad-style headline: "X covers/recommends/picks top|best …" ───
    (re.compile(r"\b(covers?|recommends?|rounds?\s+up|picks?)\b[^.!?]{0,40}\b(top|best)\b[^.!?]{0,45}\b(gifts?|deals?|reviews?|products?|buys?)\b", re.I), "ad-headline"),
    (re.compile(r"\b(top|best)\b[^.!?]{0,30}\b(gifts?|deals?)\b[^.!?]{0,30}\b(reviews?|speakers?|gadgets?)", re.I), "ad-headline"),
]


def promo_reason(text: str | None) -> str | None:
    """Return the label of the first matching promo pattern, or None if clean."""
    if not text:
        return None
    for pat, label in _PATTERNS:
        if pat.search(text):
            return label
    return None


def is_promotional(text: str | None) -> bool:
    """True if `text` looks like commerce/affiliate/product-purchase content."""
    return promo_reason(text) is not None
