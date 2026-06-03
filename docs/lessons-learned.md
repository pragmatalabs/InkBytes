# InkBytes — Lessons Learned

> *Status: living doc · Owner: Julián · Last updated: 2026-06-02*

Hard-won, non-obvious gotchas. Add to this whenever something surprises you or
costs real debugging time. Newest first.

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
