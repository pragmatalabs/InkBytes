# Messor — Refactor Findings & Fix Plan (Step 1)

> *Status: v1 · Owner: Julián de la Rosa · Last updated: 2026-06-04*
>
> Audit of what Messor does that is duplicated, misplaced, dead, or improvable —
> plus the **budget/local-processing** consideration to carry into the Curator
> analysis (Step 2). Engineering truth: [`STATUS.md`](./STATUS.md). Boundaries:
> [`Messor/adr/0005`](../Messor/docs/adr/0005-messor-curator-responsibility-split.md),
> [`adr/0006`](./adr/0006-scrape-results-via-messor-postgres.md).

## Summary

| # | Finding | Severity | Fix in one line |
|---|---|---|---|
| M1 | Outlet source-of-truth drift: Messor scrapes from a local `outlets.json` + a dead platform REST API, **not** `public.outlets` | **P0** | Fetch the catalogue over HTTP from `public.outlets` (Curator's `/outlets`); local file becomes seed fallback |
| M2 | Dead platform integration (`OutletsManagerAPI`, `MESSOR_API_BASE_URL`, `send_session_to_api`) points at the retired Strapi/Laravel platform | P1 | Delete the REST outlet path + the SEND_TO_API save-mode |
| M3 | Duplicate scrape-results paths: file-based `/api/scrapesessions` (B4) vs durable `public.scrape_sessions` (B12) | P1 | Collapse Run History onto `public.scrape_sessions`; retire the file-scan endpoint |
| M4 | `scraping_session.json` runtime artifact committed to git; default write path = cwd | P2 | Gitignore + remove; write summaries under `data/` |
| M5 | `StorageService.save_scraping_session` convoluted (nested save-mode branching + stage-then-republish) | P2 | Simplify to stage → upload → publish once SEND_TO_API is gone |
| M6 | Two legacy outlet files (`news_outlets_local.json`, `news_outlets_sources.json`) | P2 | Delete |
| M7 | 394-line interactive REPL (`command_processor`) — interactive verbs likely legacy post-client | P3 | Keep the programmatic queue path; trim/justify interactive MOVE/CLEAN/EXIT |
| — | NLP boundary correctly enforced (no `.nlp()` in Messor) | OK | Keep — see "Budget" below for the nuance |

## Findings (detail)

### M1 — Outlet source-of-truth drift (P0)

`scraper_service.py:287` calls `get_outlets(OutletsDataSource.REST_API)`, which tries
the **retired platform REST API** first (`application.py:100` →
`MESSOR_API_BASE_URL` / `platform_api.base_url()`), then falls back to a local
`data/outlets/outlets.json`. Messor's own `GET /api/outlets` also serves that local
file. The admin, however, CRUDs `public.outlets`. Result: **admin outlet edits do not
reach the harvester**, and the Backoffice Health screen (which reads Messor's
`/api/outlets`) reports a different list than the one it edits. The catalogue lives in
four places (`public.outlets`, `outlets.json`, two legacy files, dead REST path).

**Fix — respects "Messor stays Postgres-free" (ADR-0006):** do not give Messor DB
access. Have Messor resolve its catalogue over HTTP from an endpoint backed by
`public.outlets`. **Curator already exposes this:** `GET :8060/outlets`. Point
Messor's `OutletService` at that endpoint (config-driven URL), keep the bundled
`outlets.json` only as an **offline seed fallback**, and retire Messor's own
file-backed `/api/outlets` (the Backoffice reads `public.outlets` directly under
ADR-0003, or Curator's endpoint). Net: the admin's edits drive harvesting; one
canonical catalogue.

### M2 — Dead platform integration (P1)

A whole layer targets the platform Phase 1.2 retired: the `OutletsManagerAPI` REST
path, `MESSOR_API_BASE_URL`/`platform_api`, and `StorageService.send_session_to_api()`
+ its `SEND_TO_API` save-mode. All removable once M1 lands.

### M3 — Duplicate scrape-results paths (P1)

Two mechanisms surface "what happened in a run": **B4 Run History** parses
`.session.json` files off disk via `/api/scrapesessions` (ephemeral, staging-bounded),
while **B12 Scrape Results** uses durable `public.scrape_sessions` (emit → Curator
persist → Backoffice read). Two code paths + two screens for one concept. The durable
DB path is canonical; the on-disk file-scan (`_read_staging_sessions`) is now largely
redundant — collapse Run History onto `public.scrape_sessions`.

### M4–M6 — Cleanup (P2)

`scraping_session.json` is tracked in git at the scraper root with a cwd default write
path (gitignore + remove; write under `data/`). `save_scraping_session` simplifies to
`stage → upload → publish` once SEND_TO_API is gone. The two legacy outlet JSON files
are dead.

### M7 — Interactive REPL (P3, question)

`command_processor.py` (394 lines) implements an interactive REPL (`SCRAPE`/`MOVE`/
`CLEAN`/`EXIT`). The programmatic `auto_command_queue` path is still used by
`application.py`, but the human-interactive verbs may be legacy now that the React
client is retired and harvests are Backoffice-triggered. Decide: keep programmatic,
trim interactive.

## Budget / local-first enrichment (carry into Curator analysis — Step 2)

**Correction to the Step-1 framing.** Removing `.nlp()` from Messor was right for the
*boundary* (ADR-0005: enrichment is Curator's job), but the old local NLP had a real
**budget** virtue — it did cheap local work so we didn't ship everything to a paid
model. That virtue must be **recovered inside Curator**, not by reverting NLP into
Messor.

**Principle:** *Curator owns enrichment, but does the maximum locally/cheaply before
spending a Haiku token.* The per-article LLM ENRICH call is the main cost sink, and
today it runs on **every** harvested article even though only multi-source clusters
ever become pages (309 articles enriched → 29 pages published — most enrichment spend
never reaches a reader).

**Budget levers to evaluate in the Curator analysis (do NOT implement here):**

1. **Reorder embed → cluster → enrich/synth.** Embeddings are ~$0.02/M (negligible).
   Embed first, cluster, and run the expensive Haiku ENRICH/SYNTHESIZE **only on
   articles that land in a ≥2-source cluster**. This is the single biggest lever —
   it stops paying to enrich singletons that never publish.
2. **Local language detection** (e.g. `fasttext`/`langdetect`) instead of asking the
   model. (Messor already language-filters at harvest — keep that.)
3. **Local NER + keyword extraction** (spaCy / a small local model) for entities and
   keywords, leaving the LLM only the things it is uniquely good at (topic, summary,
   factuality, disambiguation) — or skipping per-article LLM enrich for low-value
   articles entirely.
4. **Local near-duplicate collapse** (MinHash / cheap embedding sim) so wire-copy
   duplicates are enriched once per group, not N times.
5. **Local embeddings option** (`sentence-transformers`, e.g. `bge-small`) to zero out
   embedding spend, traded against quality/infra.
6. **Model tiering** — cheap/local model for ENRICH, reserve Haiku for SYNTHESIZE (the
   reader-facing piece). Already anticipated in `mvp-plan.md` §6.

**Architectural placement:** these live in Curator as a **cheap local pre-pass before
the LLM** (a "Skill 0"), keeping ADR-0005 intact. The Curator analysis should size the
spend of each lever against the live `model_usage` data and recommend which to adopt.

## Fix plan (Step 2-ready — Code-agent tabs)

> Order: **M1 → M2** together (M2 falls out of M1), then **M3**, then **M4–M6** as a
> cleanup pass, then decide **M7**. The budget work is a **separate Curator track**,
> not part of these Messor fixes.

### Tab M1+M2 — Outlets from `public.outlets` via HTTP; delete the dead platform path
> `cd Messor/apps/scraper`. Make `OutletService` fetch the outlet catalogue over HTTP
> from a config-driven URL backed by `public.outlets` (use Curator's existing
> `GET :8060/outlets`; add `CURATOR_OUTLETS_URL` to config/env). Keep the bundled
> `data/outlets/outlets.json` **only** as an offline seed fallback. Delete the
> `OutletsManagerAPI`/`MESSOR_API_BASE_URL`/`platform_api` REST path and
> `StorageService.send_session_to_api()` + the `SEND_TO_API` save-mode. Retire Messor's
> own file-backed `GET /api/outlets`. Verify a harvest picks up an outlet toggled in
> the Backoffice (admin edit `public.outlets` → Messor scrapes the new set). Respect
> ADR-0006 (Messor stays Postgres-free — HTTP only, no psycopg). Update `STATUS.md`.

### Tab M3 — Collapse Run History onto durable `public.scrape_sessions`
> `cd Messor/apps/platform` (+ check Messor's scrape router). Point the Backoffice **Run
> History** screen at `public.scrape_sessions` (read-only, ADR-0003) instead of Messor's
> file-scanning `GET /api/scrapesessions`. Confirm B6 Health and B11 alerts have a DB
> source for the same signal, then retire `/api/scrapesessions` + `_read_staging_sessions`
> in Messor. Keep one screen for run results. Update `STATUS.md`.

### Tab M4–M6 — Cleanup pass
> `cd Messor/apps/scraper`. Gitignore + `git rm` the tracked `scraping_session.json`;
> change `StorageService` to write session summaries under `data/` (not cwd). Simplify
> `save_scraping_session` to `stage → upload(S3) → publish` now that SEND_TO_API is gone.
> Delete the two legacy outlet files (`news_outlets_local.json`,
> `news_outlets_sources.json`). Update `STATUS.md`.

### Tab M7 — Decide the REPL (question first, then act)
> `cd Messor/apps/scraper`. Audit `command_processor.py`: keep the programmatic
> `auto_command_queue` path (used by `application.py`); determine whether the
> interactive `SCRAPE/MOVE/CLEAN/EXIT` verbs are still used by anything after the React
> client retirement. If not, trim them to shrink surface area. Record the decision
> (ADR if non-trivial). Update `STATUS.md`.

## What NOT to do

- Do **not** revert NLP/enrichment into Messor. ADR-0005 holds: Messor harvests + does
  raw extraction (incl. the language filter it already has); Curator owns enrichment.
- Do **not** give Messor direct Postgres access (ADR-0006). Outlets come over HTTP.
- Do **not** implement the budget levers in this Messor track — they belong to the
  Curator analysis (Step 2).
