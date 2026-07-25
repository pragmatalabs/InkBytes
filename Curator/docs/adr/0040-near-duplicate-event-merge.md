# ADR-0040 — Near-duplicate event merge pass

> *Status: v1 · Owner: Julian · Date: 2026-07-25 · Built + dev-verified, dry-run validated on prod; NOT yet enabled*

## Context

The ingest clustering gate (ADR-0031: centroid-linkage + **entity-specificity
gate**, tightened to `precision_distance 0.30` + `specificity_min_shared 2` to kill
mega-buckets) has a recall failure mode. When a story's defining entities are
high-frequency geos (e.g. *Spain / Madrid / Ávila*), the specificity gate scores
them as "not specific enough," so articles that are **within** the merge distance
seed *separate* events anyway — and nothing merges them afterward (clustering is
ingest-time only).

Live example (2026-07-25): the Spain wildfires national-emergency story fragmented
into **6 published events** whose centroids were **0.15–0.29 cosine apart** (all
inside the 0.30 line) — while a genuinely different fire (Lleida, 0.447) correctly
stayed separate. The reader saw six pages for one story; the "63% related" score was
the only thing surfacing the duplication.

Loosening the ingest gate would re-open the mega-bucket problem ADR-0031 solved.

## Decision

A **post-hoc near-duplicate event-merge pass** — `Application.run_merge_nearby`
(CLI `--merge-nearby`). It operates on **event centroids** (averaged embeddings,
far more stable than the per-article ingest signal), so a tight distance here is
precision-safe *without touching the ingest entity-gate*.

1. **Detect** (`db.find_near_dup_pairs`): published event **pairs** with centroid
   cosine distance `< merge_distance` (default **0.25**), **same language**, both
   active within `since_hours` (default 72). Same-language keeps it orthogonal to
   the cross-language dedup (ADR-0037).
2. **Group**: union-find over the pairs → connected components (transitive).
3. **Merge** (`db.merge_events`, atomic): survivor = the most-developed event (most
   sources, then articles). Reassign the losers' articles to the survivor, recompute
   its centroid + `source_count`/`article_count`, and drop the losers
   (`status='dropped'`, `merged_into=survivor`, page unpublished). Then
   **re-synthesize the survivor** (`_synthesize_once`) so its page reflects all
   members — as seen in the live one-off, the merged headline correctly aggregated
   *"73,000 evacuations"* from fragments that individually said 10k/11.5k/19k.
4. **URL safety** (migration `024`): `events.merged_into` + a Reader redirect —
   `GET /events/{id}` returns `{merged_into}` for a dropped fragment, and the Reader
   `event/[id]` page 302s to the survivor (event id == page id, 1:1). Old links live.

**Safety-first rollout:** the CLI is **dry-run by default** — it prints the groups
it *would* merge; `--merge-apply` is required to mutate. Knobs: `--merge-distance`,
`--since-hours`, `--merge-min-sources`.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Loosen the ingest entity-gate / raise `precision_distance` | Re-opens the mega-bucket failure ADR-0031 fixed. The gate is right at ingest; the fix belongs *after*. |
| Merge at ingest via an embedding-distance override to the gate | Changes the hot path + risks per-article noise. Centroid-to-centroid post-hoc is a stabler, lower-blast-radius signal. |
| Hard-delete fragment events | Breaks shared URLs + loses provenance. `merged_into` + redirect keeps links + auditability. |
| Cross-language reuse (ADR-0037) | That handles *translations* (marks a non-primary page). This is same-language *duplication* — a different mechanism. |

## Consequences

- Fewer fragmented stories; the "one page per event" promise holds even when the
  ingest gate over-splits. Merged survivors re-synthesize to the full picture.
- **Precision-safe by construction**: centroid distance < 0.25 same-language; the
  Lleida fire (0.447) is never a candidate. Transitive grouping is bounded by the
  tight per-link distance. Dry-run gates every real run.
- New Curator CLI mode + migration `024` (additive). No ingest-path change.
- **Verification (2026-07-25):** logic dev-tested (seeded near-dups → group → merge
  → `merged_into` redirect); the detection query dry-run on the live corpus to
  validate the threshold before any mutation. The manual one-off on the wildfire
  cluster proved the merge+re-synth end to end.
- **Follow-up:** wire `--merge-nearby --merge-apply` into the post-synthesis cycle
  (or a cron) once the threshold is confirmed on a few dry-runs. Left manual/opt-in
  for v1.
