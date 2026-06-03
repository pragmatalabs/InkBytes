# Messor — Sprint-1 Backlog

> *Sprint length: 2 weeks · Goal: tick every box in [v1-scope §7 Definition of Done](./v1-scope.md#7-definition-of-done-v1) · Last updated: 2026-06-02*

The backlog is informed by the local-dev tune-up performed on 2026-06-02
(see [local-dev.md](./local-dev.md)). Stories below are ordered to unblock
the next one each time.

## Sprint goal

> Messor v1 builds, runs, and survives one full week in staging — single
> instance, local outlets file, RabbitMQ events + DO Spaces only, secrets
> via env vars.

## Stories

### INK-1 — Retire the `inkbytes` symlink, ship a real package

**Why now:** the symlink is the #1 footgun for new contributors. Local-dev
tune-up confirmed the symlinks were empty in `src/inkbytes/` and the only
reason imports work is brittle path tricks.

**Definition of done**

- Move `common/`, `models/`, `database/` content under
  `packages/inkbytes/inkbytes/{common,models,database}/`.
- Add `packages/inkbytes/pyproject.toml` (name `inkbytes`, version
  `0.1.0`).
- `apps/scraper/requirements.txt` references the package via a relative
  path install: `-e ../../packages/inkbytes`.
- Remove `Messor/inkbytes` and `Messor/apps/scraper/inkbytes` symlinks.
- All imports in `apps/scraper/**/*.py` keep working unchanged.
- One green CI run.

**Estimate**: 5 pts (mostly mechanical)

---

### INK-2 — Pin and fix `requirements.txt`

**Why now:** local-dev tune-up showed `requirements.txt` is missing
`lxml_html_clean` (newspaper3k won't import on modern lxml). Several pins
are also stale.

**Definition of done**

- Add `lxml_html_clean` to `requirements.txt`.
- Bump `lxml` to a version that pairs with it (5.2+).
- Drop dead deps: `articles==0.1.0` (poetry-only, fake), `common==0.1.2`
  (shadowed by INK-1), `logger==1.4` (we ship our own).
- Pin Python to `>=3.10,<3.13` in `pyproject.toml`.
- `pip install -r requirements.txt` in a fresh venv finishes without
  errors.
- Document the install in `local-dev.md` §2 (already drafted there).

**Estimate**: 3 pts

---

### INK-3 — Production-grade Dockerfile + health endpoints

**Why now:** v1-scope DoD requires `/healthz` returning 200 within 30s of
start and `/status` reporting last cycle.

**Definition of done**

- New `apps/scraper/Dockerfile` (non-root user, NLTK data baked in,
  `HEALTHCHECK` against `/healthz`).
- Add `GET /healthz` → `{"ok": true}` 200 always.
- Add `GET /readyz` → 200 when RabbitMQ + Spaces both reachable, 503
  otherwise with `{"checks": {...}}`.
- Add `GET /status` → JSON with `last_run_at`, `last_run_duration_seconds`,
  `outlets_total`, `articles_total`, `errors_total`, per-outlet breakdown.
- `docker build` succeeds from repo root, image size < 600 MB.
- `docker run` shows `/healthz` green within 30 s.

**Estimate**: 5 pts

---

### INK-4 — Env-var overlay for config (`pydantic-settings`)

**Why now:** secrets must come from env vars in production. v1-scope DoD
requires "all secrets read from env vars; none in the image or in git."

**Definition of done**

- Adopt `pydantic-settings` (or a hand-rolled overlay) in
  `core/config.py`.
- Every secret in `configuration.md` §4 is overridable by its mapped env
  var (`DO_SPACES_KEY`, `DO_SPACES_SECRET`, `PLATFORM_API_TOKEN`,
  `RABBITMQ_URL` parsed into host/port/user/pass/vhost, `OPENAI_API_KEY`).
- The `__SET_VIA_ENV__` literal in `env.yaml` causes a clear startup error
  if not overridden.
- Unit tests for the overlay (10 tests minimum).

**Estimate**: 5 pts

---

### INK-5 — Drop TinyDB and Strapi from `apps/scraper`

**Why now:** v1-scope explicitly removes both.

**Definition of done**

- Remove all `tinydb` imports and `inkbytes.database.tinydb.*` references
  from `apps/scraper/**`.
- Delete `strapi_cms` config block and the dead-path code branches in
  `core/config.py` and the services that consume it.
- `OutletService` reads only from local JSON file in v1 (platform API path
  is deferred behind a feature flag for v2).
- All previously passing imports still pass.

**Estimate**: 3 pts

---

### INK-6 — Tenacity retries around outbound I/O

**Why now:** today's code does no retries; one transient outlet 5xx or DO
Spaces hiccup loses the cycle's work.

**Definition of done**

- Wrap `core/scraper.scrape_outlet` HTTP calls with Tenacity
  (`@retry(stop=stop_after_attempt(3), wait=wait_exponential())`).
- Wrap DO Spaces upload in `StorageService` similarly.
- Wrap RabbitMQ publish in `MessageService` similarly.
- Add a per-outlet circuit breaker: 5 consecutive failures → skip outlet
  for the next 3 cycles, then re-try.
- Tests for each wrapper.

**Estimate**: 5 pts

---

### INK-7 — Lock the v1 RabbitMQ event schema

**Why now:** Entopics will consume these events. No schema = no contract.

**Definition of done**

- Create `packages/contracts/events/article-v1.json` (JSON Schema).
- Pydantic model `ArticleEventV1` in `packages/inkbytes/inkbytes/contracts/events.py`.
- Every event published by `MessageService` is validated against the
  schema; invalid ones are logged + dropped (never published).
- Schema field `"schema": "inkbytes.article.v1"` is mandatory.
- Round-trip test: produce one event, consume from RabbitMQ, model-load
  it, assert equality.

**Estimate**: 5 pts

---

### INK-8 — `.do/app.yaml` and DO App Platform deploy

**Why now:** Last DoD box.

**Definition of done**

- `.do/app.yaml` at repo root targeting `apps/scraper` as a worker.
- All env vars from INK-4 declared (secrets marked as `SECRET`).
- `master` push triggers autodeploy to the **staging** environment.
- `/healthz` green from public URL within 2 min of deploy.
- First scheduled cycle observed in DO logs within 60 min.

**Estimate**: 5 pts

---

### INK-9 — CI: lint + test + build image

**Why now:** every story above needs CI to catch regressions. Cheap to do
once.

**Definition of done**

- `.github/workflows/ci.yml` runs on PR + push to master.
- Steps: ruff lint → pytest → `docker build` → push to GHCR on master.
- Build matrix: Python 3.10 + 3.11.
- Cache `pip` and Docker layers.
- README badge.

**Estimate**: 3 pts

---

### INK-10 — Staging soak test

**Why now:** v1 ships when 7 consecutive days of green cycles pass.

**Definition of done**

- Deploy a commit tagged `v1.0.0-rc1` to staging.
- Cycle interval = 60 min.
- Daily health snapshot recorded for 7 days.
- Zero unplanned restarts.
- All 7 days: `articles_total > 0`, `errors_total / articles_total < 5%`.
- Promote to prod once green.

**Estimate**: 2 pts active + ~7 days wall time

---

## Out of Sprint-1 (parking lot)

- Outlet trust scoring (v2)
- Multi-host horizontal workers (v2 / M3)
- OpenTelemetry tracing (v2)
- Outlet intake API in Laravel platform (v2)
- Reader UX changes (separate squad / repo)

## Sprint capacity check

Total points: **41**. For a team of two engineers + occasional infra
support over 10 working days, that's tight. If capacity is one engineer,
**descope INK-9 and INK-10 to Sprint-2** and target **31 pts**.

## Suggested order

```text
Day 1-2:   INK-2 (deps) ─►  INK-1 (package)
Day 3-4:   INK-5 (drop dead code) ─►  INK-4 (env overlay)
Day 5-6:   INK-3 (Docker + health)
Day 7-8:   INK-6 (retries) ─►  INK-7 (event schema)
Day 9:     INK-9 (CI) ─►  INK-8 (deploy)
Day 10:    INK-10 starts (7-day soak)
```

## Acceptance — sprint review

For each story above:

- [ ] Demoed end-to-end (not just merged)
- [ ] No `TODO(sprint-1)` left in the diff
- [ ] Doc updated (`docs/<area>.md`)
- [ ] ADR added or amended if a non-trivial decision was made

---

**Backlog format**: Jira-ready. Copy each `### INK-N` block into a story;
move "Definition of done" to acceptance criteria.
