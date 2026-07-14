# ADR-0010 — Outlook columns: method-persona rosters (Editorial service)

> *Status: **Implemented + DEPLOYED + verified live 2026-07-12** · Owner: Julian · Date: 2026-07-12*
> *Extends [ADR-0008](./0008-editorial-service-llm-selection.md) (Editorial service). Source of truth: [`Editorial/apps/editorial/prompts/personas-spec.md`](../../Editorial/apps/editorial/prompts/personas-spec.md).*

## Context

ADR-0008 shipped one editorial persona per theme — a single one-line "voice"
string (`personas.py`: `technology → ("el-circuito", "El Circuito", "tecnología
con criterio…")`) injected into one shared prompt. It works, but every column
sounds the same shape regardless of what the day's events *are* (a corporate
scandal, a technical launch, and a policy fight all get the same treatment).

Julian supplied a far richer spec (`outlook_column_personas.md`, 150 personas):
for each of the 15 columns, a **roster of ~10 method-personas** — each an
abstraction of a respected journalist's **reporting method** (Peter Baker →
institutional-presidency chronology; Matt Levine → financial-mechanics
explainer; …) — plus a **Global Editorial Policy**, a **Universal Output
Workflow**, and invocation/execution templates. The columns map 1:1 to our
themes (La Mesa=politics … La Alerta=disaster, + El Editor fallback).

**The load-bearing rule (from the spec, non-negotiable):** the agent
**must not impersonate the named journalist**, claim their authorship,
reproduce recognizable phrasing, or imitate signature mannerisms. *"The
journalist's name is a routing reference for editorial method only."* Persona
controls **method, structure, evidence discipline** — never identity.

## Decision

1. **Adopt the spec as the Editorial service's persona system.** Vendored at
   `Editorial/apps/editorial/prompts/personas-spec.md` (canonical, diffable —
   same "prompts as .md" convention as ADR-0008).

2. **Two layers, kept distinct:**
   - **Reader-facing identity is unchanged.** The column masthead + glyph still
     show the Spanish persona (`El Circuito`, ADR-R-0011). Readers never see a
     journalist's name. The 10 archetypes are **internal method routers only.**
   - **Internal method-persona** selected per assignment drives the prompt's
     reporting method / structure / tone / evidence discipline / ending.

3. **Selection by reporting problem, not topic** (spec workflow §2): within a
   column, pick the persona whose *method* matches the shape of the day's
   events. Recommended mechanism: a cheap LLM classify-and-route step
   ("given these headlines, which method fits: chronology / accountability /
   explainer / profile / …") reusing the existing engine; fallbacks = daily
   rotation or the column's lead persona. An optional secondary persona only
   when it adds a distinct capability.

4. **The Global Editorial Policy becomes a hard system preamble** on every
   generation: no fabricated quotes/scenes/documents/access/motives; explicitly
   distinguish verified fact vs allegation vs interpretation vs statistical
   inference vs editorial judgment vs unresolved uncertainty; attribute strong
   claims; no single-anecdote→trend; no false balance; preserve presumption of
   innocence. This is a **net risk reduction** against the legal-risk memo
   ([[legal-risk-launch-gate]]) — defamation (no §230) and market-substitution
   exposure both drop when the model is disciplined about fact vs allegation and
   original vs reproduced.

5. **Store the method-persona in provenance.** `editorials` already keeps
   `input_context` + `prompt` (the Phase-2 SLM training pair). Adding the
   selected method-persona label makes the training data **method-conditioned**
   — the distilled SLM can learn "write this as accountability vs explainer."

## Backend integration (IMPLEMENTED 2026-07-12 — `personas.py` roster loader, LLM routing in `application.py`, policy preamble, method stored in `input_context.method_persona`)

| Piece | Change |
|---|---|
| `personas.py` | Keep the theme→column map (key, **reader display name**, mission). Add a loader that parses `personas-spec.md` into per-column rosters (role, use-when, method, structure, tone, evidence, avoid, ending, ready prompt). |
| `prompts/editorial.md` | Split into: Global Editorial Policy preamble + Execution Template (persona method/structure/tone/ending) + the existing language/citation/format/output rules + events. |
| `core/application.py` | `generate_theme`: load column roster → **select persona** (LLM route / rotation) → assemble prompt (policy + execution template + events) → generate → store persona label. |
| provenance | `editorials` row records `method_persona` (the archetype role) alongside the reader `persona` (El Circuito). |
| validation | Dry-run each column on real prod data (ES + EN) as in ADR-0008; compare against the current single-voice output before flipping the cron. |

Reader/API surface (ADR-R-0011 Column view) needs **no change** — same
`El Circuito` masthead; the richer method just improves the prose.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Keep the single one-line voice | Every column is the same shape; the spec's whole point is method-fit per assignment. |
| Show the journalist archetype to readers ("in the style of Matt Levine") | Violates the spec's core rule + real appropriation/repute risk. Names stay internal. |
| Hardcode one fixed archetype per column | Loses selection-by-reporting-problem; a scandal and a launch in the same column want different methods. |
| Transcribe 150 personas into Python literals | Brittle + 150-way duplication; the vendored `.md` is the source, parsed at load. |

## Consequences

- Columns vary their method to fit the day's events — more like a real desk of
  columnists than one templated voice.
- One added (cheap) routing step per column/day; latency-tolerant (nightly batch).
- Stronger factual discipline site-wide via the Global Editorial Policy — helps
  the launch-gate legal posture.
- Better Phase-2 SLM data (method-conditioned pairs).
- **Guardrail to hold forever:** journalist names never reach the reader or the
  prose; they route method only. Any output that imitates a named journalist's
  cadence/phrasing is a bug.
- **Fix 2026-07-12 (deployed):** the model backtick-wrapped `[n]` citations (the
  prompt demonstrated them in backticks) → they rendered as code spans. Prompt now
  says plain [n]; Reader linkify swallows stray backticks. See lessons-learned.
