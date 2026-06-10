# Messor ADR-0016 — Per-outlet scraper config fields

> *Status: accepted · Owner: Julian · Date: 2026-06-10*

## Context

The Messor scraper has always used global config values for article filtering
thresholds (e.g. `config.scraper.min_word_count()` — default 40 words). This
works for typical long-form news articles but fails for outlets that routinely
publish shorter formats:

- **BBC** — news briefs, live-update stubs (~25-40 words)
- **Reuters** — wire-service one-paragraph items (~25-35 words)
- **LATAM dailies** — short breaking-news flashes

When these outlets run through the global 40-word filter, their legitimate
short articles are silently dropped, producing 0 staged articles per cycle.

The same session also introduced `feed_url` (Messor ADR-0013 follow-up):
per-outlet RSS/Atom feeds that replace newspaper3k homepage crawling for
URL discovery.

Both are per-outlet overrides that flow through the same stack:
`public.outlets` DB column → Curator API → Messor OutletsSource → scraper.

## Decision

Establish a pattern for per-outlet scraper config fields:

1. **Add the column to `public.outlets`** via a numbered Curator migration
   (`013_outlet_min_word_count.sql`), with `IF NOT EXISTS` guard.
2. **Add a Pydantic field** to `OutletsSource` with `None` default (`None` =
   "use global fallback").
3. **Add to `SCRAPER_FIELDS`** in both paths in `outlet_service.py` (Curator
   API path + local JSON fallback path).
4. **Wire into the processing function** via `getattr(outlet, 'field', None)`
   at the call site in `scrape_news_outlet()`, passing down through
   `process_outlet_articles()` → `scrape_outlet_article()` →
   `build_newspaper_article()` as a keyword argument with a `None` default
   and a `if value is not None else config.global_default()` guard.
5. **Seed `outlets.json`** with per-outlet overrides for known edge cases.
6. **Add to Backoffice CRUD**: Curator migration → Laravel migration (with
   raw `information_schema` guard — see anti-pattern below) → `Outlet.php`
   fillable + cast → `OutletController` validation + `present()` → `Index.jsx`
   form field.

## Fields added (2026-06-10)

| Column | Type | Default | Purpose |
|---|---|---|---|
| `feed_url` | `TEXT` | `NULL` | RSS/Atom URL for feed-first URL discovery (ADR-0013) |
| `min_word_count` | `INT` | `NULL` | Per-outlet word count floor; `NULL` → global config (40) |

Outlets seeded with `min_word_count` overrides:
BBC, Al Jazeera, Reuters, animalpolitico → 25; eldinerodr, listindiario,
diariolibree, acentodr, elcaribedr → 25.

## Consequences

- **Good**: new per-outlet config fields follow a clear, tested pattern.
  Adding the next field (e.g. `rate_limit_ms`, `custom_headers`) takes one
  migration + five touched files.
- **Good**: `None` defaults are fully backward-compatible — no outlet
  config changes are required for outlets that are happy with the global
  defaults.
- **Watch**: `SCRAPER_FIELDS` in `outlet_service.py` must be updated for
  every new field. It is intentionally an explicit allowlist (strips unknown
  columns before feeding Pydantic) — forgetting it silently drops the value.

## Anti-pattern: `Schema::hasColumn()` is unreliable for cross-schema tables

The Backoffice DB connection's `search_path` is `backoffice,public`. Laravel's
`Schema::hasColumn('outlets', ...)` uses Doctrine DBAL which introspects the
first schema in the path (`backoffice`) — `public.outlets` is invisible to it,
so the guard always returns `false` and the `ALTER TABLE` fires even when the
column already exists (Curator migration ran first).

**Fix**: use a raw `information_schema` query that explicitly targets
`table_schema = 'public'`:

```php
$exists = DB::selectOne(
    "SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = 'outlets' AND column_name = ?",
    ['column_name']
);
if ($exists) { return; }
```

This pattern is now encoded in both `2026_06_10_000001` and `2026_06_10_000002`
migrations and in `CLAUDE.md` anti-patterns.
