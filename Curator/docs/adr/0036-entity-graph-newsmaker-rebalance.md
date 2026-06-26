# Curator ADR-0036 — Entity graph: newsmaker rebalance (fixing "People = 1")

> *Status: **accepted** — implemented 2026-06-26 (api_server.py `/graph`) · Owner: Julian · Date: 2026-06-26*

## Context — the symptom

The Reader `/entities` force graph showed almost no people ("People = 1"), which
read as broken NER / entity extraction.

## Investigation — extraction is fine; the graph *selection* was the bug

On the post-reset prod corpus the `entities` table is rich: **91,385 PERSON
mentions (34,850 distinct)**, avg **12.1 entities/article**, and a single top event
carries **186 distinct people**. So extraction and typing are healthy — enabling the
dormant spaCy NER pre-pass (ADR-0032 item 2) would have been wasted effort.

The bug was in the `/graph` node selection:

1. **Ubiquity domination.** Nodes were ranked purely by `COUNT(DISTINCT event_id)
   DESC LIMIT 80`. The winners are countries and cities that appear in *everything*
   — top nodes were `estados unidos` (402 events), `united states` (363), `españa`
   (279), `méxico` (265), `colombia` (236), `madrid`, `washington`… Only **Donald
   Trump** cracked the top as a person. Result: 55 LOC / 13 ORG / **8 PERSON** / 4
   EVENT out of 80 (and literally 1 under older, more-skewed data).
2. **Wire services as nodes.** `efe`, `ap`, `reuters`, `cnn`, `infobae` get
   NER-tagged on every article from that source → ubiquitous but not newsmakers.
3. **Alphabetical type tiebreak.** The old `node_types` derived the type from a
   per-event collapse (`DISTINCT ON … ORDER BY ent.type`), and PERSON sorts *last*
   (EVENT<LOC<ORG<OTHER<PERSON) — so a person ever mistagged ORG/OTHER got demoted.
   (Measured impact was small here, but it's a latent correctness bug.)

This is the **same insight as the clustering fix (ADR-0031)**: ubiquitous,
high-document-frequency entities are noise; specific ones are signal.

## Decision

Rebuild `/graph` node selection so it's a **balanced newsmaker network**, not a map
of countries:

1. **Per-type quotas** (derived from `limit_nodes`): PERSON ~45%, ORG ~30%, LOC
   ~18%, EVENT ~7%, OTHER ~4%. Rank *within* type by event_count, then take each
   type's quota. PERSON/ORG lead; LOC/EVENT are context.
2. **Drop wire-service/outlet bylines** via `_GRAPH_SOURCE_STOPWORDS` (efe, ap,
   reuters, afp, dpa, ansa, bloomberg, bbc, cnn, infobae, …). Conservative — keeps
   real orgs (FIFA, UEFA, EU) that are genuine subjects of coverage.
3. **Dominant type from RAW mentions**, tiebreak preferring concrete types over
   OTHER — replaces the alphabetical collapse.

## Result (validated read-only on prod before deploy)

`PERSON 8 / LOC 55` → **PERSON 35 / ORG 24 / LOC 14 / EVENT 6**. Surfaced nodes are
real newsmakers: Trump, Pedro Sánchez, Lionel Messi, Claudia Sheinbaum, Abelardo de
la Espriella, Gustavo Petro, Delcy Rodríguez, Marco Rubio, the European Union.

## Consequences / follow-ups

- The graph becomes a who's-who, not a world map. Locations remain as bounded context.
- **Cross-language duplication persists** (`estados unidos`/`united states`,
  `españa`/`spain`, `unión europea`/`european union` are the same entity in two
  languages — sometimes typed differently). The per-type quota *bounds* its impact,
  but true cross-language entity normalization is a separate item (shares the
  cross-language event-dedup theme).
- Stopword list + quota fractions are easy to tune; quotas underfill (fewer total
  nodes) rather than backfilling with locations when a type is sparse.
