# Curator ADR-0025 — Concurrent article pipeline + stale-message intake gate

> *Status: accepted · Owner: Julian · Date: 2026-06-11*

## Context

The worker consumed with `prefetch_count=1`, set when CPU-only Ollama bge-m3
timed out under concurrent embedding requests. That serialized the ENTIRE
pipeline — but the slow stage is not the embed (~0.2–1 s): it's the enrich
LLM round-trip (8–17 s of DeepSeek network wait). Measured prod throughput:
**~4.3 articles/min**, against an inflow of ~4–6 k articles/day. Net drain ≈
zero, so the queue floated at ~3,500 messages — a **permanent 9–13 h
pipeline latency**. Reader symptom (reported by Julian 2026-06-11): "headlines
of 48 h are showing, the new ones aren't shown as new" — events updated *now*
were receiving articles harvested 9–13 h ago and bumping `freshness_at` with
stale-but-newest timestamps, while today's news waited in line.

## Decision

### 1. Parallelize what's slow, lock what's shared

- `rabbitmq.prefetch_count: 8` (config) — aio-pika dispatches each message
  callback as its own task, so prefetch IS the concurrency knob.
- `application.max_concurrent_articles: 8` (was 4) — the existing `_sem`
  gates total in-flight pipelines.
- **`_embed_sem = Semaphore(1)`** around every `embed.embed()` call (live
  path + both batch paths). This replaces global `prefetch=1` as the thing
  that protects CPU Ollama. Raise only if Ollama moves to GPU.
- **`_cluster_lock = Lock()`** around `cluster.run()` in the live path: two
  same-story articles clustering concurrently would each see "no neighbour"
  and seed duplicate events. Attach is ~1 s, so the lock costs little.
- Synthesis already had per-event in-flight locks + source-count gates
  (ADR-0006/0015) — unchanged, and now doing exactly the job they were
  designed for.

### 2. Stale-message intake gate (`max_article_age_hours: 48`, 0 = off)

In `_handle_event`, before any I/O: if `article.scraped_at` is older than
48 h, log `DROP stale message` and ack. The Reader feed window is 48 h
(Messor ADR-0015), so such articles can never surface — processing them is
pure waste. Today this drops nothing (queue head was 11 h old at worst); it
exists to bound damage in queue-flood pathologies (the 105k-message incident
of 2026-06-09 would have self-healed).

## Verification (local, 2026-06-11, real DeepSeek + real Ollama)

- 8 concurrent ENRICH calls in flight (prefetch honored, single consumer)
- **~70 articles/min sustained over 1,025 articles — 16× the prod rate**
- Zero Ollama timeouts (embed serialized)
- Two same-story duplicate articles enriched concurrently and attached to
  the SAME event twice over (no duplicate-event seeding) — cluster lock works
- 60 h-old message dropped at intake: `DROP stale message … (gate=48h)`

## Consequences

- Queue backlog (~3.5 k) drains in ~1 h after deploy instead of never;
  steady-state Reader latency drops from ~10 h to minutes.
- Breaking lane (ADR-0024) gets faster too: priority-9 messages now wait at
  most one enrich slot (~seconds), not one full enrich (~15 s).
- DeepSeek spend is unchanged per article; it's the same calls, sooner.
- The duplicate fast-path (ADR-0015/0018) is untouched — re-scrapes still
  SKIP before enrichment.
- If Ollama is ever upgraded (GPU / dedicated server), bump `_embed_sem` —
  it becomes the next bottleneck at roughly 60–120 articles/min.
