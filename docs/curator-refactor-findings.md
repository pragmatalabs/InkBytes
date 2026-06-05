# Curator — Refactor Findings & Budget Plan (Step 2)

> *Status: v1 · Owner: Julián de la Rosa · Last updated: 2026-06-04*
>
> Audit of what Curator does that is duplicated, misplaced, or improvable —
> with the **budget / local-first** track promised in
> [`messor-refactor-findings.md`](./messor-refactor-findings.md). Curator stays
> the owner of enrichment (ADR-0005); the goal is to spend the model only where it
> adds reader-facing value. Engineering truth: [`STATUS.md`](./STATUS.md).

## Summary

| # | Finding | Severity | Fix in one line |
|---|---|---|---|
| C1 | **ENRICH (Haiku) runs on every article**, but only ≥2-source clusters publish (309 enriched → 29 pages) | **P0 / budget** | Reorder `embed → cluster → enrich/synth`; LLM only on clustering survivors |
| C2 | **SYNTHESIZE re-runs on every new article** above threshold (no debounce) | **P0 / budget** | Coalesce: synthesize once per event, re-run only on material change |
| C3 | ENRICH may be **largely unnecessary for output** — synthesis reads raw `body_text`, not enrichment | **P1 / budget** | Measure: replace the cluster's entity gate with **local NER**; reconsider per-article LLM enrich |
| C4 | No local-first pre-pass (lang/NER/keywords/near-dup) — all derived signal comes from the paid model | P1 / budget | Add a cheap local "Skill 0" (recovers the old Messor-NLP budget virtue, in Curator) |
| C5 | Two reclustering code paths (`scripts/recluster.py` vs `application._recluster_event`) overlap | P1 | Extract one shared recluster core both call |
| C6 | No idempotency guard in `_handle_event` — a redelivered message re-enriches (re-pays) | P2 | Skip enrich/embed when `enriched_at` is set (unless forced) |
| C7 | Three different text-truncation magic numbers (embed 4000, enrich 6000, synth 3500) | P2 | Name them in config |
| C8 | Schema restated: `contracts/article_v1` vs shared-kernel `Article`; `/status` counts vs B6 health | P3 (accept) | Deliberate boundaries — document, don't merge |

## Findings (detail)

### C1 — ENRICH runs on every article (the headline budget leak) — P0

`_handle_event` does, per article: persist raw → **ENRICH (Haiku call)** → embed →
cluster → maybe synth. So the expensive per-article LLM call fires for **all 309
articles** even though only **29 pages** ever publish (events with ≥2 distinct
sources). Most enrichment spend never reaches a reader.

**Reorder to `embed → cluster → (enrich + synth only for ≥2-source survivors)`.**
Embeddings are ~$0.02/M (negligible), so embedding everything is cheap; the Haiku
ENRICH then runs only on articles that actually land in a publishable cluster.

**Blocker:** the cluster skill's entity-overlap gate consumes ENRICH's entities (see
C3). Reordering requires the gate to run on something cheaper — embeddings alone, or
**local NER** (C4).

### C2 — SYNTHESIZE re-runs on every new article — P0

In `_handle_event`, whenever `source_count >= min_sources_to_publish`, it calls
`synthesize.run(event_id)`. As articles trickle in, a growing event is **re-synthesized
on every arrival** (each a full Haiku call that reads *all* the event's articles). A
10-article event can trigger ~9 synthesis calls for one page. There is no debounce or
change-detection.

**Coalesce synthesis:** synthesize once when the event first crosses the threshold,
then re-synthesize only on a **material change** (a new *distinct* outlet) and/or on a
short debounce timer / end-of-batch sweep — not on every article. Synthesis is the
token-heavier call, so this is a large saving on multi-article events.

### C3 — ENRICH may be largely unnecessary for the output — P1 (measure)

Synthesis (`synthesize.py`) builds its prompt from raw `articles.body_text` and
regenerates `entities_top` itself — it **does not read** the per-article ENRICH
output. Pages likewise carry synthesis-derived entities, not ENRICH's. So today
ENRICH's `topic/sentiment/factuality/summary/entities` feed mainly **(a)** the
clustering entity-overlap gate and **(b)** per-article admin metadata — *not* the
reader-facing page.

That means the expensive per-article ENRICH is, for output purposes, mostly optional.
**Recommendation:** replace the cluster gate's entity source with **local NER** (cheap)
and measure page quality with ENRICH reduced to clustering survivors (or dropped for
clustering and run only where its metadata is actually consumed). Validate against
quality before committing — ENRICH may still help factuality/topic features later.

### C4 — Add a cheap local pre-pass ("Skill 0") — P1 / budget

This is where the old Messor `.nlp()` budget virtue belongs now (in Curator, ADR-0005
intact). Candidate local steps, in cost order:

1. **Local language confirm** (`fasttext`/`langdetect`) — don't ask the model. (Messor
   already language-filters at harvest.)
2. **Local NER + keywords** (spaCy or a small local model) → powers the cluster gate
   cheaply, enabling the C1 reorder.
3. **Near-duplicate collapse** (MinHash / embedding sim) → wire-copy duplicates enriched
   once per group, not N times.
4. **Local embeddings option** (`sentence-transformers`, e.g. `bge-small`) → zero
   embedding spend, traded vs quality/infra.
5. **Model tiering** — cheap/local model for any retained per-article enrichment;
   reserve Haiku for SYNTHESIZE (the reader-facing piece). Anticipated in
   `mvp-plan.md` §6.

### C5 — Two reclustering paths — P1

`scripts/recluster.py` (bulk: null all `event_id`, re-cluster everything, re-synthesize)
and `application._recluster_event` (per-event: detach members, re-run ClusterSkill)
implement overlapping logic, and the script re-implements the synth loop. Extract a
single reusable recluster core used by the one-off script **and** the `event.recluster`
command handler.

### C6 — No idempotency guard — P2

RabbitMQ is at-least-once. `_handle_event` upserts the raw article (idempotent) but then
**unconditionally** re-runs ENRICH + embed, so a redelivered or replayed message pays
for enrichment again. Add a cheap guard: skip ENRICH/embed when `articles.enriched_at`
is already set (unless an explicit `force` is passed).

### C7 — Scattered truncation magic numbers — P2

Embedding uses `title + text[:4000]`, ENRICH `text[:6000]`, SYNTHESIZE `body_text[:3500]`.
Three undocumented limits. Promote to named `config` values so token/cost behaviour is
tunable and visible (ties into the Backoffice Curator Settings screen).

### C8 — Restated schemas / counts — P3 (accept, document)

`contracts/article_v1.py` restates a subset of the shared-kernel `Article`; Curator's
`/status` recomputes counts the Backoffice B6 health also computes. Both are **deliberate
boundaries** (RabbitMQ JSON contract across the Messor v1 / Curator v2 pydantic split;
defensive health over HTTP), not bugs. Keep, but note them in `contracts.md` so they
don't silently drift.

## Proposed target pipeline (budget-optimal)

```text
per article:  persist raw ──▶ embed (cheap) ──▶ Skill 0 local pre-pass (lang, NER, near-dup)
                                                          │
                                                          ▼
                                                 CLUSTER (gate on local NER + cosine)
                                                          │  event reaches ≥2 distinct sources?
                                          ┌───────────────┴───────────────┐
                                         no                               yes
                                          │                                │
                                   (stop — no LLM)        ENRICH survivors (if still needed)
                                                                 + SYNTHESIZE (debounced, once)
```

Net effect: LLM spend scales with **published events**, not **harvested articles**.

## Fix plan (Code-agent tabs)

> Start with a **measurement spike** — the reorder is a real architecture change and
> should be justified against live `model_usage`, not assumed.

### Tab C0 — Budget spike (decide before building)
> `cd Curator/apps/curator`. Using live `backoffice.model_usage` + `public` counts,
> quantify today's spend split (enrich vs synth, per article vs per page) and the
> redelivery/re-synthesis multiplier. Prototype **local NER** (spaCy) for the cluster
> gate and compare clusters/page quality vs the current LLM-entity gate on the existing
> 309 articles. Output: a go/no-go + sizing for C1–C4. Record as a Curator ADR.

### Tab C1+C2 — Reorder + debounce (the two P0 levers)
> Implement `embed → cluster → enrich/synth-for-survivors` and **coalesce synthesis**
> (synthesize once per event on threshold crossing; re-run only on a new distinct
> source or a short debounce). Gate behind config flags so it can be rolled back.
> Verify pages still generate for the known multi-source events; compare spend.

### Tab C5+C6+C7 — Consolidation & safety
> Extract one shared recluster core (script + `event.recluster` command both call it).
> Add the `_handle_event` idempotency guard (skip enrich/embed when `enriched_at` set,
> unless forced). Promote the three truncation limits to named config and surface them
> in Backoffice Curator Settings.

## What NOT to do

- Do **not** move enrichment back to Messor (ADR-0005). Local pre-pass lives in Curator.
- Do **not** drop the ≥2-source publish rule — it's the quality floor *and* the budget gate.
- Do **not** commit the reorder without the C0 spike confirming page quality holds.
