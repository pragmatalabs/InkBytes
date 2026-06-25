# Curator ADR-0033 — Event lifecycle + three-clock importance ranking (the "skip the noise" fix)

> *Status: **proposed** · Owner: Julian De La Rosa · Date: 2026-06-25*
> *Addresses the core product gap: InkBytes promises "one elegant page per event, today's news, pay to skip the noise" but currently surfaces a 4,203-event pile where 78% of the "last 24h" feed is stale resurfacing.*

## Context

The Reader feed ranks **all** published events by `pages.freshness_at = max(scraped_at)`
DESC (ADR-0017). That single number is overloaded — it stands in for *when the
story happened*, *when it last meaningfully changed*, and *how it should rank* —
and there is **no recency gate, no archiving, and no notion of importance**.

Measured in prod (2026-06-25, 111k articles / 4,203 published events):

| Metric | Value | Implication |
|---|---|---|
| Published events (all rankable) | **4,203** | the feed is an ever-growing pile |
| In "last 24h" feed (by `freshness_at`) | 464 | … |
| …**genuinely new** (by `first_seen_at`) | **102** | **362 (78%) are OLD events re-floated by a tangential article** |
| No activity in 7d (never archived) | **2,120** | archiving (ADR-0013) is disabled (`story_arcs = 0`) |
| Published events with only 2 sources | 2,013 (48%) | importance is uniform — routine ≈ breaking |

Symptoms reported (all explained by the above): a 9-day-old story shown as if it
happened today; a 12h-old minor article out-ranking a major update; the same real
event fragmented across pages (e.g. "Alan Greenspan Dies at 100" = 6 events — that
is clustering, see ADR-0031, and is complementary to this ADR).

## Decision

### 1. Three clocks (stop conflating)

| Clock | Meaning | Moves when | Drives |
|---|---|---|---|
| `first_seen_at` (reuse — already immutable) | when the story happened | never | the **displayed date** + the "is this old?" gate |
| `last_material_update_at` (**new** column) | last *substantive* development | only on a **material** new article | ranking recency |
| `importance_tier` / `importance_score` (**new**) | how big the story is | creation + material update | ranking weight + breaking gate |

`freshness_at` stays as "last touch" for diagnostics but is **no longer the feed
sort key**. Hard rule it enforces: an event whose `first_seen_at` is older than the
lane window can **never** enter Breaking/Today and always shows its **original
date** — a tangential article today does not move `last_material_update_at`, so it
cannot catapult to the top (fixes the 362 resurfaced events).

### 2. Rules vs Skills

**Rules (deterministic, every article/event — cheap, no LLM):**
- **Old-as-today guard** — `first_seen_at > window` ⇒ excluded from Breaking/Today; display original date.
- **Vault trigger** — no material update in `conclude_after_days` (proposed 7) ⇒ `status='concluded'` → `story_arcs`, removed from the live feed (enables the dormant ADR-0013).
- **Feed window** — live feed scoped to last 72h of `last_material_update_at`.
- **Breaking velocity** — existing ADR-0024 signal (≥2 pulse outlets within 60 min): necessary, no longer sufficient.

**Skills (LLM judgment, only where rules can't decide):**
- **`UpdateMaterialitySkill`** — on attach-to-existing-event, classify *material development* vs *tangential re-mention* (title+lede vs the event's current summary). Material → bump `last_material_update_at` + "Updated" badge; tangential → attach silently, **no re-float**. Cheap; can run on the same small local model as the triage gate (ADR-0030, `llama3.2:3b` on Hostinger) to stay ~free. Fail-open = treat as tangential (conservative: don't re-float on uncertainty).
- **`ImportanceSkill`** — rate each event `breaking | major | notable | routine | filler` + a 0–100 score + one-line "why it matters." Computed at synthesis (the cluster context is already loaded — likely a field on `PageV1`, no extra call) and re-evaluated on material update. This is the "what's more important" signal.

### 3. The feed becomes lanes (not one recency pile)

- **🔴 Breaking (24h):** `importance ≥ major` ∧ velocity signal ∧ `first_seen_at` < 24h.
- **📰 Today / Live (72h):** material activity in 72h, ranked by the formula below.
- **🔄 Developing:** older event with a **material** update — original date + "Updated" badge, ranked by real recency (never jumps to Breaking).
- **🗄️ Historical Vault:** `concluded` events, searchable, excluded from the live feed.

### 4. Ranking formula (replaces `ORDER BY freshness_at`)

```
rank_score = importance_weight(tier) · decay(now − last_material_update_at) + global_outlet_bonus
```
Importance is a **multiplier**, recency is a **curve** (e.g. `exp(−Δ/τ)`, τ≈24h),
`first_seen_at` is a **hard gate**, `status='concluded'` drops to the vault. A
`major` update out-ranks a `routine` 12h item even if slightly older.

### 5. Data model

Migration (events): `+ last_material_update_at TIMESTAMPTZ` (backfill = `first_seen_at`),
`+ importance_tier TEXT`, `+ importance_score INT`. `status` gains `concluded`
(`story_arcs` already exists, migration 010). No new clock column needed —
`first_seen_at` already never moves.

## Projected impact (shadow query, 2026-06-25)

| | Today | Under this ADR |
|---|---|---|
| Live feed candidates | **4,203** (all published) | **~744** (new/updated in 72h) → vault holds 2,120+ |
| "Last 24h" feed | 464 (102 real + **362 resurfaced**) | **~102 genuinely new**; 362 demoted to Developing w/ original date |
| Breaking lane | n/a (everything competes on recency) | ~102 new ∩ `major` ∩ velocity → tens, not thousands |

## Alternatives considered

| Option | Rejected because |
|---|---|
| Just add a 72h `WHERE` recency gate to the feed | Stops the pile but not resurfacing (a touched old event still shows as "now") and ignores importance — a routine item still beats a major update. |
| Rank by `source_count` as importance | Coarse proxy; a 2-source genuinely-major story loses to a 6-source routine roundup. The skill judges newsworthiness, not just coverage. |
| Pure-LLM ranking (score every event each request) | Too slow/expensive at feed-serve time; importance is computed once at synthesis and cached. |
| Use `published_at` (outlet date) as the clock | Outlet dates are null/future/wrong (see `freshness-at` memory). `first_seen_at` is Curator-stamped and reliable. |

## Consequences

- The feed becomes **today's news** (~hundreds), not an archive (~thousands) — the core promise.
- Resurfacing is structurally impossible (old `first_seen_at` can't enter Breaking/Today; tangential attach can't move the recency clock).
- Two new LLM touchpoints, both cheap/gated (materiality on the small triage model; importance folded into synthesis). Fail-open everywhere.
- Composes with **ADR-0031** (clustering precision — shrinks fragmentation so lifecycle/importance operate on clean events), **ADR-0024** (velocity breaking), **ADR-0029** (manual Breaking Desk), **ADR-0013** (story_arcs vault — finally enabled).
- Tunable: windows (24h/72h/7d) and the 5-tier scale are config knobs, validated via shadow before flipping.

## Rollout (cheapest impact first)

1. **P0 — rules only, no LLM:** add the three clocks + vault trigger + 72h feed window + "don't bump the material clock on tangential attach" (deterministic proxy first: only core-cluster + recent). Instantly: feed 4,203 → ~744, resurfacing 362 → 0.
2. **P1 — `UpdateMaterialitySkill`:** replace the materiality heuristic with the LLM classifier (precise developing-vs-noise).
3. **P2 — `ImportanceSkill` + lanes + ranking formula:** importance-weighted ranking + the Breaking gate.

Each phase ships behind a flag and is shadow-measured before it changes the live feed.
