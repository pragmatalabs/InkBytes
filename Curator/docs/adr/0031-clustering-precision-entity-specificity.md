# Curator ADR-0031 — Clustering precision: entity-specificity gate vs mega-buckets

> *Status: **proposed** (prototype done, validation-gated) · Owner: Julian · Date: 2026-06-14*

## Context — the symptom

Two published events had near-identical synthesized headlines:

- `01KTMRBKM2A6QE0TGFMHMBCK86` — "World Cup 2026 opens amid security incidents and fan enthusiasm"
- `01KTMRBKDT84YNE5YQA1NDGS9Q` — "World Cup 2026 Opens in Mexico Amid Economic Hopes and Social Tensions"

They are not two copies of one story. They are **two over-broad topic-buckets**:

| | `DT…9Q` | `M2…86` |
|---|---|---|
| articles | 940 | 551 |
| distinct sources | 26 | 25 |
| distinct `topic` values inside | 849 | 499 |
| span | 06-07 → 06-15 (7.8 d) | same |
| **centroid cosine distance between the two** | **0.0323** | |

Each bucket contains hundreds of *unrelated* stories (Chivas roster, World-Cup
vandalism, ambush marketing, Profeco shopping tips, a museum art installation)
glued together because they all mention the World Cup. Their centroids are 3%
apart, so synthesis produced two near-identical "World Cup opens…" headlines.

**It is systemic.** The top 12 events are all mega-buckets (356–940 articles,
100–849 distinct topics, all seeded 06-07 — the fresh-start re-cluster — and
accreting for ~8 days). 26 events hold 201–940 articles; one holds 417 articles
from a *single* source. Meanwhile 5,953 normal events have ≤20 articles.

## Root cause

`skills/cluster.py` does **single-linkage** clustering:

1. Pull the 20 nearest recent articles (same language, `recent_window_hours=48`).
2. Join the **nearest individual article's** event if cosine distance <
   `1 - similarity_threshold = 0.50` and they share ≥ `entity_overlap_min = 1`
   entity.
3. Else seed a new event.

Three failures compound:

1. **Single-linkage chaining.** Matching to the nearest *member* (not the event
   centroid) lets a cluster spread across a whole dense topic region: A~B, B~C,
   C~D… Every World-Cup-adjacent article finds *some* near member and joins.
2. **`similarity_threshold = 0.50`** → an article attaches at up to 0.50 cosine
   distance (half-related). Members run right up to 0.50.
3. **`entity_overlap_min = 1` is useless against a recurring mega-entity.** Every
   World-Cup article shares the "Mundial 2026" entity, so the one-entity gate is
   trivially satisfied and cannot separate "player stats" from "opening ceremony."

Plus: no event-level **merge/dedup** (two near-identical events never reconcile)
and no **staleness** (events never stop attaching → 8-day spans). The
`_cluster_lock` (`application.py:714`) now prevents the *duplicate-seed race* that
made *two* buckets, but it was added after 06-07, so these legacy twins persist.

## Experiment (read-only, reproducible)

`scripts/cluster_reclustering_prototype.py` re-clusters the live corpus with the
**proposed** rules (centroid-linkage + a tighter distance bar + an
**entity-specificity** gate: attach only if the article shares ≥1 *specific*
entity — one appearing in < `cap`% of the pool — so a ubiquitous mega-entity
cannot merge unrelated stories). Run against the two World-Cup buckets (1,491
articles) and 40 healthy multi-source `es` events (the fragmentation control).

### Finding 1 — distance threshold alone cannot fix it

Centroid-linkage, specificity OFF, sweeping the distance bar:

| thr | MEGA result | CONTROL intact | dropped-below-2-sources |
|---|---|---|---|
| 0.50 | 1 cluster of 1490 (unchanged) | 28/40 | 2/40 |
| 0.45 | biggest still 1477 | 15/40 | 2/40 |
| 0.26 | biggest 114 | — | — |
| 0.22 | biggest 60 | 0/40 | 16/40 |
| 0.18 | biggest 25 | 0/40 | 20/40 |

Any bar loose enough to keep real events intact leaves the mega-bucket whole
(its centroid is a generic "World Cup" vector everything is near); any bar tight
enough to break it shatters real events and un-publishes 40–50% of them.
**Embedding distance is not separable** for "same event" vs "same topic."

### Finding 2 — entity-specificity is the decisive lever

At a fixed **event-preserving** distance bar (thr = 0.48), sweeping the
specificity cap:

| cap | MEGA biggest cluster | MEGA clusters | CONTROL intact | dropped-below-2 |
|---|---|---|---|---|
| 2% | **88** (from 1490) | 598 | 8/40 | 4/40 |
| 3% | 364 | 421 | 15/40 | 4/40 |
| 5% | 376 | 321 | 17/40 | 5/40 |
| 8% | 466 | 203 | 19/40 | 4/40 |
| 10% | 489 | 179 | 19/40 | 4/40 |

The specificity gate breaks the bucket **at a loose, event-preserving distance**;
distance alone could not. The recovered sub-clusters are recognizable real
events — e.g. "Mexico home-office / no-school decree for opening day" (Sheinbaum,
June 11), "how/where to watch the 2026 World Cup," "40-day countdown."

### Finding 3 — the residual cost is a stable ~10% publish-rate hit

`dropped-below-2-sources` (a currently-publishable event whose dominant fragment
falls below the 2-source bar) holds at **~4/40 ≈ 10%** across every cap. This is
the real cost, and it is an **upper bound**: the control events were themselves
built by the buggy 0.50 single-linkage, so part of that 10% is the new algorithm
*correctly* refusing weak grab-bags rather than a true regression. `topic`
(near-unique per article) is not a usable coherence metric; size + sources +
titles are.

## Decision (proposed)

Adopt **centroid-linkage + an entity-specificity gate** as the clustering rule:

1. Match an article to the nearest event **centroid** (not nearest member),
   distance < a moderate bar (~0.45–0.48 — *not* the aggressive 0.20 that
   shatters events).
2. Require a shared **specific** entity (IDF-weighted; cap tuned, start ~3–5% of
   the recent pool) to attach. A recurring mega-entity alone cannot merge.
3. **Staleness gate** — stop attaching to events older than N days (caps the
   8-day span; pairs with the parked story-arc archive, ADR-0013).

Complementary, separately tracked:

4. **Cleanup** — re-cluster the existing 26 mega-buckets under the new rule
   (merging the World-Cup twins would just make a bigger bad bucket; re-cluster
   is the right remediation).
5. **Event merge/dedup pass** — collapse event pairs with centroid distance < ε
   (closes the legacy twins the `_cluster_lock` can't).

### Rollout is validation-gated (do NOT flip blind)

The ~10% publish-rate delta is a product decision, and the isolated-pool
simulation is a proxy (production clusters compete against the *full* recent
corpus, not just these pools). Before changing live behavior:

- **Shadow mode** (same pattern as the triage gate, ADR-0030): compute the v2
  cluster assignment alongside v1, **log** the divergence + projected publish-rate
  delta, do not apply. Measure for a few cycles.
- **Held-out check**: manually label a sample of the "dropped-below-2" events to
  confirm they are genuinely weak grab-bags vs real coverage we'd lose.
- Tune `distance_bar` + `specificity_cap` on that validation set, then flip.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Just tighten `similarity_threshold` | Finding 1: no single distance separates same-event from same-topic; tightening shatters real events. |
| Keep single-linkage, raise `entity_overlap_min` | Mega-entity is shared by all; raising N to 2–3 still passes (World Cup articles share several generic entities). Needs *specificity*, not *count*. |
| Hard cap on cluster size | Arbitrary; splits a genuinely large breaking story at the cap. Specificity splits on *meaning*. |
| Merge the two World-Cup events | They're incoherent buckets; merging makes one bigger bad bucket. Re-cluster instead. |
| LLM adjudicates each attach | Cost + latency at ~7k articles/day; the embedding+entity signal is enough once specificity is added. |

## Status / next steps

- [x] Root cause confirmed on prod data
- [x] Read-only prototype + threshold/cap sweeps (`scripts/cluster_reclustering_prototype.py`)
- [ ] Implement v2 clustering behind a shadow flag
- [ ] Measure shadow divergence + publish-rate delta for N cycles
- [ ] Manual held-out validation of "dropped" events; tune cap/bar
- [ ] Flip + re-cluster the 26 legacy mega-buckets + merge legacy twins
