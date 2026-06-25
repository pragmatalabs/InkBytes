"""Non-news filler filter — keeps horoscopes & gambling/lottery picks out of events.

Many general-interest outlets (especially LATAM/ES dailies) publish recurring
non-news filler alongside real reporting:

  • Horoscopes / astrology  ("Horóscopo de hoy: predicciones para tu signo")
  • Lottery results & number picks ("Resultados de la Lotería Nacional: números
    ganadores", "Powerball winning numbers", "Quiniela de hoy")
  • Sports-betting tips / projections ("Pronósticos deportivos de la jornada")

These cluster by recurrence (every outlet runs a daily horoscope) and synthesize
into junk pages that crowd out news.  `is_excluded()` flags them by deterministic,
high-precision patterns so SynthesizeSkill can (a) skip a cluster that is a strict
majority filler, and (b) refuse to publish a filler headline as a backstop
(Curator ADR-0021).

Scope is intentional — PRECISION over recall.  We target horoscope/astrology and
explicit lottery-result / betting-pick content, NOT:
  • a disease or a person that shares a sign's name   ("Cáncer de mama", Pope "León XIV")
  • news ABOUT the gambling industry / regulation      ("regulan las apuestas online",
                                                         "Lotería Nacional anuncia reforma")
  • a weather forecast                                 ("pronóstico del tiempo: lluvias")
  • a match preview / editorial prediction             ("Pronóstico: Argentina vs Honduras")
When in doubt the filter KEEPS the item — a stray horoscope slipping through is
cheaper than dropping real news.  EN + ES primary, FR/DE for the European outlets.
Tune against the live corpus via scripts/test_content_filter.py.
"""
from __future__ import annotations

import re

# ── Horoscope / astrology ────────────────────────────────────────────────────
# Unambiguous astrology vocabulary only — NEVER bare sign names (Leo/Cáncer/Aries/
# Virgo), which collide with people, diseases and brands.
_HOROSCOPE = (
    r"\bhor[oó]scop"                       # horoscope / horóscopo / horoscopo
    r"|\bhoroskop"                          # de: Horoskop
    r"|\bzodiac"                            # zodiac / zodiacal
    r"|\bzod[ií]aco"                        # es: zodiaco / zodíaco
    r"|\bzodiaque\b"                        # fr: zodiaque
    r"|\bastrolog"                          # astrology / astrología / astrologie
    r"|\btarot\b"
    r"|\bstar\s+signs?\b"
    r"|\bsternzeichen\b|\btierkreiszeichen\b"   # de
    r"|\bsigne\s+astrologique\b"            # fr
    r"|\bcarta\s+astral\b"
    r"|\btu\s+signo\b|\bsigno\s+(del\s+)?zodiac"
)

# ── Lottery results / number picks (require a result/number/draw signal) ──────
# A bare org name ("Lotería Nacional") is KEPT — only results/numbers/draws flag.
_LOTTERY = (
    r"\bpowerball\b"
    r"|\bmega\s?millions\b"
    r"|\b(winning|lucky)\s+numbers?\b"
    r"|\bn[uú]meros?\s+(ganadores?|de\s+la\s+suerte)\b"
    r"|\blottery\s+(results?|numbers?|draw)\b"
    r"|\blottozahlen\b"                                       # de
    r"|\bresultados?\s+(de\s+)?(la\s+)?(loter[ií]a|loterie|quiniela|sorteo|powerball|mega\s?millions)\b"
    r"|\bsorteo\b[^.!?]{0,25}\b(loter[ií]a|quiniela|premio\s+mayor)\b"
    r"|\b(loter[ií]a|quiniela)\b[^.!?]{0,25}\bsorteo\b"
    r"|\bquiniela\b"
    r"|\bleidsa\b|\bloteka\b"                                 # DR lottery brands
    r"|\b(loto|lotto)\b"
)

# ── Sports-betting tips / projections (explicit betting signal required) ──────
# Avoids weather "pronóstico" and metaphorical "apuesta por" by demanding an
# explicit betting context word.
_BETTING = (
    r"\bbetting\s+tips?\b"
    r"|\btipster\b"
    r"|\bpron[oó]sticos?\s+(deportivos?|de\s+apuestas)\b"
    r"|\bcu[oó]tas\s+de\s+apuestas?\b"
    r"|\bapuestas?\s+(deportivas?\s+)?(de\s+hoy|del\s+d[ií]a)\b"
)

# ── Live-blog / daily-roundup non-events ──────────────────────────────────────
# Live tickers, "what's on today", live standings, date-only titles. These cluster
# together (all "live update" pages) and mix every topic of the day into one junk
# page. Precision-first: require an explicit live/today-roundup marker — NEVER bare
# "hoy" or "noticias" (every news headline has those). "Noticias del ICE en Houston
# hoy: …" (a real story) must NOT match.
_LIVEBLOG = (
    r"\ben\s+vivo\b[^.!?]{0,30}\b(hoy|[uú]ltimas\s+noticias|minuto\s+a\s+minuto)\b"
    r"|\b[uú]ltimas\s+noticias\s+de\s+hoy\b"
    r"|\ben\s+directo\b[^.!?]{0,30}\bhoy\b"
    r"|\bminuto\s+a\s+minuto\b"
    r"|\blive\s+blog\b|\bliveblog\b|\blive\s+updates?\b|\blive:\s"
    r"|\bqu[eé]\s+partidos\s+se\s+juegan\s+hoy\b"
    r"|\btabla\s+de\s+posiciones\b[^.!?]{0,40}\b(en\s+vivo|hoy|resultados?)\b"
    r"|\bresultados?\b[^.!?]{0,20}\ben\s+vivo\s+hoy\b"
    r"|\bal\s+momento\s*:"                                  # "AL MOMENTO:" live marker
    r"|\b(eliminados|clasificados)\b[^.!?]{0,40}\bal\s+momento\b"
)
# NOTE: match-preview / "when & where to watch" titles (e.g. "Argentina vs
# Honduras: previa, horario y dónde ver") are intentionally KEPT — the corpus test
# treats single-match previews as legitimate content, not filler. Only daily
# all-fixtures roundups ("qué partidos se juegan hoy") and live tickers are gated.

# A title that is essentially just a date — "Miércoles, 24 de junio de 2026".
_DATE_ONLY = re.compile(
    r"^\s*(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)?,?\s*"
    r"\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s*$", re.I)

# Each entry is (compiled pattern, label). A single match flags the text.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(_HOROSCOPE, re.I), "horoscope"),
    (re.compile(_LOTTERY, re.I), "lottery"),
    (re.compile(_BETTING, re.I), "betting"),
    (re.compile(_LIVEBLOG, re.I), "liveblog"),
]


def exclusion_reason(text: str | None) -> str | None:
    """Return the label of the first matching filler pattern, or None if clean."""
    if not text:
        return None
    if _DATE_ONLY.match(text.strip()):
        return "date-only"
    for pat, label in _PATTERNS:
        if pat.search(text):
            return label
    return None


def is_excluded(text: str | None) -> bool:
    """True if `text` looks like horoscope / lottery / betting filler (non-news)."""
    return exclusion_reason(text) is not None
