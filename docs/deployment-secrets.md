# GitHub Secrets — InkBytes

Set at: **GitHub repo → Settings → Secrets and variables → Actions**

```bash
# Bulk-set with gh CLI (run locally after generating keys):
gh secret set DIGITALOCEAN_ACCESS_TOKEN --body "dop_v1_..."
gh secret set DO_REGISTRY              --body "pragmata"
gh secret set DEPLOY_HOST              --body "<pragmata-001 IP>"
gh secret set DEPLOY_USER              --body "root"
gh secret set DEPLOY_KEY               < ~/.ssh/inkbytes_deploy
```

---

## DigitalOcean

| Secret | Description | Where to get |
|---|---|---|
| `DIGITALOCEAN_ACCESS_TOKEN` | DO API token (read/write — needs registry push) | DO Console → API → Personal Access Tokens |
| `DO_REGISTRY` | Registry slug (`pragmata`) | DO Console → Container Registry |

---

## SSH / Deploy

| Secret | Description |
|---|---|
| `DEPLOY_HOST` | Droplet public IP (e.g. `159.65.x.x`) |
| `DEPLOY_USER` | SSH user (`root`) |
| `DEPLOY_KEY`  | **Private** half of `~/.ssh/inkbytes_deploy` (ed25519) |
| `DEPLOY_PORT` | SSH port (omit → defaults to 22) |

Generate the key pair:
```bash
ssh-keygen -t ed25519 -C "gha-deploy-inkbytes" -f ~/.ssh/inkbytes_deploy -N ""
# Install public key on the droplet:
ssh-copy-id -i ~/.ssh/inkbytes_deploy.pub root@<DROPLET_IP>
# Give GitHub the private key:
gh secret set DEPLOY_KEY < ~/.ssh/inkbytes_deploy
```

---

## App secrets (managed on server via `infra/.env` — NOT as GitHub Secrets)

These live in `/opt/inkbytes/infra/.env` on the droplet (never committed).
Document here for reference:

| Variable | Description |
|---|---|
| `APP_KEY` | Laravel application key — `php artisan key:generate --show` |
| `POSTGRES_PASSWORD` | Postgres password |
| `RABBITMQ_PASS` | RabbitMQ password |
| `MINIO_KEY` / `MINIO_SECRET` | MinIO root credentials |
| `DO_SPACES_KEY` / `DO_SPACES_SECRET` | DigitalOcean Spaces for article archival |
| `ANTHROPIC_API_KEY` | Claude API key |
| `OPENAI_API_KEY` | OpenAI API key (embeddings + optional LLM) |
| `DEEPSEEK_API_KEY` | DeepSeek API key (optional LLM) |
| `INKBYTES_DEMO_PASSWORD` | Reader demo access password |

---

## Repo deploy key (droplet → GitHub, for `git pull`)

The droplet needs read-only access to pull the repo. See `infra/scripts/server-bootstrap.sh` step 5.
The generated public key (`~/.ssh/inkbytes_repo.pub`) must be added to:
**GitHub repo → Settings → Deploy keys** (read-only scope).

---

## Rollback procedure

```bash
# SSH into the droplet
ssh root@<DROPLET_IP>

# Roll back a single service to a known-good SHA
docker pull registry.digitalocean.com/pragmata/inkbytes-curator:<good-sha>
docker tag  registry.digitalocean.com/pragmata/inkbytes-curator:<good-sha> \
            registry.digitalocean.com/pragmata/inkbytes-curator:latest
cd /opt/inkbytes
docker compose -f infra/docker-compose.prod.yml up -d inkbytes-curator-api inkbytes-curator-worker

# Or re-trigger deploy workflow with skip_build=true to redeploy :latest
```
