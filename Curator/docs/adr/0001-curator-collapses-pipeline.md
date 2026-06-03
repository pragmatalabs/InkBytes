# ADR-0001 — Curator collapses Entopics + Synochi + Unitas for v0

* **Status**: Accepted
* **Date**: 2026-06-02
* **Deciders**: Julián de la Rosa
* **Relates to**: [`InkBytes/docs/mvp-plan.md`](../../../docs/mvp-plan.md), [`Messor/docs/adr/0005`](../../../Messor/docs/adr/0005-messor-curator-responsibility-split.md)

## Context

The long-term InkBytes architecture has three independent monorepos
between Messor (stage 1, harvester) and the reader:

- **Entopics** — NER + topic modeling + sentiment (stage 2)
- **Synochi** — cross-source synthesis + entity relations (stage 3)
- **Unitas** — clustering + similarity + QA + persistence (stage 4)

These folders exist on disk today as half-finished Python projects.
Building three production-grade services in five days for the MVP is not
realistic.

At the same time, modern LLMs (Anthropic Claude Haiku 4.5) can do
high-quality NER + topic classification + summarisation + sentiment in
one structured call, and clustering in v0 needs only embeddings +
cosine distance + an entity-overlap rule.

## Decision

For v0, **collapse Entopics + Synochi + Unitas into a single Python
service named `Curator`**, with three internal "skills":

1. **Skill 1 — ENRICH** (replaces Entopics)
   One Haiku call per article. Returns
   `{topic, summary_50w, sentiment, factuality, keywords_canonical, entities[]}`.

2. **Skill 2 — CLUSTER** (replaces Unitas)
   OpenAI embedding + pgvector cosine search + entity-overlap gate.
   No LLM here; pure math + SQL.

3. **Skill 3 — SYNTHESIZE** (replaces Synochi)
   One Haiku call per event once `source_count ≥ min_sources_to_publish`.
   Produces `{headline, synthesis_md, evidence_rail[], entities_top[]}`.

The skills live in `apps/curator/skills/{enrich,cluster,synthesize}.py`.
A single async event loop ingests Messor's `event.article.scraped`
events and runs the pipeline.

## Consequences

**Positive**

- One service to deploy, one image, one log stream, one set of secrets.
- Fits the one-week MVP timeline.
- Lower operational complexity — three RabbitMQ exchanges become one
  outbound exchange (`curator`).
- Easier reasoning for new contributors: one process, three function
  calls, no IPC.
- The LLM removes ~80% of the NLP plumbing the three legacy services
  needed (NLTK, spaCy, custom tokenizers, similarity-graph builders).

**Negative**

- Coupling: a bug in one skill takes down the whole pipeline. Mitigated
  by the asyncio semaphore — failures isolate per article.
- Scale ceiling: a single process saturates around ~10k articles/hour.
  When we hit that, we split back into three services (see "Reversal
  path" below). Plenty of headroom for v0.
- Vendor concentration: one LLM provider (Anthropic) does both enrichment
  and synthesis. Acceptable risk given the cost/quality argument; we
  keep a Gemini Flash fallback in mind.

## Reversal path (post-v0)

The skill boundaries match the future service boundaries by design:

| v0 skill | Future service | What changes |
|---|---|---|
| `EnrichSkill` | `Entopics/apps/enricher` | move `prompts/enrich.md` + the skill class; expose a RabbitMQ consumer for `event.article.scraped`; publish `event.article.enriched` |
| `ClusterSkill` | `Unitas/apps/clusterer` | consume `event.article.enriched`; publish `event.event.updated` |
| `SynthesizeSkill` | `Synochi/apps/synthesizer` | consume `event.event.threshold-reached`; publish `event.page.published` |

The Pydantic contracts in `apps/curator/contracts/` already model the
intermediate payloads, so the split is mechanical when scale demands it.

## Alternatives considered

1. **Build all three services for v0** — rejected. Five days isn't
   enough; we'd ship none of them.
2. **Keep v0 as one Python file inside Messor** — rejected. Messor is a
   harvester (ADR-0005). Mixing concerns there would re-create the
   bleed we just cleaned up.
3. **Use LangGraph / CrewAI / AutoGen for the three skills** — rejected.
   Three sequential function calls don't need a framework. The learning
   curve and indirection cost outweigh the benefit.
4. **Skip clustering, treat each article as its own page** — rejected.
   The whole product proposition is "one page per event", not "one page
   per article".

## Follow-ups

- ADR-0002 (when scale demands it): split Curator into Entopics +
  Synochi + Unitas as separate services.
- ADR-0003 (when prompts mature): formalise the prompt-versioning policy
  beyond what `docs/prompts.md` describes.
