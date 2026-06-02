# Messor — Security & Secrets

> *Status: v1 · Owner: Julián de la Rosa · Last updated: 2026-06-01*

## 0. ⚠️ Immediate action required

`apps/scraper/env.yaml` currently contains **plaintext production-looking
credentials** committed to the repository:

| Secret | Status |
|---|---|
| `digitalocean.access_id` / `access_key` / `secret_key` | Must rotate |
| `digitalocean.access_token` | Must rotate |
| `strapi_cms.key_token` / `strapi_cms.token` | Must rotate |
| `platform_api.key_token` / `platform_api.token` | Must rotate |
| `openai.api_key` | Must rotate |
| `rabbitmq.username` / `password` | Must rotate if `guest/guest` is reused anywhere real |

**Action plan:**

1. **Rotate every key above** in their respective providers — assume they're
   compromised since the repo is public/hosted on GitHub.
2. **Remove them from history** with `git filter-repo` (or BFG) — a regular
   `git rm` is not enough; old commits keep the secrets.
3. **Replace `env.yaml` with a sanitized template** (`env.example.yaml`) and
   add the real file to `.gitignore`.
4. **Inject real values via env vars** at container start (see below).
5. **Add a pre-commit hook** (`gitleaks` or `detect-secrets`) to block future
   leaks.

## 1. Secrets handling — target model

```text
                 ┌──────────────────────────────────┐
                 │ Secret store                     │
                 │ (DO App env / Doppler / 1Pass)   │
                 └──────────────┬───────────────────┘
                                │  injected at boot
                                ▼
                  ┌──────────────────────────┐
                  │ Container env vars       │
                  │ DO_SPACES_KEY=…          │
                  │ PLATFORM_API_TOKEN=…     │
                  │ RABBITMQ_URL=amqps://…   │
                  └──────────────┬───────────┘
                                 │  read at startup
                                 ▼
              env.yaml (non-secret defaults & topology)
                                 │
                                 ▼
                          Messor process
```

The YAML stays in git for **topology** (bucket names, exchange names, ports);
secrets come from the environment only.

## 2. Recommended tooling

| Concern | Tool |
|---|---|
| Local dev secrets | `.env` (gitignored) + `direnv` |
| Production secret store | DO App Platform env vars, Doppler, or 1Password CLI |
| Secret scanning (pre-commit) | `gitleaks` or `pre-commit/detect-secrets` |
| Secret scanning (CI) | GitHub secret scanning + `gitleaks-action` |
| Container runtime | Inject via env, never bake into image |
| History cleanup | `git filter-repo --replace-text` |

## 3. Allowed-host & content controls

- **Outlet allowlist.** Messor must only scrape outlets that exist in the
  platform's `news-outlets` registry. Reject ad-hoc URLs in production.
- **Language allowlist.** Only languages in `articles.supported_languages`
  are persisted. Drop the rest at the parser boundary.
- **Robot etiquette.** Set a clearly identifying User-Agent
  (`InkPill Mozilla/...` today) and honor `robots.txt` per outlet. Roadmap:
  per-outlet crawl-delay enforcement.
- **PII.** Articles are public content; do not extract or store reader
  identifiers in the scraper service.

## 4. Network posture (production on DigitalOcean)

| Surface | Exposure | Notes |
|---|---|---|
| FastAPI `/scrape`, `/status` | Internal VPC only | Front with auth proxy or platform BFF |
| RabbitMQ | AMQPS, password auth, dedicated vhost | Move off `guest/guest` |
| DO Spaces | IAM-style scoped key per bucket | Least-privilege: `messor` write, no delete on history |
| Outbound HTTP to outlets | Open egress | Optionally route through HTTP proxy for logging |

## 5. Authentication of downstream calls

- Platform API: bearer token in `Authorization: Bearer {token}`, token in env
  var, rotated quarterly.
- Strapi (legacy): same pattern; remove once Laravel platform replaces Strapi.
- DO Spaces: signature v4 via boto/`DigitalOceanSpacesHandler`.
- RabbitMQ: username/password over TLS (AMQPS).

## 6. Audit & response

- All scraping sessions write a JSON artifact under `data/scrapes/` and to DO
  Spaces; keep ≥ 90 days for audit.
- Log shipping target should support replay (Better Stack / Axiom / Datadog).
- Incident playbook: see [operations.md](./operations.md) §7.

## 7. Compliance posture

- No reader PII processed in this service → out of scope for GDPR processor
  duties at this layer.
- Republished snippets must respect each outlet's terms-of-use; track outlet
  licensing in the platform registry, not here.

## 8. Checklist before going to production

- [ ] All secrets rotated and moved to env vars
- [ ] `env.yaml` sanitized; real config injected at runtime
- [ ] Pre-commit secret scanning installed in repo
- [ ] CI secret scanning enabled
- [ ] Dedicated RabbitMQ user with vhost-scoped permissions
- [ ] DO Spaces key scoped to the `inkbytes` bucket only
- [ ] FastAPI not exposed to public internet
- [ ] Outlet allowlist enforced at `OutletService` level
- [ ] Log shipper configured and verified
- [ ] Incident contact + on-call defined
