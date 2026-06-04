# ADR-0008 — `--no-api` flag for Backoffice-triggered harvests

> *Status: v1 · Owner: Julian · Last updated: 2026-06-04*

## Context

The InkBytes Backoffice (Laravel, `Messor/apps/platform`) exposes a
**"▶ Iniciar Scraping"** button. It POSTs `/scraping/trigger` →
`ScrapingJobController@trigger`, which dispatches a queued `RunScrapingWorker`
job on the `scraping` queue. With `SCRAPING_REMOTE_HOST` empty the worker runs
`config('scraping.command')` locally via `bash -lc`.

The button did nothing. Three independent root causes:

1. **`SCRAPING_COMMAND` unset** in `apps/platform/.env` → `trigger` returned
   422 `"SCRAPING_COMMAND is not configured."`.
2. **No queue worker** consuming the `scraping` queue
   (`QUEUE_CONNECTION=database`) → a dispatched job never executes.
3. **Port clash on :8050.** `main.py` always started the FastAPI server
   (`Application.run()` called `self.api_server.start()` unconditionally). The
   dev `messor-api` already owns :8050, so a button-triggered `main.py --scrape`
   would fail to bind ("address already in use"). The harvest must run **without**
   the API.

## Decision

1. **Add a `--no-api` flag to Messor.** `main.py` parses `--no-api`
   (`store_true`) and passes `no_api=True` into `Application.run(...)`; `run()`
   skips `self.api_server.start()` when set. Everything else (the one-shot
   `--scrape` path, the non-interactive EOF-clean exit, `--schedule`, serve mode)
   is unchanged. A one-shot harvest can now coexist with a running messor-api:

   ```bash
   python main.py env.local.yaml --scrape=--limit=2 --no-api < /dev/null
   ```

2. **Set `SCRAPING_COMMAND`** in `apps/platform/.env` (gitignored) to the no-api
   one-shot harvester with absolute paths and non-TTY stdin; document a commented
   example in the committed `.env.example`. On Apple Silicon the command is
   prefixed with `arch -arm64` (see Consequences).

3. **The Backoffice requires two background processes**, documented in
   `docs/STATUS.md` and `Messor/CLAUDE.md`:
   - `php artisan queue:work --queue=scraping --timeout=0` — scraping jobs
   - `php artisan schedule:work` — B11 alert cron

## Consequences

- A Backoffice-triggered harvest writes staging JSON + emits RabbitMQ
  `event.article.scraped` events; it does **not** touch Curator's `public.*`
  tables (verified: `articles`/`events`/`pages` counts unchanged before/after).
- **Apple Silicon / Rosetta gotcha:** the local `php` (and therefore the queue
  worker and the `bash -lc` it spawns) is an x86_64 build running under Rosetta.
  A child invocation of the arm64 Messor venv then loads under the x86_64
  personality and fails with *"pydantic `.so` … incompatible architecture
  (have 'arm64', need 'x86_64')"* — even though the same command run from a
  native arm64 shell works. Pinning the interpreter with `arch -arm64` in
  `SCRAPING_COMMAND` forces the native interpreter regardless of the parent
  process architecture. Documented in `.env.example`. (Not needed once the
  Backoffice runs in a Linux container in prod, but harmless there.)
- `--no-api` is also the right primitive for production scheduled harvests that
  should not stand up an API surface.

## Alternatives considered

- **Make `api_server.start()` tolerate a bound port (catch the bind error).**
  Rejected: it would silently swallow a real misconfiguration and leave the
  process thinking it owns :8050. An explicit opt-out flag is clearer.
- **Run the trigger over SSH (`SCRAPING_REMOTE_HOST`).** That path already exists
  in `RunScrapingWorker` for prod, but for local dev a direct `bash -lc` against
  the same checkout is simpler and avoids needing an SSH loopback.
