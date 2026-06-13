# Curator ADR-0029 — On-demand breaking-news gate (search → scrape → manual publish)

> *Status: accepted · Owner: Julian · Date: 2026-06-13 · spans Messor + Curator + Backoffice*

## Context

The automatic breaking detector (ADR-0024) flags an event when ≥2 pulse outlets
converge on it. But an editor often knows a story is breaking *before* the
fleet converges — or wants coverage of a specific story on demand (e.g. an
announcement at `anthropic.com/news/...`). There was no way to pull a named
story into the pipeline and publish it under editorial judgement.

## Decision

A Backoffice "Breaking Desk": the editor enters a **title** or pastes a
**URL**; the system searches + scrapes coverage on demand, runs it through the
normal enrich→cluster→synthesize pipeline at high priority, and exposes manual
gate actions on the resulting event.

### Part 1 — Messor: discovery + on-demand scrape (`feat/messor … part 1/3`)

- **`core/gnews_search.py`** — free-text discovery via Google News RSS search
  (`news.google.com/rss/search?q=`). Its result links are opaque
  `/articles/CBMi…|AU_yqL…` blobs that don't redirect; the real source URL is
  recovered by replaying Google's `batchexecute` RPC with a signature+timestamp
  scraped from the article shell page. Every failure degrades gracefully (entry
  skipped). Fragile (undocumented Google endpoint) but a pasted URL bypasses it
  entirely, so search-recall can drop without breaking the gate.
- **Explicit-URL scrape path** — `scrape_outlet(..., explicit_urls=[...])`
  scrapes exactly those URLs, skipping discovery, and **bypasses the ADR-0015
  freshness gate** (`process_outlet_articles(skip_freshness=True)`): the editor
  hand-picked them and they may be days old.
- **`ScraperService.execute_on_demand_scrape(query|url, lang, limit)`** scrapes
  under a namespaced `ondemand-<slug>` brand at AMQP **priority 9** (jumps the
  enrich queue). **`POST /api/scrape/on-demand`** returns the brand immediately;
  the scrape runs in a background thread.

### Part 2 — Curator: manual gate commands (this part)

Three new commands on the existing `curator.commands` bus (`_handle_command`):

- **`event.mark_breaking`** → `db.set_event_breaking` sets `breaking_at=NOW()`,
  `breaking_until=NOW()+ttl` (default `breaking_ttl_hours`). Editor override of
  the auto-detector — fires regardless of pulse velocity.
- **`event.clear_breaking`** → NULLs both columns.
- **`event.force_publish`** → `synthesize.run(event_id, force=True)`. The new
  `force` flag bypasses the ≥2-article minimum and the promo/noise publish
  gates (ADR-0020/0021) — the editor has vetted the story. Still requires ≥1
  article. `synthesize.run` already sets `published_at` + event status, so this
  publishes immediately.

`force` defaults to `False`, so `event.resynthesize` and the normal pipeline are
unchanged.

### Part 3 — Backoffice: the Breaking Desk screen (next part)

Search box (title|URL) → calls `/api/scrape/on-demand` → polls the Curator API
for events whose articles carry the `ondemand-<slug>` outlet brand → renders
them with **Mark Breaking / Force Publish** buttons (priority enrich is
automatic via the priority-9 scrape).

## Consequences

- **Good**: editors can surface a named breaking story in seconds, independent
  of the auto-detector and the harvest cycle.
- **Risk — Google News decode fragility**: monitored by the graceful-skip
  counters in `gnews_search`; URL mode is the always-works fallback.
- **Quality**: `force_publish` deliberately bypasses the safety gates, so it's
  an editor-only action (behind the Backoffice, not automatic). On-demand
  articles carry a single synthetic `ondemand-` brand, so source_count is not
  meaningful for them — which is why the gate is manual, not auto-detected.
- On-demand articles are exempt from the 48h freshness + intake gates by
  design; they are intentionally editor-curated, not part of the live feed's
  automatic freshness ranking.
