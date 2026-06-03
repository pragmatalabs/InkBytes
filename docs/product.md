# InkBytes — Product & Business Layer

> *Status: v1 · Owner: Julián de la Rosa · Last updated: 2026-06-02*
>
> The business/strategy framing for InkBytes. Ported from the Notion hub so the
> repo carries the "why," not just the "how." Engineering truth lives in
> [`STATUS.md`](./STATUS.md) and [`mvp-plan.md`](./mvp-plan.md); the canonical
> Notion mirror is the [InkBytes hub](https://www.notion.so/373eca56ed94818da548f66ca288593a).

## 1. Mission

Transform how people consume and understand the news by delivering **accurate,
unbiased, comprehensive** coverage — aggregated and refined from many trusted
sources by an AI layer. One elegant page per event. The reader pays to skip the
noise.

Tagline: *Your Source for Comprehensive News.*

## 2. The problem

Today's news landscape is **fragmented, noisy, and biased**. Readers get
incomplete, contradictory, or slanted headlines; every outlet shows a different
slice of the same event; the sheer volume makes the full picture impossible to
assemble; and telling fact from fiction keeps getting harder.

The question InkBytes answers: *how does a reader get a balanced, nuanced,
objective account of an important event without reading 20 sources themselves?*

## 3. Value proposition

For every newsworthy event, InkBytes produces a single page that's worth twenty —
with citations, entity context, and source diversity preserved. The pipeline:

1. **Collects** from many sources in parallel (Messor).
2. **Enriches** with entities, topic, language, and a short summary (Curator · ENRICH).
3. **Clusters** related articles by semantic similarity + entity overlap (Curator · CLUSTER).
4. **Synthesizes** a single balanced, source-traceable one-pager once a cluster has
   ≥ 2 distinct sources (Curator · SYNTHESIZE).
5. **Assures quality** with a fact-check pass that drops any claim not tied to a source.

> **Architecture note.** The original product framing described four services
> (Messor → Entopics → Synochi → Unitas). For v0 the three middle stages are
> collapsed into one LLM-powered service, **Curator**. The reader-facing promise is
> unchanged; only the implementation is simpler. See
> [`Curator/docs/adr/0001-curator-collapses-pipeline.md`](../Curator/docs/adr/0001-curator-collapses-pipeline.md).

## 4. Target audience

| Segment | Need | Why InkBytes |
|---|---|---|
| Journalists / researchers | Comprehensive coverage of a topic, fast | Saves hours of manual scraping and consolidation |
| Executives / analysts | Accurate briefings without editorial bias | One traceable source instead of ten with opposing slants |
| Professionals staying current | Full context in fast-moving industries | Less time lost in fragmented feeds |
| Academics / students | Balanced material to cite | Multi-source with citation transparency |
| The informed citizen | Break the filter bubble | Multi-source perspective without biased algorithmic curation |

## 5. Core values

**Accuracy · Transparency · Accountability**

- **Accuracy** — every fact traceable to its source; automated QA plus editorial
  review where it applies.
- **Transparency** — the sources behind each page are visible. It isn't magic, it's
  traceable aggregation.
- **Accountability** — errors are corrected in the open; the system learns from its
  failures.

## 6. Differentiation

| Alternative | Limitation vs InkBytes |
|---|---|
| Google News / Apple News | Opaque algorithmic curation; doesn't synthesize; keeps you fragmented |
| Feedly / Inoreader | RSS aggregation only — no synthesis or cross-source analysis |
| Ground News | Strong on bias labelling, but doesn't synthesize a single article |
| LLM + web search (ChatGPT, Claude, Perplexity) | Hallucinations, inconsistent citations, no reproducible pipeline |
| Reading 10 sources manually | Expensive in time; impossible at scale |

**The edge:** a reproducible, traceable pipeline with programmatic QA and a hard
"≥ 2 distinct sources" rule — not a thin wrapper over an LLM.

## 7. Commercial thesis

People are **fatigued by the volume of news** but **don't want less coverage** —
they want **better synthesis**. InkBytes targets the gap between static aggregators
(no added value), generalist LLMs (no reproducibility or traceability), and
traditional journalism (expensive to scale).

**v0 pricing & gating:** free tier sees headlines + first ~100 words; paid at
**$9/month** unlocks the full synthesis, evidence rail, and entity links. v0 ships
behind a single shared password for invited users (full auth/billing deferred). See
[`mvp-plan.md`](./mvp-plan.md) §9.

**v0 vertical:** LATAM bilingual (Dominican Republic, Mexico, Colombia, Argentina)
plus the existing global EN business/tech set — the underserved wedge.

## 8. Lineage — from InkPills to InkBytes

**InkPills (2023)** was the original concept: consolidated "pills" of information
synthesized from many sources. The **Factory Objects** and **Pilled Article
Anatomy** described the atomic unit — a *Pill* is a final consolidated article that
references its source articles, carries extracted entities, and links to related
Pills via similarity/clustering. **InkBytes (2024+)** is the evolution: same
concept, formalized architecture, commercial name. InkPills terminology may still
surface in older technical docs as the name of the *concept*; InkBytes is the
*product*.

## 9. Validation status (SPARK-X)

InkBytes is tracked under Pragmata Labs' **SPARK-X** validation framework
(Strategic Validation → functional prototype → go/no-go to Build MVP). As of
2026-06-02 the v0 functional prototype is **proven end-to-end** — the pipeline runs
on real infrastructure and produces multi-source pages a reader can open. The open
strategic questions (primary audience B2C vs B2B, launch language, monetization
shape, focus vs other Pragmata Labs bets) are tracked on the Notion
[MVP / SPARK-X page](https://www.notion.so/373eca56ed9481c084caee2499e074e5).

## Related

- [`STATUS.md`](./STATUS.md) — live engineering status (authoritative)
- [`mvp-plan.md`](./mvp-plan.md) — one-week v0 plan, pricing, cost model, risks
- [Notion hub](https://www.notion.so/373eca56ed94818da548f66ca288593a) — product/strategy canonical
