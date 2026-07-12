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
