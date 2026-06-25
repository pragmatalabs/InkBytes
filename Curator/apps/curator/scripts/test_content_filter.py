#!/usr/bin/env python
"""Test the non-news filler filter — horoscope / lottery / betting (Curator ADR-0021).

FLAG cases: real horoscope, lottery-result, and betting-pick titles.
KEEP cases: real news that mentions a sign-name disease/person, the gambling
            industry, a weather forecast, or a match preview — these must NOT be
            flagged (precision guard).

Run:
  cd Curator/apps/curator && .venv/bin/python scripts/test_content_filter.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.content_filter import is_excluded, exclusion_reason  # noqa: E402

FLAG = [
    # Horoscope / astrology (EN/ES/FR/DE)
    "Horóscopo de hoy, 9 de junio: predicciones para todos los signos",
    "Horóscopo Aries: qué te depara el amor esta semana",
    "Daily Horoscope for June 9: What the stars have in store for your zodiac sign",
    "Tu signo del zodiaco y la suerte de la semana",
    "Astrología: la carta astral de junio para cada signo",
    "Tarot del día: las cartas hablan",
    "Horoskop heute: Was die Sterne für Ihr Sternzeichen sagen",
    "Horoscope du jour : vos prédictions selon votre signe astrologique",
    # Lottery results / numbers
    "Resultados de la Lotería Nacional: números ganadores del sorteo de hoy",
    "Powerball winning numbers for June 9 drawing: jackpot climbs to $200M",
    "Mega Millions results: did anyone win the jackpot last night?",
    "Quiniela de hoy: resultados y premios",
    "Leidsa: números ganadores de la quiniela palé",
    "Lottozahlen vom Samstag: die aktuellen Gewinnzahlen",
    "Lucky numbers for today, according to your sign",
    # Sports betting tips / projections
    "Pronósticos deportivos: las mejores apuestas para la jornada",
    "Apuestas deportivas de hoy: cuotas y picks del día",
    "Betting tips: best bets for the Champions League final",
    # Live-blog / daily-roundup non-events (2026-06-25)
    "Mundial 2026, en VIVO: últimas noticias de hoy, 23 de junio",
    "Mundial 2026: ¿qué partidos se juegan hoy, 23 de junio? Horarios",
    "Tabla de posiciones del Mundial 2026 EN VIVO HOY: resultados",
    "Eliminados en fase de grupos AL MOMENTO: ¿qué equipos ya NO siguen?",
    "Miércoles, 24 de junio de 2026",
    "Champions League final live: minute-by-minute updates",
]

KEEP = [
    # Sign-name collisions — disease, person, brand
    "Cáncer de mama: nuevo tratamiento aprobado por la FDA",
    "El Papa León XIV celebra misa ante un millón en Madrid",
    "Virgin Galactic launches its next commercial spaceflight",
    # Gambling INDUSTRY / regulation news (not a result/pick)
    "El gobierno regula las apuestas deportivas online para menores",
    "Lotería Nacional anuncia una reforma en la distribución de premios",
    "Casino revenue falls 12% amid new gambling addiction rules",
    # Weather forecast — NOT betting
    "Pronóstico del tiempo: lluvias intensas y oleaje en Guerrero",
    "Weather forecast: heatwave to grip the Southwest this week",
    # Match preview / editorial prediction — sports journalism, kept
    "Argentina vs Honduras: previa, horario y dónde ver el partido",
    "Análisis: cómo llega España al Mundial 2026",
    # Real story with "noticias … hoy" — NOT a live-blog (live-blog guard)
    "Noticias del ICE en Houston hoy: perímetro cerrado y desvíos de tráfico",
    "España gana hoy su primer partido del Mundial",
    # Real news mentioning numbers
    "Inflación de mayo: los precios suben un 4% interanual",
    "Three winning startups announced at the tech summit",
]


def main() -> int:
    ok = True
    print("── FLAG (must be excluded) ──")
    for t in FLAG:
        r = exclusion_reason(t)
        mark = "✅" if r else "❌ MISS"
        if not r:
            ok = False
        print(f"  {mark} [{r or '-'}] {t}")

    print("\n── KEEP (must NOT be excluded) ──")
    for t in KEEP:
        r = exclusion_reason(t)
        mark = "✅" if not r else f"❌ FALSE-POSITIVE [{r}]"
        if r:
            ok = False
        print(f"  {mark} {t}")

    flagged = sum(1 for t in FLAG if is_excluded(t))
    kept_clean = sum(1 for t in KEEP if not is_excluded(t))
    print(f"\nFLAG: {flagged}/{len(FLAG)} flagged | KEEP: {kept_clean}/{len(KEEP)} clean")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
