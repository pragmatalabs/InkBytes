# InkBytes — Lessons Learned

> *Status: living doc · Owner: Julián · Last updated: 2026-06-07*

Hard-won, non-obvious gotchas. Add to this whenever something surprises you or
costs real debugging time. Newest first.

---

## 2026-06-07 — Next.js 16: `viewport` is a separate export from `metadata`

`themeColor`, `viewportFit`, `colorScheme` etc. were moved out of `Metadata`
into a `Viewport` export in Next.js 15+. If you put them in `metadata` they
are silently ignored. The correct pattern:

```typescript
import type { Metadata, Viewport } from "next";
export const viewport: Viewport = { themeColor: "#1a1a2e", viewportFit: "cover" };
export const metadata: Metadata = { /* no themeColor here */ };
```

Lesson: always check for `Viewport` type import when setting anything
viewport-related in layout.tsx. The TypeScript type for `Metadata` no longer
accepts `themeColor`, so it's caught at build time — don't silence those errors.

---

## 2026-06-07 — `env(safe-area-inset-bottom)` silently returns 0 without `viewport-fit=cover`

The CSS `env(safe-area-inset-bottom)` inset for the iPhone home indicator is
only non-zero when the viewport is configured with `viewport-fit=cover`. Without
it the value is always 0 and the bottom nav sits on top of the home indicator.

Must pair two things:
1. `viewport: { viewportFit: "cover" }` in Next.js layout
2. `style={{ paddingBottom: "env(safe-area-inset-bottom)" }}` on the nav element

---

## 2026-06-07 — Pydantic v2 `model_dump()` returns `datetime` objects, not strings

asyncpg encodes query parameters against the Postgres column type *before* any
SQL cast runs. A bare ISO string like `"2026-06-07T12:00:00"` raises
`asyncpg.exceptions.DataError: invalid input for query argument $N: ... (expected datetime, got str)`
for `TIMESTAMPTZ` columns.

When calling `upsert_article_raw(article.model_dump(), ...)` from a pydantic v2
model, `model_dump()` returns `datetime.datetime` objects for `datetime` fields
— which asyncpg handles correctly. The problem only arises if you manually
construct the dict from raw strings (e.g. in tests). Always use
`ArticleV1(...).model_dump()`, never hand-build the dict.

---

## 2026-06-07 — newspaper3k: prefer `og:image` over `top_image` for quality

`article.top_image` uses newspaper3k's heuristic (largest `<img>` near the
article body). `article.meta_data.get("og", {}).get("image")` is the explicit
`og:image` tag set by the publisher — almost always better quality (correct
aspect ratio, CDN-hosted, editor-chosen). Always prefer `og:image` when present:

```python
lead_image = article.top_image or None
og = (article.meta_data or {}).get("og", {}).get("image")
if og and isinstance(og, str) and og.startswith("http"):
    lead_image = og  # override with the explicit publisher image
```

---

## 2026-06-07 — Ollama embedding saturation → Curator dead-loop

**Symptom:** Curator worker processed the same 4 articles every 30 minutes
forever; `run-total` cost kept growing but no new pages were produced.

**Root cause cascade:**
1. 7,545 articles queued in RabbitMQ → Curator started consuming
2. ENRICH (LLM) succeeded in ~30 sec, then EMBED called Ollama
3. Ollama was hammered by all queued embedding requests → CPU at 5597% on a 4-core host
4. Each `/v1/embeddings` call timed out after ~5 min → `openai.APITimeoutError`
5. `APITimeoutError` fell into `except Exception` → `nack(requeue=False)` → **message silently dropped**
6. BUT the RabbitMQ 30-min consumer ACK timeout fired BEFORE the nack → broker requeued the messages anyway
7. Result: same 4 articles looped back every 30 min; no progress

**Fixes applied:**
- `message_service.py`: add `_TRANSIENT_ERRORS = (APITimeoutError, APIConnectionError)` caught before the generic except — nacks with `requeue=True` so articles are genuinely retried, not dropped
- `infra/rabbitmq/rabbitmq.conf`: `consumer_timeout = 3600000` (1h) so the channel isn't force-closed while Ollama recovers
- Restart Ollama when it's CPU-saturated (the request backlog can't be cancelled via API; restart is the only escape)
- After Docker daemon restart, always reconnect Ollama to inkbytes-internal: `docker network connect inkbytes_inkbytes-internal ollama`

**Lesson:** `except Exception → nack(requeue=False)` is a dangerous default. Any transient infrastructure error (network timeout, embedding service overload) looks like a "permanent" failure and silently discards work. Always catch infrastructure errors separately and requeue.

---

## 2026-06-07 — newspaper3k: `download_categories()` has no timeout

`NewsPaper.generate_paper()` calls `paper.download_categories()` which spawns
newspaper3k's own internal thread pool to fetch category/section pages. If a site is
slow or blocked, this call hangs indefinitely — **no timeout is configurable**. Setting
`request_timeout=30` only applies to individual article downloads, not the homepage
category crawl.

**Effect observed:** Messor cycle started at 20:04, was still running at 00:19 (4+ hours),
consuming 2338% CPU and 4 GB RAM. RabbitMQ acked out from the message backlog, making
the broker "unhealthy".

**Fix:** Wrap each outlet's `create_outlet_scraping_session()` call in
`future.result(timeout=300)` — abandon the WAIT after 5 min while the thread continues
to wind down naturally. Also catch `Exception` (not just `ValueError`) in
`generate_paper()` so homepage-crawl failures are logged and counted.

**Lesson:** newspaper3k's internal threading is not observable or cancellable from
outside. Any timeout must be imposed at the Future layer, not inside the library.

---

## 2026-06-07 — `docker mem_limit` vs `deploy.resources.limits`

**Wrong (Swarm-only):**
```yaml
services:
  messor:
    deploy:
      resources:
        limits:
          memory: 3g
```
This syntax is silently ignored in standalone `docker compose` (only works in Docker Swarm
mode). Messor appeared to have a 3 GB limit but was actually uncapped.

**Correct (standalone compose):**
```yaml
services:
  messor:
    mem_limit: 3g
    cpus: 2.0
```

Verified via `docker inspect` — `HostConfig.Memory` must be non-zero.

---

## 2026-06-07 — Scrape success rate: `failed` includes `duplicates`

Messor's `ScrapingSession` increments `failed_articles` for BOTH:
1. Articles that fail to parse/download (true failures)
2. Articles already seen in the current batch or previous scrapes (duplicates)

So `success_rate = successful / total` shows e.g. 11% when the real parse success on
genuinely new articles was 47%.

**Real formula:** `successful / (total - duplicates)` = parse success on new articles.

**Fix:** `ScrapeResultsController.presentRow()` now computes `trueNew = total - duplicates`
and `realRate = successful / trueNew`. Column renamed "Success" → "Parse %" with tooltip.

**Lesson:** Always understand what "failed" means in each system — it may not mean
"error". In Messor, deduplication counts as failure in the stats.

---

## 2026-06-07 — Docker zombie PID 1 requires daemon restart to clear

When Messor's `download_categories()` froze all threads for 4+ hours, killing the
container via `docker compose down` produced:

```
Error: container PID 1696 is zombie and can not be killed.
Use the --init option when creating containers to run an init inside the container.
```

A zombie process with PID 1 cannot be reaped by any parent since it IS the container
root. The only clean resolution is `systemctl restart docker` (daemon restart).

**Prevention:** Add `init: true` to containers in docker-compose to run a minimal init
(tini) that properly reaps child processes.

---

## 2026-06-07 — `docker update -m` works live (no restart needed)

To change a running container's memory limit:
```bash
docker update -m 6g --memory-swap 6g inkbytes-messor
```

This takes effect immediately without restarting the container. Verified via
`docker inspect inkbytes-messor --format '{{.HostConfig.Memory}}'`.

Note: `--memory-swap` must be set to at least `--memory`; setting only `-m` without
`--memory-swap` keeps the old swap limit which may be inconsistent.

---

## 2026-06-07 — Ollama not on Docker network after Docker daemon restart

Ollama runs in a separate compose project (`galvanic`) and is connected to
`inkbytes_inkbytes-internal` via `docker network connect`. This connection is
**not persistent** — after `systemctl restart docker`, Ollama starts on its own
`galvanic_ollama-net` only.

**Fix (manual):** `docker network connect inkbytes_inkbytes-internal ollama`

**Permanent fix (pending):** Add a systemd unit override or an `ExecStartPost` hook.
Until then, verify Curator can reach Ollama after any Docker daemon restart:
`docker exec inkbytes-curator-api curl -s http://ollama:11434/api/tags | python3 -c "import sys,json; print(json.load(sys.stdin))"`

---

## 2026-06-07 — newspaper3k article order = editorial prominence

`paper.articles` returned by `newspaper.build(outlet.url)` is ordered by how links appear
on the homepage — top stories first, archive/category-nav last. Slicing `[:200]` gives
the top-200 most-prominently-placed articles, which is a reasonable editorial-priority
proxy without RSS.

This is NOT publication-date order. Two articles published at the same time appear in
the order their links appear in the HTML. Deep-archive content at the bottom of category
pages is naturally excluded.

**Future:** RSS/Atom feeds provide explicit `<pubDate>` → sorting by recency becomes
trivial and the homepage-order heuristic is no longer needed.

---

## 2026-06-07 — DeepSeek thinking mode rejects `tool_choice`

DeepSeek R1 (deepseek-reasoner) uses "thinking mode" which does not support
`tool_choice` in the API. `instructor` defaults to `tool_choice="auto"` which fails with:

```
Thinking mode does not support this tool_choice
```

**Fix:** Use `instructor.Mode.JSON` instead of the default mode when wrapping DeepSeek:
```python
instructor.from_openai(
    AsyncOpenAI(api_key=..., base_url="https://api.deepseek.com/v1"),
    mode=instructor.Mode.JSON   # ← required for DeepSeek reasoner
)
```

---

## 2026-06-07 — Synthesis cost loop ($6.32 in one session)

Curator's `_synthesize_once()` was being called on every article enrichment for events
that already had a page. Root cause: `_last_synth_source_count` (in-memory gate) reset
on restart, so on the next enrichment of any article in an existing event, synthesis
re-ran even though `source_count` hadn't grown.

**Fix:** `_last_synth_source_count` gate checks `source_count > last`. On restart it's
empty, so the FIRST article enrichment for each existing event triggers synthesis — but
only once (subsequent articles find `source_count == last` and skip).

**Residual issue:** A restart still causes one synthesis per existing event. With 400+
events this is $2–4 per restart. Long-term fix: persist `_last_synth_source_count` to
DB so it survives restarts.

## 2026-06-04 — Local embeddings (Ollama bge-m3): the threshold is NOT vendor-portable

Moving Curator's CLUSTER embeddings from OpenAI (1536d) to a local Ollama
`bge-m3` (1024d). Surprises worth recording (see Curator ADR-0003):

- **Each embedder has its own cosine *scale* — a threshold tuned for one will
  silently wreck clustering on another.** A spike measured same-event vs
  diff-event similarity: OpenAI mean-inter 0.27, bge-m3 0.41, nomic 0.59. At the
  fixed 0.62 gate, `nomic-embed-text` matched ~everything (false-positive 0.31)
  and would have collapsed every event into one. Always re-measure the gate on
  the new embedder before swapping — don't assume the number carries over.
- **…but it happened to carry over for bge-m3.** At the *production* operating
  point (0.62, precision-heavy), bge-m3 gave rec 0.304 / fp 0.017 vs OpenAI
  0.305 / 0.010 — near-identical. Lucky, and only known because it was measured.
- **Ollama is OpenAI-wire-compatible**, so the existing `AsyncOpenAI` client
  just takes a `base_url` (`http://ollama:11434/v1`) + a dummy api_key
  ("ollama") — the `embeddings.create(model=…, input=…)` call site is unchanged.
  No `torch`/`sentence-transformers` in Curator's venv; the heavy ML lives in
  the Ollama container.
- **Validate the embedder swap on real labels, but mind circularity.** The
  "same-event" labels came from the *current* OpenAI-based clustering, which
  biases the comparison toward OpenAI. bge-m3 nearly tying *despite* that bias
  is a stronger signal than the raw numbers suggest.
- **pgvector width change is destructive.** `vector(1536) → vector(1024)` can't
  cast existing rows; you must drop the ANN index, `ALTER … USING NULL::vector(1024)`,
  recreate the index, and re-embed. Source `body_text` is intact, so it's
  data-safe — but plan the re-embed.
- **EN-only corpus can't prove a multilingual claim.** Our spike was 99.5 %
  English (LATAM/ES outlets unharvested), so bge-m3's multilingual edge is
  design-asserted, not measured. Flag that in the ADR rather than overclaim.

## 2026-06-03 — Backoffice "doesn't work" was three small things, not a broken app

Reported as "visually + functionally doesn't work / no logic." Running it (login →
click every page) showed the app is actually sound; the perception came from:

- **`db:seed` was never run → `backoffice.users` empty → login wall.** A fresh app
  with no account *looks* completely broken. Seeders that create the admin must
  actually be run after `migrate`; the dev seeder now creates `admin@inkbytes.test`.
- **MUI v7 `<Grid item xs={} md={}>` is a silent no-op.** v7's `Grid` is the v2 API
  (`<Grid size={{ xs, md }}>`); the legacy `item`/`xs`/`md` props are ignored, so
  columns don't size and inputs collapse to content width — the Curator Settings
  model dropdowns truncated to "Enrich mo…" / "cl…". Fix: use `size={{...}}`. Grep
  the whole app for `<Grid item` after a v6→v7 bump.
- **A "Control Center" that only shows outlet counts reads as "no logic."** Wiring
  the dashboard to the real pipeline (articles/enriched/events/pages/spend/last-harvest
  via cross-schema reads of Curator `public.*` + `backoffice.model_usage`) is what
  makes an admin feel alive.
- **Responsive ≠ broken.** Below the sidebar breakpoint the nav collapses to a
  hamburger; verifying at a narrow viewport made it look like the nav was missing.
  Check desktop width before "fixing" a non-bug.

## 2026-06-03 — Phase 2.3: events/pages moderation + re-run commands

### Laravel has no AMQP client — publish commands via the RabbitMQ management HTTP API
The Backoffice needs to emit RabbitMQ commands but ships only Guzzle (no
`php-amqplib`, and the handoff forbids adding one without justification). The
management API's `POST /api/exchanges/{vhost}/{exchange}/publish` (HTTP basic
auth `messor:messor`, port **15672** not 5672) does fire-and-forget publishing
with zero new dependencies. `%2F` is the default vhost; rawurlencode it.
`CuratorCommandService` wraps this. Two non-obvious bits: (1) the API returns
`{"routed": true|false}` — `false` means the exchange exists but no queue is
bound (Curator's consumer isn't running), so we raise on it rather than report
success; (2) we **PUT the exchange declare first** (idempotent) so an admin can
issue a command even before Curator has ever booted, otherwise publish 404s.

### `public.pages.published_at` was `NOT NULL` — unpublish needs it nullable
The 001 schema declared `published_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, so
"unpublish" had no clean representation (a sentinel date is worse). Curator owns
the pages DDL, so the fix is a **Curator** migration (`003_pages_moderation.sql`,
`ALTER COLUMN published_at DROP NOT NULL`), not a Backoffice one. The moderation
state of record stays `events.status` (`draft|published|dropped`, already in
001); `pages.published_at` is just the publish toggle. `page.drop` is a soft
drop (unpublish + event `dropped`, row retained) — no hard delete, so a dropped
page is revivable. (→ ADR-0003: Curator owns these writes; Backoffice commands)

### Curator's migration applier needs a predicate guard for ALTER-style migrations
`_ensure_schema` skipped a migration only if a *sentinel table* existed — fine
for CREATE TABLE files, useless for an ALTER (the table already exists). Added a
second guard kind: a boolean SQL predicate (`is_nullable='YES'` for 003) so the
ALTER runs once and is skipped on every later boot. Without this it'd re-ALTER
on every connect (harmless but noisy).

### Test the controller's cross-schema read defensively — SQLite has no `public.*`
The moderation list reads `public.events`/`public.pages`, which don't exist in
the `:memory:` SQLite test DB. Like the cost dashboard, wrap the reads in
try/catch and render an empty list rather than 500. Command-publish tests use
`Http::fake()` against the mgmt API — no real broker needed.

### Re-synthesize in stub mode overwrites real page content — use a throwaway event to test
`event.resynthesize` re-runs the synthesize skill, which in stub mode (no
`ANTHROPIC_API_KEY`) writes a deterministic "Stub one-pager (offline dev)" over
the real headline/synthesis_md (source articles are untouched, so a real
re-synthesize regenerates it). When proving the command path against live data,
prefer a disposable event, or expect to re-run synthesis with real keys after.

## 2026-06-03 — Phase 2.1: DB-backed Curator config + key management

### Curator's asyncpg connection lives in `public`; cross-schema reads MUST be qualified
Laravel sets `search_path=backoffice,public`, but Curator's asyncpg pool has no
custom search_path, so it defaults to `public`. An unqualified
`SELECT ... FROM curator_settings` would silently fail to find the
Backoffice-owned table. Always schema-qualify the cross-schema read:
`backoffice.curator_settings`. (→ ADR-0004, ADR-0003)

### Refresh-without-redeploy = mutate the *same* cfg objects in place
The skills (`EnrichSkill.llm_cfg`, `ClusterSkill.cfg`) and the orchestrator hold
**references** to the same `LlmCfg` / `ClusterCfg` instances created at boot.
So applying DB settings by mutating those objects' attributes in place (not
rebuilding `CuratorConfig`) makes a change visible on the very next event with
no re-wiring. Pydantic v2 models are mutable by default, so this just works.

### Keep provider keys in env — don't make Python decrypt Laravel's `encrypted` cast
Laravel's `encrypted` cast is AES-256-GCM with a PHP-specific JSON envelope
(`{"iv":...,"value":...,"mac":...}`) keyed by `APP_KEY`. Re-implementing that in
Python to read `api_keys` would be fragile cross-language crypto for zero v0
benefit, since Curator already has the keys in its environment. Decision:
`api_keys` is a management vault for the admin (store/rotate/mask/test);
Curator's key-loading stays env-only. (→ ADR-0004)

### Migrations that seed must run on the test DB too (SQLite in-memory)
`phpunit.xml` uses `DB_CONNECTION=sqlite` / `:memory:`. The `curator_settings`
migration seeds its single row with `DB::table()->insert(['id'=>1,...])`, which
works identically on SQLite and Postgres — verify new seed/`down()` logic isn't
Postgres-only or the whole suite breaks under `RefreshDatabase`.

### Laravel `$hidden` + an explicit `masked()` is the safe key projection
Marking the `encrypted` `value` column as `$hidden` stops it leaking through any
accidental `->toArray()` / `->toJson()`, while a dedicated `masked()` (last-4)
is the only thing the controller ever sends to the client. Never project the
raw decrypted value into an Inertia prop.

## 2026-06-02 — Monorepo unification, kernel consolidation, Docker, Reader admin

### Symlinks on `sys.path` shadow installed packages — silently
A tracked symlink `apps/scraper/inkbytes -> src/inkbytes` (where `src/` was
*untracked*) made `import inkbytes` resolve to the symlink locally, because the
**cwd wins on `sys.path`** and shadows an editable-installed package. On a fresh
clone (no `src/`) the symlink dangled and Python fell back to the installed
package — so **local and CI ran different code** with no error. Lesson: consume
shared libs via their installed distribution, not path-shadowing symlinks; a
shared package that fails *loudly* (ImportError) beats one that silently uses
stale code. (→ Messor ADR-0007)

### `git check-ignore` on a directory is misleading
`git check-ignore -q somedir/` can report a directory as ignored (matching `/*`)
even when its **contents** are re-included by a later `!somedir/` negation. The
decisive test is whether a real *file inside* is ignored, not the directory
itself. Don't trust a directory-level check; test a file path. (Initial alarm
that `git add` would skip `database/common/models` was a false positive from
exactly this.)

### A directory containing `.git` is added as a gitlink, not recursed
Even with the contents un-ignored, `git add` treats any dir holding a nested
`.git` as an embedded repo (mode 160000 gitlink). You must remove the nested
`.git` first for the files to be tracked. This is why severing the GitLab module
repos was a prerequisite to absorbing their source. (→ root ADR-0001)

### Docker build context vs. symlinks pointing outside it
Kernel symlinks pointed to repo-root dirs *outside* the `Messor/` build context,
so they couldn't be copied — which is why the old Dockerfile cloned them from
GitLab. Either widen the context (and pay for it) or make the artifact
self-contained. We chose self-contained. (→ Messor ADR-0007)

### `COPY`ing runtime artifacts blows up the image (and the disk)
`COPY apps/scraper` pulled in 710 MB of `data/history` + logs, filling Docker's
disk mid-build (`no space left on device`). The build context was 1.68 GB.
Excluding runtime dirs in `.dockerignore` dropped it to ~671 KB. Always exclude
`data/`, `logs/`, and sibling apps from a service image; bind-mount runtime dirs.

### …but then create the runtime dirs in the image
After excluding `logs/`, the container crashed at startup: the logger opens
`logs/messor.log` **eagerly** at import. An image that excludes bind-mounted
dirs must `mkdir -p` them so it still runs standalone. Caught only by actually
running the built image — a static review would have missed it.

### EOF spin: `input()` on closed stdin loops at full speed
In a non-TTY (Docker, CI, `< /dev/null`, background), `input()` raises
`EOFError` *immediately and forever*. A generic `except Exception: log; continue`
turned that into **2.86 M error lines / 551 MB logs** from a single run — a
disk-filler on a 24/7 service. Fix: detect `not sys.stdin.isatty()` and don't
enter the REPL at all.

### …but "don't enter the REPL" must not kill the server
The first EOF fix returned from `process_commands()`, which tore down the API
server when `main.py` was launched in the background to serve the admin client
(the old spin had kept it alive by accident). Resolution: distinguish
**one-shot** (queued `--scrape` command → exit) from **serve mode** (bare
`main.py` → block on `exit_event.wait()` to keep the API alive). (→ Messor
ADR-0007 follow-up)

### `fetch()` does NOT reject on HTTP error status
Reader `/admin` crashed with `outlets.map is not a function`. Root cause: the
proxy returns `{error}` with a **502** when Curator is down, but
`fetch().then(r => r.json())` resolves (not rejects) on non-2xx — so `.catch`
never fired and the error *object* flowed into `setOutlets`. Always check
`r.ok` (throw) and defensively coerce API responses to the expected shape
(`Array.isArray(o) ? o : []`).

### Next.js 16 allows only one `next dev` per app directory
You cannot run a second `next dev` for the same app, even on a different port —
it detects the running instance and exits. Combined with auth (`/admin` →
`307 /login`, and credentials are off-limits to the agent), a parallel headless
browser verification of an authed page isn't possible while the user's server
runs. Verify what you can (compiles, route returns 307 not 500, upstream
trigger reproduced) and hand the authed visual check to the user.

### Curator `--api-only` serves the Reader without LLM keys
The Reader `/admin` only needs Curator's `/status` + `/outlets`, which read the
DB. `python main.py --config env.local.yaml --api-only` serves them with no
`ANTHROPIC_API_KEY`/`OPENAI_API_KEY` (stub-mode warnings are expected and
harmless). LLM keys are only needed for the `--consume`/`--fixture` pipeline
that *creates* enriched articles and pages.

> Note: the Reader `/admin` is **transitional** — system ADR-0001 (Laravel
> Backoffice consolidation) calls for deleting it and moving admin into the
> Backoffice. Fixing its crash + serving it via Curator was about unblocking
> the immediate "it's broken" state, not endorsing it as the long-term admin.

### Laravel + Curator in one Postgres: schema isolation, not `migrate:fresh` (Phase 1.1)
Moving the Laravel Backoffice off SQLite onto Curator's shared Postgres required
isolating it in a `backoffice` schema (`'search_path' => 'backoffice,public'` in
the `pgsql` connection). With `backoffice` first in the search_path, Laravel's
`migrations` table and every Laravel-owned table land there automatically — no
per-migration schema annotations needed — while cross-schema reads of Curator's
`public` tables still resolve. The schema must be created out-of-band first
(`CREATE SCHEMA IF NOT EXISTS backoffice;`); Laravel won't create it. Run a
**scoped `php artisan migrate`**, never `migrate:fresh` (it would drop Curator's
live `public` data). See ADR-0003.

When dropping the legacy Laravel `sources`/`articles` migrations, also drop
anything that FK-references them: `scrape_runs` pointed a `foreignIdFor(Source)`
at the deleted `sources` table, and `add_view_tracking` only altered
`scrape_runs` — both had to go for the set to migrate cleanly. `scraping_jobs`
was standalone (no FK to the dropped tables) and was kept. The orphaned
`Source`/`ScrapeRun`/`Article` models + their controllers/routes still exist and
will 500 at request time; per the handoff those Sources/Runs/Articles views are
reworked in Phase 1.2, so they were left in place (they don't break boot or
migrate, only the specific authed routes).

### Persisting per-call cost from a sync meter via an async DB sink (Phase 2.2)
Curator's `CostMeter.record()` is synchronous and is called from inside
`LlmService.structured()` (which *is* async) right after reading the
completion's token usage. To add a DB sink without making the meter async or
threading a DB handle through every call site, the meter takes an optional
async sink (`set_sink(db.record_model_usage)`) and schedules it
fire-and-forget with `loop.create_task(...)` *outside* the meter's lock. Two
things that matter:

- **Non-fatal by construction.** The whole sink path is wrapped so a DB/logging
  failure is caught and logged, never propagated — accounting must never break a
  real LLM call. The in-memory totals + the existing `COST …` log line are kept
  exactly as-is and run *before* the sink, so even if persistence fails the
  operator still sees the run total. Verified by pointing the sink at a function
  that raises: `record()` returned normally and only logged a WARNING.
- **No running loop ⇒ skip, don't block.** `record()` guards
  `asyncio.get_running_loop()`; in a sync context (a unit test, a future sync
  caller) there's nothing to schedule onto, so it logs a debug line and skips
  the write rather than blocking. In the real pipeline `structured()` is always
  on the loop, so writes happen.

`event_id` is threaded only where it's cheap: synthesize passes the cluster's
event id; enrich passes `None` (no event exists pre-clustering), which is why
the column is nullable.

### `date_trunc` is Postgres-only — make dashboard aggregations driver-aware
The cost dashboard groups spend "by day". `date_trunc('day', created_at)` is
correct in prod (Postgres) but the Laravel feature tests run on **SQLite
in-memory**, where `date_trunc` doesn't exist and the request 500s. Fix: pick
the day-bucket expression from `getConnection()->getDriverName()` —
`to_char(date_trunc('day', …), 'YYYY-MM-DD')` for `pgsql`, `strftime('%Y-%m-%d', …)`
for sqlite. Same lesson for the cross-schema denominators: the dashboard reads
`public.articles`/`public.pages` for the per-1000-articles / per-page figures,
which don't exist under the SQLite test DB, so those count reads are wrapped to
fall back to 0 — the read-only dashboard renders instead of erroring. Both keep
prod behaviour identical while letting the suite stay on SQLite.

### B1 audit log — `public.outlets` can't be exercised over HTTP in SQLite tests
The Backoffice `Outlet` model is bound to `protected $table = 'public.outlets'`
(Curator owns that DDL; ADR-0003). Under the feature suite's **SQLite in-memory**
DB there is no `public` schema — Laravel parses the dotted name as
`connection.table`, so an outlet route under test fails with *"Database connection
[public] not configured."* The apikey + settings audit paths *can* run over HTTP
(those tables are Laravel-migrated into the test DB), so they assert the full
controller→recorder wiring; the outlet path is instead covered by (a) a unit-style
test that calls `AuditLog::record()` directly with outlet-shaped before/after and
(b) a tinker run against real Postgres. Takeaway: any feature test that touches
`public.*` tables over HTTP will not run on the SQLite suite — verify those paths
against Postgres (tinker/feature-on-pgsql) and keep the SQLite suite to
Laravel-owned tables.

### Keep secret material out of `audit_logs` at the *caller*, not the model
The audit recorder is generic (`record($action, $type, $id, $before, $after)`),
so it can't know which fields are sensitive. The rule is enforced where secrets
live: `ApiKeyController` has a dedicated `auditSnapshot()` returning only
`provider` / `label` / `masked` (last-4) / `active` — never the raw or encrypted
`value`. A feature test scans the **raw stored** `before`/`after` JSON columns for
both the original and rotated secrets (and for the literal `sk-` prefix) and
asserts neither is present, so a future refactor that accidentally widens the
snapshot is caught.

### Best-effort audit writes — wrap and warn, never 500 the real action
`AuditLog::record()` wraps the insert in try/catch and logs a `WARNING` on
failure (same philosophy as the cost-meter sink). An audit hiccup (DB blip,
missing table) must never break the outlet/key/settings mutation it's recording.
Verified by dropping the `audit_logs` table mid-test and asserting `record()`
returns normally instead of throwing.

### B2 RBAC — gate at the route, test on SQLite by relying on middleware order
The `role` middleware runs **before** the controller, so a forbidden role gets
its 403 before any Postgres-backed controller logic runs. That's what lets the
gating feature tests assert cleanly on the **SQLite in-memory** suite even for
routes that read Curator's `public.*` tables (e.g. `outlets.store`, which
validates with `Rule::unique('public.outlets')`). For the *positive* direction —
proving an operator/admin **passes** the gate — those `public.*` routes can't run
to completion under SQLite, so the test asserts the status is simply **not 403**
(the request continues past the gate to a non-auth failure), while the
fully-self-contained moderation action POSTs (RabbitMQ mgmt API is HTTP-faked)
give a clean 302 to prove the operator tier end-to-end. Takeaway: order your
middleware so the cheap authz check fires first, and your gating tests stay DB-agnostic.

### Default new users to the least-privileged role, guard the last admin
New self-service Breeze registrations default to `viewer` (least privilege — an
admin must promote them). The factory, by contrast, defaults to `admin` so the
pre-existing feature suites (which exercise mutations) keep passing unchanged;
explicit `->viewer()` / `->operator()` / `->admin()` states drive the RBAC tests.
Role changes go through `UserController::updateRole`, which blocks demoting the
**last remaining admin** (zero-admin lockout) — enforced in the controller, not a
DB constraint, and audited as `user.role_changed`. Role itself is a plain string
validated against `User::ROLES` (not a Postgres CHECK) so SQLite and Postgres
behave identically and the allowed set lives in one constant.

### B3 outlet health — "success rate" needs Messor, not Curator
The obvious "success rate" column for outlets is **not computable from the
Backoffice**. Curator's `public.articles` only stores articles that scraped
*successfully*; it has no record of attempts or failures. A true success rate
(succeeded / attempted) requires Messor's per-cycle run history — which is a
separate, future backlog item (B4). So B3 deliberately shows **volume +
recency + events contributed** (article count, last-scraped relative time,
distinct events the outlet fed) plus a **health chip** derived from
active-flag + recency, and explicitly does NOT fake a rate. Lesson: before
adding a "rate" metric, check that *both* numerator and denominator actually
live in the table you're reading — a partial table (successes only) silently
turns any rate into a meaningless 100%.

### Cross-schema stats: one grouped query + try/catch fallback, keyed by slug
Per-outlet stats join `public.articles.outlet_id = public.outlets.id` (the
TEXT slug, not an int). One `GROUP BY outlet_id` query (count, max(scraped_at),
count(distinct event_id)) is fetched once and attached to each outlet by id in
PHP — no N+1. The whole read is wrapped in try/catch returning `[]` so the page
renders with null/0 stats when `public.articles` is absent (SQLite suite /
un-migrated Curator) — same defensive pattern as the moderation and cost
dashboards. Tests assert the fallback under SQLite; the populated payload is
Postgres-only and tinker-verified (apnews art=158/evt=132, bbc 0/null).

### B6 unified health — defensive probes, a non-standard Messor reachability check, creds stay server-side
The health dashboard's only real complexity is *not letting one dead service
break the page*. Each component (Postgres / Curator / Messor / RabbitMQ) is its
own method with a **~2s `Http::timeout()` + try/catch**, returning
`up`/`down`/`unreachable` rather than throwing. Verified by pointing
`CURATOR_URL` at a dead port: connection-refused returns in ~9ms and the total
request was 82ms with the other services still green — the timeout caps a
*slow* (vs refused) service so the page can't hang. Two non-obvious points:
(1) **Messor has no `/health`** (it 404s), so reachability is probed with the
cheapest real read, `GET /api/scrapesessions?page=1&limit=1` — when probing a
service for liveness, confirm the health endpoint actually exists before relying
on it, and fall back to a known-cheap 200 route. (2) **RabbitMQ creds reuse the
existing `services.curator.rabbitmq.*` config** (same as `CuratorCommandService`
— don't duplicate creds) and are used only to build the server-side basic-auth
client; the returned payload contains only `status`/`latency_ms`/`queues`, so no
user, password, or `:15672` mgmt URL ever reaches the Inertia props (asserted by
a test that scans the rendered response for the secret + a tinker check of the
component payload). Lesson: when a screen exists to *observe* infra, the
observation must be cheaper and safer than what it observes — bounded time, no
500s, and no leakage of the credentials used to reach it.

### B11 alerting — dedup as a DB invariant, "don't alert on your own blindness", and the Http::fake merge trap
The evaluator's job is to *not* spam: a condition that stays true for hours must
be **one** open alert, not one per 5-minute run. We made dedup a **DB
invariant**, not just app logic — a **partial unique index `(dedup_key) WHERE
status='open'`** (Postgres + SQLite both support it) so even a concurrent
`alerts:evaluate` can't open two rows for the same key. The app-side upsert
(`raise()`: find-open-by-key → refresh, else create) is the fast path; the index
is the safety net. We deliberately chose **no auto-resolve** — when a condition
clears, the open alert stays for a human to acknowledge, because a *cleared*
alert is still operationally interesting and auto-closing would hide flapping.
Acknowledge (not resolve) is the only state transition the UI offers.

Second principle: **never alert on your own inability to observe.** The
`scrape_low_success` rule reads Messor over HTTP; if Messor is unreachable the
rule **returns 0 (no alert)** rather than raising "scrape is broken" — a probe
failure is not the same as a bad signal (`pipeline_stalled` has a separate, more
deliberate basis: no harvest in N h OR a real RabbitMQ backlog). Likewise the
RabbitMQ backlog check returns `null` (skip the symptom) when the mgmt API is
down. Each of the four rules is **independently try/caught** and the command
always exits 0 — it's a background evaluator, not a health gate, so one dead
probe must never abort the sweep.

The testing gotcha worth remembering: **`Http::fake()` calls MERGE, and earlier
stubs win.** Registering a catch-all `['*' => 500]` in `setUp()` and then a
specific `['*/api/scrapesessions*' => 200, ...]` in a test does **not** override
— the `*` from setUp matches first and you get 500. Fix: don't register a
catch-all in `setUp` (use only `Http::preventStrayRequests()`); let each test
register its own fakes **first**, so its specific-pattern-then-`*` ordering
actually applies. Tinker-reproduced both the broken merge and the fix before
trusting the suite.

### B12.1 durable scrape sessions — "emit→consume" beats "give the harvester a DB", and the asyncpg timestamptz cast trap
ADR-0006 said "Messor persists scrape sessions to Postgres." Implementing it, the
better mechanism was **Messor emits, Curator persists**: Messor already owns
RabbitMQ publishing (`event.article.scraped`), so a sibling
`scrape.session.completed` event on the same `messor` exchange costs nothing new
and keeps Messor **Postgres-free**, while the DB owner (Curator) stays the sole
writer to `public.scrape_sessions`. We refined the ADR to record the accurate
mechanism rather than leave the doc saying "Messor persists." Lesson: when an ADR
fixes the *decision* (Option B: durable in Postgres, one owner of dedup) but the
*mechanism* line is loose, implementing it is the right time to tighten the
mechanism — same decision, accurate words.

**Granularity:** Messor completes work **per outlet** (`create_outlet_scraping_session`
in a thread pool), but the run-level view `/api/scrapesessions` shows **one row per
run across outlets** (grouped by the file timestamp prefix). So we emit **once per
run** at the run boundary (`execute_scraping_process`), keyed `session-<unix_ts>`,
accumulating the per-outlet stats Messor already computed into an `outlets[]` array —
not one event per outlet. Curator upserts `ON CONFLICT (session_id)` so a re-emit
refreshes the same row. Matching the existing view's key shape means the future
Backoffice browser (B12.2) reads the same identifiers the old client showed.

**The asyncpg gotcha that cost a round-trip:** passing an **ISO-8601 string** for a
`timestamptz` column fails with `TypeError: expected a datetime.date or
datetime.datetime instance, got 'str'` — and a `$2::timestamptz` **cast in the SQL
does not help**, because asyncpg encodes each parameter against the column's type
*before* the server-side cast runs. Fix: parse the string to a real `datetime` in
Python before binding (`datetime.fromisoformat`, after swapping a trailing `Z` for
`+00:00` since <3.11 rejects `Z`). The defensive handler caught it (logged + ACKed,
never wedged the consumer), which is exactly why the consumer is wrapped that way —
a malformed/unstorable run summary is non-fatal history, never a pipeline stop.
Lesson: for asyncpg, coerce types in Python; SQL casts are not a substitute for the
client-side codec.

### B13 UX polish — auto-surface flash in the provider, not the page
The 6 pages with bespoke `Snackbar`s each repeated the same `useEffect(() =>
{ if (flash.success) setSnack(...) }, [flash])`. Putting that one effect inside
the shared `ToastProvider` (mounted once in `AppLayout`) meant **flash-only pages
delete their effect *and* their state entirely** — they wire nothing and still
get toasts. Only the two pages with *imperative* toasts (ApiKeys key-test result,
ScrapingJobs trigger result) needed `useToast()`. Lesson: when a cross-cutting
behavior (here: echo server flash) is identical on every page, hoist it into the
provider so the common case becomes zero-config; reserve the hook for the genuinely
page-specific calls.

**Outlets kept its `flash` read** — it uses `flash.importPreview` (B10) for the
import-diff dialog, which is *not* a toast. So its `useEffect` shrank to only the
preview branch; the toast branches moved to the provider. Lesson: "migrate off
local Snackbar" doesn't mean "stop reading flash" — separate the toast concern from
other transient flash payloads.

**Tables go responsive for free.** MUI `TableContainer` already sets
`overflow-x:auto`, and the theme doesn't override it, so every wide table (Outlets'
13 columns included) scrolls horizontally inside its container at 375px instead of
blowing out the page — no cards-vs-scroll rewrite needed for a "don't break it"
mobile pass. Verified by reasoning from the MUI default + absence of a theme
override rather than standing up the full stack.

---

## 2026-06-07 — Production stability sprint

**Docker exit code 0 ≠ clean exit.** When Messor crashed due to OOM, the container
exited with code 0 (not the typical OOM 137). The `OOMKilled` field in `docker inspect`
and memory watermark events are the reliable signals. `RestartCount` also resets on
`--force-recreate`, masking the true restart history.

**newspaper3k has no default timeout and will hang forever.** `paper.download_categories()`
spawns threads internally and can block indefinitely on slow/blocked outlets. Always set
`request_timeout` in the build config AND wrap the outer `scrape_outlet()` call in a
`concurrent.futures` timeout. Without both, a single outlet can freeze the entire scraper
process for hours.

**`restart: unless-stopped` + immediate cycle start = crash amplification.** A service
that crashes and restarts immediately fires its startup work again. 4 crashes in 10 min
= 4 concurrent full-outlet scrapes. Always add a configurable startup delay
(`MESSOR_STARTUP_DELAY_MINUTES`). FastAPI/healthcheck can still start immediately; only
the business cycle should delay.

**GitHub Actions matrix jobs cannot reference `matrix.*` in their `if:` condition.**
The `if:` at job level is evaluated before matrix expansion. Use separate named jobs
per service with `if: needs.changes.outputs.X == 'true'` instead of a matrix with
a complex `if`. The `dorny/paths-filter` action is the standard solution.

**React hydration error #418 = `Date.now()` mismatch between server and client.**
Any call to `Date.now()` or `new Date()` in a Next.js server component (or during
the initial render of a `"use client"` component) produces different output on server
vs client because they run at different times and may have different timezone context.
Use `suppressHydrationWarning` on the specific `<span>`, or move the computation to
`useEffect + useState` so it only runs client-side.

**Messor "success rate" was counting duplicates as failures.** `failed_articles` in
Messor's session data = duplicates + true parse failures. The stored `success_rate`
was `successful / total`, so a session with 90% duplicates and perfect parsing showed
10% success. Real parse success = `successful / (total - duplicates)`. Fix display
in the controller, not in Messor's accounting (which is correct for its dedup purpose).

**Docker Compose `container_name` gets UUID-prefixed after daemon restart.** When
`systemctl restart docker` is needed (zombie container), named containers may be
re-registered with a `{containerID}_` prefix. Other containers resolving the service
by name fail. Fix: `docker stop + rm` the prefixed container, then `up -d --force-recreate`.

**Al Jazeera throttles sequential scrapes from the same IP.** Two scrape cycles 15 min
apart dropped parse success from 60% → 1.4%. newspaper3k makes one HTTP request per
article URL; 350+ requests to the same CDN in rapid succession triggers throttling.
RSS/Atom-first approach (1 feed request → N article fetches spread over time) will
mitigate this. Short-term: disable the outlet.

**Alphabetical outlet ordering creates hot batches.** With 4 concurrent threads and
outlets sorted A→Z, the same 4 outlets (acento, aljazeera, apnews, clarin) always
run together in the first batch. Adds `random.shuffle(outlets)` before the thread pool
starts — cost zero, removes structural bias.

**Feed sort formula can freeze the top of the news feed.** A scoring formula that
weights `source_count` heavily will permanently rank old multi-source events above
fresh single-source events. For a news reader, recency should be primary. Use
`freshness_at` (timestamp) as the primary sort key with `source_count` only as a
tiebreaker within the same scrape window.
