# Curator ADR-0032 — Salvage the Entopics/DocTrainer NLP IP into Curator; retire the legacy repos

> *Status: **accepted** — items 1 + 2 implemented 2026-06-15 (committed, not yet deployed; NER pre-pass ships disabled behind two gates) · Owner: Julian De La Rosa · Date: 2026-06-15*
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

**Implemented 2026-06-15** (committed locally, not yet deployed):
- `services/taxonomy.py` — single loader for the two vendored artifacts; exposes
  `CATEGORIES_33`, `normalize_category()` (case-fold the LLM's pick to a canonical
  33 label, reject off-ontology), `suggest_category()` (634→33 bridge over
  section/tags, case-insensitive). Fail-soft: a missing artifact logs once and the
  pipeline runs on the LLM alone.
- `contracts/enriched_v1.py` — `Theme` widened 8→15; new optional
  `article_category: str | None` (free text, so `instructor` never re-prompts on a
  near-miss; constrained to the 33-set in Python).
- `prompts/enrich.md` — rule 7 lists the 15 themes; new rule 8 lists the 33
  categories + `BRIDGE_SUGGESTION` hint; the bridge line is injected by
  `skills/enrich.py`.
- `core/application.py` — `article_category = normalize_category(llm_pick) or
  suggest_category(section, tags)` (LLM first, bridge fallback on abstain).
- `services/database_service.py` — `write_enrichment(... article_category=)` writes
  it via `COALESCE($9, article_category)` — **non-destructive**: an abstain that the
  bridge can't resolve keeps the existing Messor-raw section rather than NULLing it.
  Existing rows upgrade to the normalized 33-cat only as they re-enrich.
- `core/api_server.py` — `_VALID_THEMES` widened to 15; the ADR-0027 `?category=`
  filter now documents `article_category` as the normalized 33-cat (legacy Messor
  section until re-enriched).
- `scripts/test_taxonomy_widen.py` — 17 checks (theme subset, contract validation,
  loader=33, normalize/bridge behaviour, prompt↔33-set drift guard,
  `_VALID_THEMES`↔contract). All green. Verified on real-LLM `--dry-run`: both
  fixtures classify `business` / `Business & Economy`.

**Known wrinkles (follow-ups, not blockers):**
- The 33-cat ontology is a raw 2024 model artifact with overlaps/dotted subtypes
  (`Entertainment` vs `.Tv/.Movies/.Music`, `Economy` vs `Business & Economy`,
  `Miscellaneous`/`Headline News`/`Weird News`). It's an imperfect LLM target;
  the prompt tells the model to prefer the broadest fitting label. A future cleanup
  could prune it to a tighter granular set.
- **Reader + Backoffice UI** still surface only the original 8 theme chips/icons.
  The 7 new themes flow through safely (the Reader's `CategoryIcon` returns `null`
  and the colour maps are open `Record<string,string>`, so no crash — just no
  dedicated chip/icon/colour yet). Widening the Reader chips/icons and the
  Backoffice filter dropdown is the immediate non-breaking follow-up.

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

**Implemented 2026-06-15** (committed locally, not deployed; ships **disabled**):
- `services/ner_prepass.py` — `NerPrepass.extract(article)` lazy-loads the
  per-language model (NER-only pipeline; others disabled for speed/memory),
  runs spaCy in a worker thread (`asyncio.to_thread`) under a per-doc timeout,
  normalizes labels (EN OntoNotes + ES/`xx` CoNLL → PERSON/ORG/LOC; EVENT left to
  the LLM), dedupes + caps the most-frequent surface forms per type. **Fail-open
  everywhere** (gated off, unsupported language, missing model, load error,
  timeout → `[]`). `format_must_cover()` renders the `TYPE: a, b` block.
- `core/config.py` — `NerCfg` (`enabled=False`, `models={en:en_core_web_md,
  es:es_core_news_lg}`, `max_entities_per_type`, `max_chars`, `max_concurrent`,
  `timeout_s`); env overlay `NER_ENABLED` + per-language `NER_EN_MODEL`/
  `NER_ES_MODEL` (drop es to `_md` on a memory-tight box).
- `prompts/enrich.md` (rule 4 + input block) — the LLM must include each genuine
  MUST_COVER entity with the *correct* type/salience, may drop a false positive,
  and still finds the central EVENT itself.
- `skills/enrich.py` — `run(article, must_cover=…)` injects the block.
- `core/application.py` — runs after triage, before enrich, bounded by
  `_ner_sem`; also wired into `--dry-run` (logs MUST_COVER).
- `requirements.txt` — `spacy>=3.7,<3.9` (lib always; models NOT).
- `Dockerfile` — `ARG INSTALL_NER_MODELS=false` gates the ~600MB
  `spacy download en_core_web_md es_core_news_lg`, so the default image stays lean.
- `scripts/test_ner_prepass.py` — 15 checks (gating, fail-open ×3, format,
  prompt injection, real EN+ES extraction, dedup, type-filter, cap). All green.
  Verified end-to-end on `--dry-run`: a Spanish fixture loaded `es_core_news_sm`,
  surfaced 9 typed entities, and the LLM covered all 9 — multilingual gap closed.

**Two gates, both default-off:** build-time (`INSTALL_NER_MODELS`) keeps models
out of the image; runtime (`NER_ENABLED`) keeps the pass dormant. Roll out like
triage did — bake models, enable on one cycle, watch worker memory — because
`es_core_news_lg` is ~1GB resident vs the worker's 1.5GB cap (use `es_core_news_md`
or wait for the 16GB droplet upgrade).

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
1. ✅ Taxonomy (33-cat + 634-bridge) → `Curator/.../data/taxonomy/` **and wired
   into the enrich path** (item 1 build, 2026-06-15).
2. ✅ spaCy NER pre-pass → `Curator/.../services/ner_prepass.py` (item 2 build,
   2026-06-15). Ships disabled (build + runtime gates); enable after a memory
   check on the worker.
3. ☐ `lee.py` Wikipedia linker → preserved (port when item 3 is built).
4. ☐ 346k corpus + 224 MB BERTopic → DO Spaces archive + manifest.
5. Then: tag the repos read-only / move out of active `Trashx`, add a `DORMANT.md`
   pointing at this ADR. No code deleted — git history + Spaces archive retain it.

## Credits

Original Entopics + DocTrainer NLP design, the 346k-doc corpus curation, the
IPTC-aligned 634→33 category ontology, and the entity-resolution/linking pipeline:
**Julian De La Rosa** (2024). This ADR carries that work forward into InkBytes v0.
