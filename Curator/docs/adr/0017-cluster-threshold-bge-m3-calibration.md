# ADR-0017 — Cluster similarity threshold lowered to 0.50 for bge-m3

> *Status: accepted · Owner: Julian · Date: 2026-06-08*

## Context

`ClusterSkill` merges two articles into the same event when:

1. Cosine similarity ≥ `similarity_threshold` **and**
2. They share ≥ `entity_overlap_min` named entities **and**
3. Both fall within the `recent_window_hours` window

The threshold was originally set at **0.78** (ADR-0002) for OpenAI
`text-embedding-3-small`.  It was later lowered to **0.62** when bge-m3
(Ollama, 1024-dim) replaced OpenAI embeddings — because 0.78 produced zero
clusters with the new model.

After **72 hours of production observation** Julian found that articles with
~0.50 cosine similarity (bge-m3) are effectively the same story from different
outlets.  At 0.62 those pairs were falling below the threshold and spawning
separate events instead of merging — fragmenting coverage of the same story
into multiple single-source pages.

## Decision

Lower `similarity_threshold` from **0.62 → 0.50**.

The entity overlap gate (`entity_overlap_min: 1`) remains the primary quality
guard against false merges.  Two articles that happen to land at ≥0.50
cosine similarity but cover unrelated stories will still not cluster unless
they share at least one named entity.

## Why the thresholds differ by model

`text-embedding-3-small` (1536 dims, OpenAI) and `bge-m3` (1024 dims, BAAI)
have different absolute similarity distributions.  bge-m3 is trained with a
different contrastive objective and different corpus — same-semantic pairs
routinely score lower in raw cosine similarity than they would under OpenAI
embeddings.  A threshold calibrated on one model is not portable to the other.

| Model | Threshold | Observation |
|---|---|---|
| `text-embedding-3-small` | 0.78 | ADR-0002 original |
| `bge-m3` | 0.62 | Too strict — same-story articles under threshold |
| `bge-m3` | **0.50** | Correct — 72h empirical calibration 2026-06-08 |

## What changes

| File | Change |
|---|---|
| `env.yaml` | `similarity_threshold: 0.62` → `0.50` |
| `env.example.yaml` | Same, with updated comment |
| `config.py` `ClusterCfg` | Default `0.62` → `0.50`, comment updated |

No migration of existing articles is needed — the threshold only affects
**incoming** articles as they are clustered.  Existing fragmented events
can be re-clustered with `python scripts/recluster.py` if backfill is desired.

## Consequences

- **Positive:** same-story articles from different outlets merge into one
  event instead of spawning separate single-source events.
- **Positive:** more multi-source events → more synthesis runs → more
  published pages.
- **Risk:** marginally related articles could merge if they share one entity.
  Mitigated by `entity_overlap_min: 1`; tunable upward if false merges appear.
- **Tunable live:** `similarity_threshold` is in `_DB_SETTINGS_MAP` and is
  overlaid from `backoffice.curator_settings` every 30 s — no redeploy needed
  to adjust further.
