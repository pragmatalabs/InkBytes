"""Per-theme editorial personas (ADR-0008).

A named, READER-FACING editorial voice per vertical — the masthead/glyph on the
Outlook Column page (ADR-R-0011). The corpus is LATAM-first, so the names are
Spanish. Keys map 1:1 to the 15 `articles.theme` values (Curator ADR-0032).

⚠️ ADR-0010 (method-persona rosters): the RICH per-column reporting-method
rosters live in `prompts/personas-spec.md` (10 journalist-METHOD archetypes per
column — method/structure/evidence only, NOT identity; the journalist names are
internal routing references and must NEVER reach the reader or be imitated in
prose). This module stays the reader-facing (key, display name, mission) map;
the generator selects an internal method-persona from the spec per assignment.
The one-line `voice` below is the interim single-voice until ADR-0010's
selection step is wired.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

# theme → (persona key, display name, one-line voice/stance injected into the prompt)
PERSONAS: dict[str, tuple[str, str, str]] = {
    "politics":      ("la-mesa",       "La Mesa",        "análisis político sobrio y equilibrado; explica el porqué detrás de las maniobras, sin partidismo."),
    "world":         ("el-atlas",      "El Atlas",       "mirada de asuntos globales; conecta los hechos del día con corrientes geopolíticas más amplias."),
    "business":      ("el-balance",    "El Balance",     "economía y mercados con cabeza fría; traduce cifras en consecuencias para la gente."),
    "technology":    ("el-circuito",   "El Circuito",    "tecnología con criterio; distingue la señal del bombo y pregunta a quién beneficia."),
    "sports":        ("la-tribuna",    "La Tribuna",     "crónica deportiva con pasión medida; el relato humano detrás del resultado."),
    "health":        ("el-pulso",      "El Pulso",       "salud con rigor; matiza el riesgo real, evita el alarmismo y la falsa esperanza."),
    "environment":   ("la-marea",      "La Marea",       "clima y medioambiente; los hechos a largo plazo bajo la noticia del día, sin sermones."),
    "culture":       ("el-telon",      "El Telón",       "cultura y artes; por qué una obra o un debate importa más allá del estreno."),
    "science":       ("el-laboratorio","El Laboratorio", "ciencia explicada con honestidad; lo que un hallazgo sí dice y lo que aún no."),
    "entertainment": ("la-marquesina", "La Marquesina",  "espectáculo con ironía elegante; el fenómeno cultural detrás del titular."),
    "crime":         ("el-expediente", "El Expediente",  "crimen y justicia con prudencia; presunción de inocencia, sin morbo."),
    "education":     ("el-aula",       "El Aula",        "educación con perspectiva; el sistema detrás de la anécdota."),
    "lifestyle":     ("la-plaza",      "La Plaza",       "vida cotidiana y tendencias; lo que un cambio social dice de nosotros."),
    "religion":      ("el-campanario", "El Campanario",  "religión y sociedad con respeto y distancia crítica a la vez."),
    "disaster":      ("la-alerta",     "La Alerta",      "desastres y emergencias con cabeza fría; qué pasó, qué falló, qué sigue — sin espectáculo del dolor."),
}

_DEFAULT = ("el-editor", "El Editor", "análisis sobrio que sintetiza el día en una sola narrativa.")


def persona_for(theme: str | None) -> tuple[str, str, str]:
    return PERSONAS.get((theme or "").lower(), _DEFAULT)


# ── ADR-0010: method-persona rosters (parsed from prompts/personas-spec.md) ────
#
# Each column has a roster of ~10 journalist-METHOD archetypes. These are
# INTERNAL routing references (method / structure / evidence discipline only) —
# the journalist names must never reach the reader or be imitated in prose. The
# reader-facing identity stays the Spanish persona above (PERSONAS / persona_for).

_SPEC = Path(__file__).resolve().parent / "prompts" / "personas-spec.md"


class MethodPersona(NamedTuple):
    role: str          # e.g. "Institutional presidency correspondent"
    use_when: str       # the reporting problem this method fits
    ready_prompt: str   # the vendored ready-to-use method prompt


def _display_to_theme() -> dict[str, str]:
    return {name: theme for theme, (_k, name, _v) in PERSONAS.items()}


@lru_cache(maxsize=1)
def _parse_spec() -> tuple[str, dict[str, list[MethodPersona]]]:
    """Parse personas-spec.md once → (global policy, {theme|'_default': roster})."""
    text = _SPEC.read_text("utf-8")

    pol = re.search(r"## Global Editorial Policy\n(.*?)\n## ", text, re.S)
    policy = pol.group(1).strip() if pol else ""

    disp2theme = _display_to_theme()
    rosters: dict[str, list[MethodPersona]] = {}

    # level-1 headers split the columns (front matter is skipped: no theme match)
    for part in re.split(r"\n# ", "\n" + text):
        if not part.strip():
            continue
        header = part.splitlines()[0].strip()
        colname = header.replace("Fallback —", "").strip()
        theme = disp2theme.get(colname)
        bucket = theme or ("_default" if "El Editor" in header else None)
        if bucket is None:
            continue

        roster: list[MethodPersona] = []
        for chunk in re.split(r"\n## ", part)[1:]:  # each h2 = a persona (skip mission)
            ready = re.search(r"```text\n(.*?)```", chunk, re.S)
            if not ready:
                continue  # the mission chunk / non-persona sections have no prompt
            title = chunk.splitlines()[0].strip()
            role_m = re.search(r"\*\*Persona role:\*\*\s*(.+)", chunk)
            use_m = re.search(r"\*\*Use this persona when:\*\*\s*(.+)", chunk)
            role = role_m.group(1).strip() if role_m else re.sub(r"^\d+\.\s*", "", title)
            use_when = use_m.group(1).strip() if use_m else "no specialized method fits"
            roster.append(MethodPersona(role, use_when, ready.group(1).strip()))
        if roster:
            rosters[bucket] = roster

    return policy, rosters


def global_policy() -> str:
    """The Global Editorial Policy preamble (ADR-0010), from the vendored spec."""
    return _parse_spec()[0]


def roster_for(theme: str | None) -> list[MethodPersona]:
    """The column's method-persona roster; falls back to El Editor's single method."""
    _policy, rosters = _parse_spec()
    return rosters.get((theme or "").lower()) or rosters.get("_default", [])
