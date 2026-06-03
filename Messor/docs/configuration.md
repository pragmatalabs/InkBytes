# Messor — Configuration Reference

> *Status: v1 · Source of truth: `apps/scraper/env.yaml` · Last updated: 2026-06-01*

Messor reads a single YAML config file at startup. Production layers env-var
overrides on top — **never** put secrets directly in the YAML.

## 1. File location

| Environment | Path | Notes |
|---|---|---|
| Dev | `apps/scraper/env.yaml` | Local YAML, no secrets |
| Docker | `/app/env.yaml` (mounted) | YAML + env-var overrides |
| DO Production | `/app/env.yaml` + DO env vars | Secrets injected at runtime |

CLI usage:

```bash
python main.py                         # uses ./env.yaml
python main.py path/to/env.yaml        # explicit path
python main.py --schedule              # scheduled mode (Docker)
```

## 2. Top-level sections

| Section | Purpose |
|---|---|
| `application` | App identity, threading, CLI verbs |
| `fast_api` | Embedded API server settings |
| `logging` | Log level, destinations, RabbitMQ exchange |
| `scraper` | Extraction policy (min words, timestamps) |
| `storage` | Local staging paths, offline outlets file |
| `digitalocean` | Spaces (S3) credentials and bucket layout |
| `strapi_cms` / `platform_api` | Downstream REST targets |
| `articles` | Supported languages |
| `scraping` | Schedule, user-agents, HTTP headers |
| `rabbitmq` | Broker connection + queue/exchange names |
| `openai` | Optional LLM key (downstream only) |
| `tinydb` | Local document DB tuning |

## 3. Field-by-field

### 3.1 `application`

| Field | Type | Default | Description |
|---|---|---|---|
| `mode` | str | `development` | `development` / `production`; affects TinyDB slicing |
| `name` | str | `Messor` | Display name |
| `version` | str | `1.0` | Semantic version |
| `max_threads` | int | `10` | Upper bound for ThreadPoolExecutor (auto-clamped to CPU) |
| `uuid_prefix` | str | `IKPGRB` | Prefix for session UUIDs |
| `time_zone` | str | `America/New_York` | Schedule reference |
| `container_name` | str | `messor` | Docker container identifier |
| `api_url` | str | `http://localhost:8080/api` | Platform API base |
| `command_line.mode_arguments` | list | `[SCRAPE, MOVE, EXIT, CLEAN]` | Allowed CLI verbs |

### 3.2 `fast_api`

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `True` | Toggle embedded API |
| `server_args.host` | str | `localhost` | Bind host (use `0.0.0.0` in Docker) |
| `server_args.port` | int | `8050` | Bind port |
| `server_args.app` | str | `api.main:app` | Uvicorn target |
| `server_args.log_level` | str | `info` | Uvicorn log level |

### 3.3 `logging`

| Field | Type | Default | Description |
|---|---|---|---|
| `level` / `log_level` | str | `INFO` | Logger level |
| `logger_name` | str | `messor` | Root logger name |
| `folder` / `file_name` | str | `logs` / `messor.log` | File destination |
| `destinations` | list | `[console, file, rabbit]` | Active sinks |
| `exchange_name` | str | `messor.logs` | RabbitMQ log exchange |

### 3.4 `scraper`

| Field | Type | Default | Description |
|---|---|---|---|
| `min_word_count` | int | `40` | Drop articles below this length |
| `timestamp` | int (min) | `2880` | Reject articles older than N minutes |

### 3.5 `storage`

| Field | Description |
|---|---|
| `data_folder_path` | Root for staged data |
| `file` | TinyDB articles index |
| `staging.local.scraping` | Per-cycle scrape output dir |
| `staging.local.history` | Archived scrape outputs |
| `staging.local.clusters_path` | Cluster artifacts (downstream) |
| `offline.local.outlets` | Fallback outlets file (when platform API unreachable) |
| `offline.local.queue` | Local JSON spillover when RabbitMQ unreachable |

### 3.6 `digitalocean`

| Field | Description |
|---|---|
| `access_id` / `access_key` / `secret_key` | Spaces credentials (**use env vars in prod**) |
| `access_token` | DO API token (**env var only**) |
| `region_name` | e.g. `nyc3` |
| `endpoint_url` | e.g. `https://nyc3.digitaloceanspaces.com` |
| `spaces.buckets.main.name` | Bucket name (e.g. `inkbytes`) |
| `spaces.buckets.main.folders` | Per-domain prefixes (`messor`, `messor/logs`, `data`) |

### 3.7 `rabbitmq`

| Field | Description |
|---|---|
| `host` / `port` / `virtual_host` | Broker connection |
| `ssl.enabled` | Use AMQPS |
| `heartbeat` | Heartbeat seconds |
| `connection_attempts` | Retry count |
| `exchanges.scraping.name` | Article event exchange (`messor`) |
| `exchanges.logging.name` | Log fan-out (`messor.logs`) |
| `queues.articles_scraped` | Output queue consumed by Entopics |
| `queues.topics_extracted` | Input queue from Entopics |
| `username` / `password` | Broker creds (**env var only**) |

### 3.8 `scraping`

| Field | Description |
|---|---|
| `save_mode` | `send_to_api` / `local_only` / `send_to_api_and_local` |
| `schedule_interval_minutes` | Loop interval in scheduled mode (default 60) |
| `agent.default` | Default User-Agent string |
| `headers.default` | Default HTTP headers per request |

### 3.9 `articles`

| Field | Description |
|---|---|
| `supported_languages` | Whitelist (`en`, `es`, `fr`, `de`, `pt`) |

### 3.10 `tinydb`

Slicing parameters; in `production` mode, both are `-1` (no slicing).

## 4. Environment variable overrides

Implemented today: `MESSOR_API_BASE_URL` overrides
`platform_api.base_url`. Roadmap: full layered config via
`pydantic-settings` so every secret can be set as `MESSOR__SECTION__KEY=...`.

**Recommended env-var mapping (production):**

| Env var | Maps to |
|---|---|
| `MESSOR_API_BASE_URL` | `platform_api.base_url` |
| `DO_SPACES_KEY` | `digitalocean.access_id` |
| `DO_SPACES_SECRET` | `digitalocean.secret_key` |
| `DO_API_TOKEN` | `digitalocean.access_token` |
| `RABBITMQ_URL` | `rabbitmq.host` + creds (full URI) |
| `PLATFORM_API_TOKEN` | `platform_api.token` |
| `OPENAI_API_KEY` | `openai.api_key` |

## 5. Validation at boot

Required: presence of `application`, `storage.staging.local.scraping`,
`rabbitmq.host` (if logging destination includes `rabbit`), and
`digitalocean.endpoint_url`. Add a `Config.validate()` step on the roadmap to
fail fast on missing fields.

## 6. Example: minimal dev config

```yaml
application:
  mode: development
  name: Messor
  max_threads: 4
fast_api:
  enabled: true
  server_args: { host: 127.0.0.1, port: 8050, app: api.main:app, log_level: info }
logging:
  level: INFO
  destinations: [console, file]
  folder: logs
  file_name: messor.log
scraper:
  min_word_count: 40
  timestamp: 2880
storage:
  data_folder_path: data/
  file: data/articles.db.json
  staging:
    local:
      scraping: data/scrapes/
      history:  data/history/
articles:
  supported_languages: [en, es]
scraping:
  save_mode: local_only
  schedule_interval_minutes: 60
```

## 7. See also

- Security & secrets: [security.md](./security.md)
- Operations: [operations.md](./operations.md)
- ADR-0002 RabbitMQ events: [adr/0002-rabbitmq-events.md](./adr/0002-rabbitmq-events.md)
