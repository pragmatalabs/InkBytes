# Scraper App (`apps/scraper`)

Legacy Messor Python scraper stack migrated under monorepo `apps/`.

## Run Locally

```bash
cd apps/scraper
python3 main.py env.yaml
```

From repository root you can still use:

```bash
python3 main.py
```

## Key Folders

- `core/` - application orchestrator, config, command processor
- `services/` - scraping, storage, messaging, outlets
- `api/` - FastAPI websocket/status endpoints (legacy)
- `data/` - scraping data and outlet source files
