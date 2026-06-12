# Curator ADR-0026 — Offload embeddings to the Hostinger Ollama box

> *Status: accepted · Owner: Julian · Date: 2026-06-11*

## Context

The DO droplet's CPU-only Ollama embedded bge-m3 in **~13–17 s per article**
under scrape-time CPU contention (Ollama pegged ~310%, competing with Messor).
Because embeds are serialized through `_embed_sem(1)` (CPU Ollama saturates
under concurrent requests — ADR-0025), this capped the *entire* enrich pipeline
at **~4 articles/min**, against ~4/min inflow → the article queue sat
permanently at ~3,700 messages ≈ a 10+ h Reader freshness lag. The ADR-0025
concurrency work (prefetch 8) was wasted: 8 parallel enrich slots all funnelled
through one 15 s embed.

Measured 2026-06-11: lowering the intake age gate would NOT have helped — 100%
of the backlog was 6–12 h old (recent news, not stale), so it was a throughput
problem, not a staleness problem.

## Decision

Point prod embeddings at the **Hostinger VPS** (`82.112.250.139:32768`, the
rebuilt `srv1521854` — 16 GB, 4 vCPU, currently idle, also slated to run the
Editorial 12B model). It runs the **same bge-m3 model** over the same
OpenAI-compatible `/v1/embeddings` endpoint.

Critically: **same model → same 1024-dim vector space → zero re-embed, zero
clustering disruption.** The existing 17 k-article corpus stays valid; new
embeddings are directly comparable to old ones. (Switching to a different
provider — e.g. OpenAI — would have required re-embedding the corpus and broken
clustering for the 48 h recent-window during the transition. Rejected for that
reason despite being faster per-call.)

Change is a single env var on both curator services
(`infra/docker-compose.do.yml`), overridable via `EMBEDDINGS_BASE_URL`:

```
EMBEDDINGS_BASE_URL: http://infra-ollama:11434/v1   →   http://82.112.250.139:32768/v1
```

### Measured latency (from the droplet, through the firewall)

| | DO infra-ollama (contended) | Hostinger bge-m3 (warm) |
|---|---|---|
| per embed | ~15 s | ~2.2 s (0.36 s when fully warm) |
| pipeline rate | ~4/min | ~27/min |
| 3,740 backlog drain | ~15 h (never catches up) | ~2.3 h, then keeps real-time |

Port 32768 is firewalled to this droplet's IP only (DOCKER-USER iptables,
`-i eth0 ! -s 67.205.136.61`, persisted via netfilter-persistent).

## Consequences

- **Good**: backlog clears in ~2.3 h then stays real-time; DO droplet reclaims
  the Ollama embedding CPU for Messor/Curator/Postgres; no API cost; no
  migration.
- **Trade-off — hot-path cross-host dependency**: if the Hostinger box is down,
  embeds fail → the existing `_TRANSIENT_ERRORS` requeue path preserves the
  articles (no loss) and the pipeline pauses until it's back. Same failure shape
  as DO Ollama dying today. A future OpenAI fallback (`EMBEDDINGS_PROVIDER`
  swap) is the belt-and-suspenders option if this proves flaky.
- **Trade-off — Editorial contention**: when the nightly Editorial 12B batch
  runs (~20 min, ADR-0008), it shares the box's CPU and embeds slow briefly.
  Acceptable; Editorial is a once-daily batch.
- DO `infra-ollama` stays running (no other consumer today) but is no longer on
  the critical path; can be removed later to reclaim its ~1 GB.
