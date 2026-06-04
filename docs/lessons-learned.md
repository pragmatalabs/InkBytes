# InkBytes — Lessons Learned

> *Status: living doc · Owner: Julián · Last updated: 2026-06-03*

Hard-won, non-obvious gotchas. Add to this whenever something surprises you or
costs real debugging time. Newest first.

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
