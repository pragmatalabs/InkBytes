# Curator ADR-0031 — Clustering precision: entity-specificity gate vs mega-buckets

> *Status: **accepted** — implemented 2026-06-25 (committed `6d94ef0`, ships DORMANT behind `clustering.precision_mode`; not deployed) · Owner: Julian · Date: 2026-06-14*
>
> **Implementation (flag-gated, default off — legacy single-linkage untouched):** migration 019 `events.centroid` + `scripts/backfill_event_centroids.py` (seed existing events before flipping); `cluster.py::_run_precision` does centroid-linkage (`events.centroid <=>`, distance < `precision_distance`=0.48) + the entity-specificity gate (share ≥1 entity in ≤ `specificity_cap`=0.05 of the recent pool) + a staleness gate (skip events with no material update in `recent_window`) + the shared `_maybe_flag_breaking` helper. Enable via `infra/.env` `PRECISION_MODE=true` **after** backfilling centroids. Verified live (dev): a WC article with specific entities attaches (d=0.296); the same embedding with only ubiquitous entities **seeds** — the gate blocks the mega-bucket merge (Finding 2). Follow-ups still open: re-cluster the ~308 legacy mega-buckets + the event merge/dedup pass (items 4–5 below).

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

## Update 2026-06-25 — distance tightened + ≥2 shared entities + live-blog gate (clean-slate reset)

When the precision gate (`precision_distance=0.48`, share **≥1** specific entity) was
exercised against a **flat re-cluster of a week's real corpus from scratch** (dev,
4,008 bge-m3-embedded articles, `scripts/recluster_fresh.py`), the World Cup **still
rebuilt a 363-article blob**. Two reasons the original bar wasn't enough:

1. **Same-genre embeddings are too close.** Spanish WC match reports sit well inside
   0.48 of each other regardless of which match — embedding distance alone can't
   separate them; the entity gate has to.
2. **The accumulating-union magnet.** A cluster's `spec_ents` is the *union* of all
   members' specific entities, so a big WC cluster accumulates `{argentina, portugal,
   messi, ronaldo, …}` and *any* new WC article shares ≥1 → it joins. Sharing **one**
   specific entity is too weak once a cluster is large.

**Fix (validated on the dev corpus):**
- `precision_distance` **0.48 → 0.34 → 0.30** — biggest lever; collapses the top cluster 363 → 80.
- new `specificity_min_shared` (default **2**) — an article must share **≥2** specific
  entities with the event; a lone shared team/region can't merge distinct stories.
  `cluster.py::_run_precision` step 3 now counts shared specifics instead of `EXISTS`.

**Prod-scale correction — the fraction cap doesn't hold across corpus sizes.** The
first prod dry-run (25,225 articles in the 72h reset window) rebuilt a **421-article**
WC blob despite 0.34/min2. Cause: `specificity_cap` was a *fraction of pool* (`cap·n`),
so at n=25k the "specific" threshold was ~1,261 articles — team names ("Argentina",
"Portugal") fell under it and acted as merge magnets. At dev's n=4k the same 0.05 gave
a ~200 threshold, which is why dev looked fine. **Fix: replace the fraction with an
ABSOLUTE doc-frequency threshold `specificity_max_df` (default 90)** — window-independent.
With `distance=0.30, max_df=90, min_shared=2` the prod top clusters are all coherent real
events (Venezuela quake 94/32, France/Lecornu 89/28, Portugal–Uzbekistán 85/23, Mexico's
WC campaign 71/13, UK Labour 67/21) — no blob. `specificity_cap` kept only as a legacy
fallback (used iff `max_df<=0`); the live path skips the pool-count query when max_df is set.

Result: the WC splits into coherent real events — *Colombia elections* (80/24),
*Ronaldo's six-Mundiales record* (77/25), *Messi/Golden-Boot race* (51/19),
*Ábalos sentence* (46/9) — no mega-bucket. Publishable (≥2 src) events: ~328/week.

**Residual = a *content* problem, not a distance one:** the stubborn remaining cluster
is daily **live-blog / roundup** pages (*"en VIVO: últimas noticias de hoy"*, *"qué
partidos se juegan hoy"*, *"Tabla de posiciones EN VIVO HOY"*, *"AL MOMENTO:"*,
date-only titles). Gated at publish via `services/content_filter.py` (extends ADR-0021)
— precision-first, single-match previews ("previa, horario y dónde ver") stay KEPT.
Tests: `test_content_filter.py` 24/24 FLAG, 14/14 KEEP.

**Rollout = clean-slate "keep recent" reset** (chosen over re-clustering ~104 legacy
mega-buckets, which is the bigger/irreversible op for data that's mostly outside the
freshness window anyway): `pg_dump` backup → `DELETE FROM events` (cascades pages/arcs,
NULLs `article.event_id`) + `DELETE FROM articles WHERE scraped_at < NOW()-7d` (cascades
entities) → `recluster_fresh.py --apply` (0.34/min2) → `--synthesize-pending --since-hours
168` (scoped, published-aware) → conclude. Pre-launch + freshness-gated feed make this the
cheapest, lowest-risk path to a clean feed.

## Status / next steps

- [x] Root cause confirmed on prod data
- [x] Read-only prototype + threshold/cap sweeps (`scripts/cluster_reclustering_prototype.py`)
- [x] Implement v2 clustering behind `precision_mode` (centroid-linkage + specificity gate)
- [x] Tighten the bar after from-scratch validation: distance 0.34 + `specificity_min_shared=2`
- [x] Live-blog/roundup publish gate in `content_filter.py` (+ tests)
- [ ] Deploy the tightened params to prod (`PRECISION_DISTANCE=0.34`, `SPECIFICITY_MIN_SHARED=2`)
- [ ] Execute the clean-slate reset on prod (backup → wipe → `recluster_fresh` → scoped re-synth)
