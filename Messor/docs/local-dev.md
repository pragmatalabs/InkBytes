# Messor — Local Development Quickstart

> *Status: v1 · tested 2026-06-02 · Last updated: 2026-06-02*

This is the fast path to get the harvester running on your laptop in
**local-only mode** — no DigitalOcean, no RabbitMQ, no Platform API.

## 1. Prereqs

- Python 3.10 or 3.11 (3.12 may need lxml wheels rebuilt)
- Working internet (the scraper fetches real news outlets)
- ~200 MB free disk for venv + NLTK data

## 2. One-time setup

```bash
cd /Volumes/Pragmata/Projects/InkBytes/Messor/apps/scraper

# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (now includes the inkbytes shared kernel via
# an editable install — see INK-1)
pip install -r requirements.txt

# NLTK tokenizer data (one-time)
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

## 3. The `inkbytes` package

The shared kernel (`inkbytes.common`, `inkbytes.models`,
`inkbytes.database`) is now a real Python package at
`Messor/packages/inkbytes`. `requirements.txt` installs it editable via
`-e ../../packages/inkbytes`, so no `PYTHONPATH=.` hack is required.

If you ever recreate the workspace from scratch:

```bash
pip install -e Messor/packages/inkbytes
python -c "import inkbytes; print(inkbytes.__path__)"
# → ['.../Messor/packages/inkbytes/inkbytes']
```

The legacy symlinks at `Messor/inkbytes` and
`Messor/apps/scraper/inkbytes` are dead and can be removed:

```bash
rm -f Messor/inkbytes Messor/apps/scraper/inkbytes
```

## 4. Local config

Use the committed `env.local.yaml` (gitignored as a pattern, sample lives in
the repo at `apps/scraper/env.local.yaml` — copy + customise as needed):

```yaml
scraping:
  save_mode: local_only          # no API push, no Spaces
logging:
  destinations: [console]         # no RabbitMQ
fast_api:
  enabled: false
storage:
  offline:
    local:
      outlets:
        file: data/outlets/news_outlets_local.json
```

The starter outlets file `news_outlets_local.json` has 3 sources for quick
loops (CNN lite, BBC News, NPR). Add or trim freely.

## 5. Run

```bash
# One-shot — single cycle, then exit
python main.py env.local.yaml --scrape

# Scheduled (Docker-style production loop, but local)
python main.py env.local.yaml --schedule
```

Successful first cycle drops a session JSON under
`apps/scraper/data/scrapes/<session>.json` and per-outlet logs to the
console.

## 6. What "good" looks like

| Signal | Where | What you want |
|---|---|---|
| Stdout | terminal | `INFO Duplicate filtering stats for <outlet>: Total: N | New: M | Duplicates: K (X.X%)` |
| Staging dir | `data/scrapes/` | one `.json` per outlet per cycle |
| Session file | `scraping_session.json` | written at app root, reflects last run |
| Exit code | shell | `0` on `--scrape` one-shot |

## 7. Known gotchas (from the tune-up)

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: lxml.html.clean module is now a separate project` | Modern lxml split out html cleaner | Bundled in requirements.txt; if missing, `pip install lxml_html_clean` |
| `No module named 'inkbytes.common'` | `inkbytes` package not installed | `pip install -e packages/inkbytes` from repo root |
| `fastapi requires pydantic>=2.9.0` warning | We're on pydantic v1 deliberately | Ignore for v1; `fastapi==0.99.1` is the last v1-compatible release |
| `Error loading punkt` from NLTK | First run, no tokenizer data | `python -c "import nltk; nltk.download('punkt')"` |
| `No articles could be retrieved from <outlet>` | Outlet blocks default UA OR you're behind a corporate proxy | Try another outlet; tune `scraping.headers.default.User-Agent` |
| `Connection refused` to RabbitMQ | You set `destinations: [rabbit]` in local-only | Remove `rabbit` from destinations |
| Pydantic v1 vs v2 deprecation warnings | Requirements pins `pydantic==1.10.14` | Leave alone in v1; migrate in Sprint-2 |

## 8. Iteration loop

```text
edit code  →  python main.py env.local.yaml --scrape  →  inspect data/scrapes/*.json
       └────────────  ctrl-C any time  ──────────────┘
```

No hot-reload, no daemon. The agent loop is short enough that restart is fine.

## 9. When to stop local-only and move on

- You're hitting the same outlets enough to want dedup history → **good.**
- You want to publish to RabbitMQ for Entopics to consume → switch to
  `env.local.yaml` with rabbit destination and a local broker.
- You want to upload artifacts → fill DO Spaces credentials in env vars and
  set `save_mode: send_to_api`.

## 10. See also

- [v1-scope.md](./v1-scope.md) — what we're targeting
- [configuration.md](./configuration.md) — every field explained
- [operations.md](./operations.md) — when this leaves your laptop
