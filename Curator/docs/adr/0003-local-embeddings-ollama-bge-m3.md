# ADR-0003 — Local-first embeddings via Ollama (bge-m3)

> *Status: Accepted · Owner: Julián de la Rosa · Date: 2026-06-04*
>
> Supersedes the "Migration to local embeddings (v1 option)" follow-up in
> [ADR-0002](./0002-pgvector-embeddings-clustering.md). The CLUSTER design
> (pgvector cosine `<=>` + entity-overlap gate) is unchanged; only the embedding
> *provider* and vector *width* change.

## Context

ADR-0002 chose OpenAI `text-embedding-3-small` (1536-dim) for the CLUSTER skill.
It works, but it is the one piece of the pipeline that:

- adds a **second external paid vendor** (separate from Anthropic) and a second
  key/failure point — "OpenAI down ⇒ articles enrich but never cluster";
- runs on **every harvested article** (embedding is the cheapest stage, so we
  *want* to keep embedding everything — that is what enables the C1 reorder in
  [`docs/curator-refactor-findings.md`](../../../docs/curator-refactor-findings.md)),
  which means it is also the stage most coupled to an external dependency.

The owner's directive: **make the embedding tier part of the deployed project,
running locally** — "why not a local embedder, and reserve LLMs for specific
enrichment skills?" Decision constraints (locked):

- **Embeddings-only** local for now. ENRICH + SYNTHESIZE stay on Anthropic
  Haiku 4.5 (the reader-facing quality bet is not worth gambling yet).
- **Same DigitalOcean droplet, CPU** (no GPU). Deploy target D6.
- **Bilingual EN/ES** is a product mandate (LATAM outlets) — the local embedder
  must be multilingual.

## Decision

Run a **local [Ollama](https://ollama.com) service** as first-class deployed
infra (a container alongside Postgres / RabbitMQ / MinIO) and use it to serve
the **`bge-m3`** multilingual embedding model (1024-dim) for the CLUSTER skill.

- Curator's `EmbeddingService` gains a `provider` switch: `ollama` (default,
  deployed) | `openai` (fallback). Ollama exposes an **OpenAI-compatible**
  `/v1/embeddings` endpoint, so the existing `AsyncOpenAI` client is reused with
  a `base_url` — the call site (`embeddings.create(model=…, input=…)`) is
  unchanged.
- `articles.embedding` migrates `vector(1536) → vector(1024)` (migration 005).
  Old vectors cannot be re-cast; they are cleared and the pipeline re-embeds.
- The cosine gate stays at `0.62` (see "Threshold" below).

### Why bge-m3 — measured, not assumed

A read-only spike (`scratch_embed_spike.py`, not committed to the pipeline)
re-embedded the **794 already-embedded articles** (391 in 81 multi-member
events; ~11.6k labelled pairs) with each candidate and measured separation of
*same-event* vs *different-event* cosine similarity. Higher Youden's J = cleaner
separation.

| Embedder | dims | mean intra | mean inter | **Youden J** | best T | rec@0.62 / fp@0.62 |
|---|---|---|---|---|---|---|
| OpenAI `text-embedding-3-small` (baseline) | 1536 | 0.567 | 0.267 | **0.769** | 0.40 | 0.305 / 0.010 |
| **`bge-m3`** (chosen) | 1024 | 0.592 | 0.408 | **0.747** | 0.48 | **0.304 / 0.017** |
| `nomic-embed-text` | 768 | 0.763 | 0.593 | 0.761 | 0.67 | 0.993 / 0.314 |

Reads:

1. **`bge-m3` essentially matches OpenAI** (J 0.747 vs 0.769, ~3%) — and the
   labels were themselves produced by the OpenAI-based clustering, a bias that
   *favours* OpenAI, so the true gap is smaller. Local embeddings are viable.
2. **The 0.62 threshold transfers.** At the production operating point (cosine
   ≥ 0.62, run deliberately precision-heavy), `bge-m3` gives rec 0.304 / fp
   0.017 vs OpenAI's 0.305 / 0.010 — near-identical gate behaviour. No retune
   needed to preserve current clustering; we *could* drop to ~0.48 later for
   more recall.
3. **`nomic` rejected** despite its tiny 274 MB footprint: English-only (fails
   the ES mandate) and its similarity scale is shifted so far up that 0.62
   matches almost everything (fp 0.314 — clustering would collapse). It would
   need its own threshold *and* still lose bilingual.

### Why Ollama (vs in-process sentence-transformers / spaCy)

- **OpenAI-wire-compatible** → minimal Curator change (one `base_url`); no
  `torch`/`sentence-transformers` bloating Curator's venv — the heavy ML stays
  in the Ollama process.
- **One runtime** that can later also host a small enrichment SLM if we ever
  extend the local tier (model-tiering, C4 #5) — without re-architecting.
- **CPU-friendly for embeddings**: `bge-m3` resident ≈ 1.2 GB; observed
  ≈ 120 ms/embed on CPU ⇒ ≈ 3–4 min to embed all ~1.8k articles. Embedding runs
  on every article, so this is steady-state, not one-off.

## Consequences

**Positive**
- Removes the OpenAI dependency from the steady-state pipeline; no embedding
  spend; one fewer external key/failure point.
- Multilingual embedder aligns with the LATAM/ES product direction.
- `provider` switch keeps OpenAI as a drop-in fallback (set
  `EMBEDDINGS_PROVIDER=openai` + `OPENAI_API_KEY`).

**Negative / risks**
- **New deployed dependency**: Ollama must be up for clustering to work
  (mirrors the old "OpenAI down" risk, now local). Curator `depends_on` it;
  prod healthcheck required.
- **Droplet RAM**: +~1.5 GB resident for the model. The D6 droplet must be
  sized accordingly (≈ 16 GB once the full stack + Ollama co-reside).
- **EN-corpus caveat**: the spike corpus was 99.5 % English (LATAM/ES outlets
  not yet harvested), so `bge-m3`'s *multilingual* edge is asserted from model
  design, not measured. Re-validate once ES articles exist.
- **Migration is destructive to vectors**: all `articles.embedding` are cleared
  and re-embedded (data-safe — the source `body_text` is intact).

## Rollout

1. `embeddings.provider` flag + `base_url` in config; `EmbeddingService`
   branch (this ADR's code).
2. Migration `005_embedding_dim_1024.sql`: drop the IVFFlat index, widen the
   column to `vector(1024)` (clearing old data), recreate the index.
3. `ollama` + `ollama-bootstrap` (pull `bge-m3`) services in the dev compose
   (`full` profile) and the prod compose; `curator depends_on ollama` with
   `EMBEDDINGS_*` env wiring.
4. Re-embed the existing corpus (pipeline does this on the next pass; a manual
   re-embed pass can backfill immediately).
5. Confirm 0.62 holds on a held-out slice once ES articles land.

## Follow-ups

- Re-run the separation spike when the corpus has meaningful ES volume.
- Re-tune IVFFlat `lists` (still ~sqrt(rows)) — unchanged from ADR-0002.
- If the local tier proves itself, evaluate a small enrichment SLM on the same
  Ollama (separate ADR; out of scope here — ENRICH/SYNTH stay on Haiku).
