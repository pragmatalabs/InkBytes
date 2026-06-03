# Messor — Dev Bring-Up Handoff (parallelisable tickets)

> *Goal: Messor running locally end-to-end in dev mode — scrape → JSON staging → DO Spaces stand-in (MinIO) → RabbitMQ event — observable from your laptop.*
>
> *Status: Ready · Owner: Julián de la Rosa · Last updated: 2026-06-02*

This is a sliced-up plan. Each **ticket** is small enough for one person (or
one agent) to own in under an hour and verify independently. Run them in
the order shown; tickets in the same phase can be done in parallel.

## Phase 0 — Pre-flight (you, on host terminal)

These need to happen before any agent runs.

### TKT-0.1 — Release the git lock

```bash
cd /Volumes/Pragmata/Projects/InkBytes
rm -f .git/index.lock
git status -s | head
```

**Done when:** `git status` exits 0 and doesn't complain about a lock.

### TKT-0.2 — Land the work in `master`

```bash
bash Messor/scripts/commit-v1-docs.sh
```

The script handles the two clean commits (migration + docs) plus pushes
to `origin/master`. Add the post-INK files manually if you've worked
between commits:

```bash
git add Messor/packages Messor/apps/scraper/core/staging_store.py \
        Messor/apps/scraper/requirements.txt \
        Messor/apps/scraper/pyproject.toml \
        Messor/apps/scraper/env*.yaml \
        Messor/apps/scraper/core Messor/apps/scraper/services \
        Messor/scripts/dev-up.sh Messor/scripts/dev-smoke.sh \
        Messor/infra/docker/dev-compose.yaml \
        Messor/docs
git commit -m "feat(messor): INK-1/2/5 — real inkbytes pkg, clean reqs, drop tinydb/strapi"
git push origin master
```

**Done when:** `git log -1 origin/master` shows the new commit.

### TKT-0.3 — Rotate the leaked tokens

The legacy `env.yaml` had real-looking DO Spaces / Strapi / Platform /
OpenAI / RabbitMQ creds. Rotate them in their provider consoles **today**.
History scrub (`git filter-repo`) is the follow-up after rotation.

**Done when:** rotated keys exist in 1Password/Doppler and the old keys
are revoked.

---

## Phase 1 — Bring Messor up (one agent, ~15 min)

### TKT-A1 — Run the bring-up script

```bash
cd /Volumes/Pragmata/Projects/InkBytes
bash Messor/scripts/dev-up.sh
```

This boots RabbitMQ + MinIO, creates `apps/scraper/.venv`, installs
deps, downloads NLTK data.

**Done when:** the script ends with the "Dev environment ready" banner
and these all work:

```bash
curl -fs http://localhost:15672                  # RabbitMQ UI HTTP 200
curl -fs http://localhost:9001                   # MinIO console HTTP 200
docker compose -f Messor/infra/docker/dev-compose.yaml ps   # all healthy
```

### TKT-A2 — Run one scrape cycle (file-only)

```bash
cd Messor/apps/scraper
source .venv/bin/activate
python main.py env.local.yaml --scrape
```

**Done when:**

- exit code `0`
- `data/scrapes/` contains at least one new JSON file (per outlet)
- console log shows `Duplicate filtering stats for <outlet>: Total: N | New: M | Duplicates: K`
- `scraping_session.json` exists at the project root

Run the smoke check:

```bash
bash Messor/scripts/dev-smoke.sh
```

All `PASS` lines should be green.

### TKT-A3 — Switch on the broker

Edit `env.local.yaml`:

```yaml
logging:
  destinations:
    - console
    - rabbit              # add this

rabbitmq:
  host: localhost         # was __SET_VIA_ENV__ before, fine for dev
  username: messor
  password: messor
  ssl: { enabled: false } # local broker is not TLS
```

Re-run a scrape:

```bash
python main.py env.local.yaml --scrape
```

**Done when:** RabbitMQ management UI (`http://localhost:15672`) shows
non-zero throughput on the `messor.logs` exchange.

---

## Phase 2 — Optional polish (parallel; pick what you need)

### TKT-B1 — Switch on the Spaces stand-in (MinIO)

Edit `env.local.yaml`:

```yaml
digitalocean:
  access_id: messor
  access_key: messor
  secret_key: messormessor
  region_name: us-east-1            # MinIO ignores this
  endpoint_url: http://localhost:9000

scraping:
  save_mode: send_to_api            # was local_only
```

Re-run. **Done when:** `mc ls local/inkbytes/messor/staging/` shows new
objects, or the MinIO console at `localhost:9001` lists them under
bucket `inkbytes`, prefix `messor/staging/`.

### TKT-B2 — Tail logs comfortably

In one terminal:

```bash
docker compose -f Messor/infra/docker/dev-compose.yaml logs -f rabbitmq
```

In another:

```bash
cd Messor/apps/scraper && source .venv/bin/activate
python main.py env.local.yaml --schedule        # continuous mode
```

**Done when:** every 60 minutes the scheduled loop runs and you can see
new messages in RabbitMQ UI without a restart.

### TKT-B3 — Inspect a staging file

```bash
ls -t Messor/apps/scraper/data/scrapes/ | head
jq '._default | to_entries | length' Messor/apps/scraper/data/scrapes/<file>.db.json
jq '._default | .["1"] | {id, title, language, publish_date, word_count: (.text | length)}' \
   Messor/apps/scraper/data/scrapes/<file>.db.json
```

**Done when:** a sane article record prints with title, language, and
non-empty text.

---

## Phase 3 — Stop / clean / restart

```bash
# Stop infra (data volumes persist)
docker compose -f Messor/infra/docker/dev-compose.yaml down

# Nuke infra including data
docker compose -f Messor/infra/docker/dev-compose.yaml down -v

# Reset Python env
rm -rf Messor/apps/scraper/.venv
bash Messor/scripts/dev-up.sh
```

---

## Verification checklist (definition of "Messor is up locally")

Tick all six for a green hand-off:

- [ ] `docker compose -f Messor/infra/docker/dev-compose.yaml ps` — all services healthy
- [ ] `Messor/scripts/dev-smoke.sh` exits 0 with all PASS
- [ ] At least one outlet returned ≥ 5 articles in a cycle
- [ ] RabbitMQ UI shows traffic on `messor.logs` exchange
- [ ] MinIO bucket `inkbytes` contains at least one object under `messor/staging/`
- [ ] `python main.py env.local.yaml --schedule` runs unattended for ≥ 2 cycles

When all six are ticked, Messor is **dev-ready** and we move to INK-3
(production Dockerfile + health endpoints).

---

## Who does what (suggested assignments)

| Phase | Owner role | Why |
|---|---|---|
| Phase 0 | You (repo admin) | Host-only access; sensitive (key rotation) |
| Phase 1 (A1–A3) | Pipeline agent | Owns Messor service code + config |
| Phase 2 / B1 | Infra agent | Owns dev-compose + MinIO/RMQ topology |
| Phase 2 / B2–B3 | Observability agent / QA | Owns dashboards + verification |
| Phase 3 | Anyone | Mechanical |

If you're solo: do Phase 0 → A1 → A2 → A3, skip Phase 2 until you need it.

## Troubleshooting (quick refs)

| Symptom | Fix |
|---|---|
| `dev-up.sh` says "docker not found" | Install Docker Desktop, restart shell, re-run |
| `ImportError: lxml.html.clean` | Already pinned via `lxml_html_clean` in requirements.txt |
| `No module named 'inkbytes'` | `pip install -e Messor/packages/inkbytes` |
| RabbitMQ refuses connection on :5672 | `docker compose -f infra/docker/dev-compose.yaml restart rabbitmq` |
| MinIO returns 403 to boto3 | Use `endpoint_url: http://localhost:9000` and key `messor` / secret `messormessor` |
| `nltk` punkt error | `python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"` |
| `git/index.lock` after a crash | `rm -f .git/index.lock` from host |

See [local-dev.md](./local-dev.md) for the longer setup walk-through and
[v1-scope.md](./v1-scope.md) for what's intentionally NOT in dev today.
