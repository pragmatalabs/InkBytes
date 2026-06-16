# Curator ADR-0032 — Salvage the Entopics/DocTrainer NLP IP into Curator; retire the legacy repos

> *Status: **proposed** · Owner: Julian De La Rosa · Date: 2026-06-15*
> *Original NLP work (Entopics service + DocTrainer training project) designed, trained and authored by **Julian De La Rosa** (2024). This ADR salvages that work into the InkBytes monorepo so the two source repositories can be put **dormant**.*

## Context

Before the LLM era of InkBytes, entity/topic/category extraction was done with
**classic ML, no LLM**, across two of Julian's repositories:

- **Entopics** (`Trashx/Entopics`) — the *runtime* service: spaCy `en_core_web_md`
  NER (10 entity types) + a Multinomial-NB/TF-IDF topic classifier (33 categories)
  + Wikipedia entity-linking (circuit-breaker + cache) + TextBlob sentiment,
  consuming Messor scrapes off RabbitMQ.
- **DocTrainer** (`Trashx/DocTrainer`) — the *training* project: 11 trainer
  notebooks (LDA, Top2Vec, BERTopic-100, LogReg/MNB/RandomForest classifiers) over
  a curated **346,707-document** news corpus, producing the .joblib/.pkl models
  Entopics loaded.

Today Curator does all of this with an LLM (DeepSeek `v4-flash`, multilingual,
~$3–4/day). A prior analysis (this session) concluded: **do not revive the full
ML pipeline** — it is English-only (fatal for the LATAM/ES core vertical), caps at
~57.8% category accuracy, and the LLM is cheaper *and* better. But several pieces
are genuine, hard-won IP worth pulling forward **before the repos go dormant**.

This ADR plans the salvage of the 4 High→Medium-value assets and how each plugs
into InkBytes.

## What's special (the IP an LLM does *not* give you for free)

1. **An IPTC-grounded news ontology.** The `category_mappings` artifact unifies
   **634 raw source labels into 33 normalized categories** — and **~574 of those
   labels are IPTC Media Topics**, the international standard used by Reuters/AP and
   the wire services (`crime, law and justice`, `conflict, war and peace`,
   `economy, business and finance`, …), bridged with HuffPost + 20-Newsgroups
   consumer labels. This is an *opinionated, standards-aligned editorial taxonomy*.
   An LLM will happily invent ad-hoc categories; it will **not** reproduce a stable,
   IPTC-aligned ontology that maps cleanly onto how professional newsrooms classify.
2. **Entity-resolution craft.** Deterministic dedup/merge of mentions
   ("Trump"/"Donald Trump" → one entity + occurrence count) and **Wikipedia
   entity-linking** with a circuit-breaker + two-tier cache — *canonicalization*
   the LLM does not do.
3. **A 346k-doc labeled news corpus** (own Messor scrapes + IPTC/HuffPost labels) —
   a ready fine-tuning / evaluation asset.
4. **A deterministic, multilingual-capable typed-NER pattern** (spaCy, 10
   IPTC-ish entity types) — free, reproducible, and (with spaCy's own `es_*`/`xx_*`
   models) able to do what the legacy stack never did: **Spanish**.

## Decision

Salvage the 4 High→Medium assets into the InkBytes monorepo. Items 1–2 integrate
into Curator's enrich path now; items 3–4 are preserved-and-documented (built when
needed). Then archive Entopics + DocTrainer (see *Repo-dormancy plan*).

### Item 1 (🥇 High) — the taxonomy → widen categories  *[no model, no retraining]*

Vendored into the repo at `Curator/apps/curator/data/taxonomy/`:
- `categories_33.json` — Julian's 33-category ontology, verbatim.
- `source_category_bridge.json` — the full 634→33 IPTC+HuffPost+20NG mapping.

Because InkBytes enriches with an **LLM**, widening the taxonomy is a *prompt +
reference-data* change, not a classifier retrain. Two-level scheme (the DB columns
already exist: `theme`, `article_category`, `meta_categories`):

- **`theme`** widened from **8 → 15** (broad, mutually-distinct, UI-facing):
  `politics · world · business · technology · science · health · sports · culture ·
  entertainment · environment · crime · education · lifestyle · religion · disaster`
  (current 8 splits: tech→technology+science, culture→culture+entertainment; adds
  crime, education, lifestyle, religion, disaster).
- **`article_category`** = the granular **33** (Julian's ontology) for drill-down /
  Backoffice filters / future per-category pages.
- The 634-bridge maps Messor `OUTLET_SECTION`/`meta_categories` → a normalized
  category, used as a strong hint in the enrich prompt (and a deterministic fallback
  when the LLM is unsure).

### Item 2 (🥈 Medium-high) — spaCy NER pre-pass → enforce typed entity coverage

A new **optional** pre-enrich step in Curator (`services/ner_prepass.py`, behind a
flag, same shape as the triage gate): run spaCy NER (`en_core_web_md` +
`es_core_news_lg`, language-routed) to extract typed entities deterministically,
then pass them into the enrich prompt as `MUST_COVER` entities so the LLM can't
under-extract PERSON/ORG/LOC/**EVENT** (the exact gap fixed half-way in ADR-0027's
entity work). Runs on the Hostinger box / locally — **~free, no API**. Crucially it
is **multilingual**, closing the legacy stack's fatal EN-only limitation. Fail-open
(spaCy hiccup → LLM-only, never blocks). Net effect: deterministic typed-coverage
floor + the LLM's judgment on top.

### Item 3 (🥉 Medium) — Wikipedia entity-linking  *[design captured, deferred]*

Port `Trashx/Entopics/nlp/lee.py` (circuit-breaker + LRU + disk cache) as an
optional entity-canonicalization pass: enriched entities → Wikipedia/Wikidata IDs,
enabling cross-event entity dedup and a future entity knowledge-graph. Not built
now; the module + design are preserved in this ADR so the source repo can retire.

### Item 4 (Medium) — the 346k labeled corpus  *[archive, don't vendor]*

Too large for the monorepo (~108–227 MB). **Archive to DO Spaces**
(`backups/datasets/doctrainer-news-346k/`) with a provenance manifest; reference it
here. Preserved for future local-model fine-tuning / extraction evaluation.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Revive the full classic-ML extraction pipeline | English-only (kills the LATAM/ES core), ~57.8% category ceiling, stale (2024) models; LLM is cheaper, better, multilingual. |
| Keep the legacy repos "just in case" | They rot; the IP is undiscoverable in `Trashx/`. Salvage the 4 assets, then archive. |
| Re-derive a taxonomy by asking the LLM | Loses IPTC-standard alignment + stability; LLM invents inconsistent categories run-to-run. |
| Vendor the 346k corpus + 224 MB BERTopic into the monorepo | Bloats the repo; the classifiers/BERTopic are EN-only + superseded by pgvector clustering. Archive instead. |

## Consequences

- **Categories widen 8→15 + a 33-deep layer** with zero model training — purely
  prompt/reference data. Richer Reader navigation + Backoffice filters.
- **Entity coverage gains a deterministic, multilingual floor** (item 2).
- **Entopics + DocTrainer can go dormant** — their durable value lives in-repo.
- Cost stays ~flat (spaCy pre-pass is free/CPU; may *reduce* LLM tokens slightly).
- Trade-off: two more spaCy models to ship (~600 MB combined) on the box running
  the pre-pass; gated/optional so it never blocks the pipeline.

## Repo-dormancy plan (the goal)

A repo is "dormant" once its durable value is in-repo or archived:
1. ✅ Taxonomy (33-cat + 634-bridge) → `Curator/.../data/taxonomy/` (this ADR).
2. ☐ spaCy NER pre-pass → `Curator/.../services/ner_prepass.py` (item 2 build).
3. ☐ `lee.py` Wikipedia linker → preserved (port when item 3 is built).
4. ☐ 346k corpus + 224 MB BERTopic → DO Spaces archive + manifest.
5. Then: tag the repos read-only / move out of active `Trashx`, add a `DORMANT.md`
   pointing at this ADR. No code deleted — git history + Spaces archive retain it.

## Credits

Original Entopics + DocTrainer NLP design, the 346k-doc corpus curation, the
IPTC-aligned 634→33 category ontology, and the entity-resolution/linking pipeline:
**Julian De La Rosa** (2024). This ADR carries that work forward into InkBytes v0.
