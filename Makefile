SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE_DEV  = docker compose -f orchestrator/docker-compose.dev.yaml
COMPOSE_PROD = docker compose -f infra/docker-compose.prod.yml --env-file infra/.env
# ── Hostinger VPS ─────────────────────────────────────────────────────────────
DEPLOY_USER  ?= root
DEPLOY_HOST  ?= 82.112.250.139
DEPLOY_KEY   ?= ~/.ssh/galvanic_id
DEPLOY_PATH  ?= /docker/inkbytes

# ── DigitalOcean pragmata-001 ─────────────────────────────────────────────────
DEPLOY_HOST_DO   ?= 67.205.136.61
DEPLOY_USER_DO   ?= root
DEPLOY_KEY_DO    ?= ~/.ssh/id_rsa
DEPLOY_PATH_DO   ?= /opt/inkbytes

# ── Local development ─────────────────────────────────────────────────────────
infra: ## Start local infra only (Postgres + RabbitMQ + MinIO)
	$(COMPOSE_DEV) up -d postgres rabbitmq minio minio-bootstrap

infra-full: ## Start full local dev stack (includes Messor + Curator + Reader)
	$(COMPOSE_DEV) --profile full up -d

cycle: ## Start continuous pipeline (native Python: Messor --schedule + Curator --consume)
	bash orchestrator/scripts/cycle.sh start

cycle-stop: ## Stop continuous pipeline
	bash orchestrator/scripts/cycle.sh stop

cycle-status: ## Check pipeline status
	bash orchestrator/scripts/cycle.sh status

cycle-logs: ## Tail pipeline logs
	bash orchestrator/scripts/cycle.sh logs

infra-down: ## Stop local infra (keep volumes)
	$(COMPOSE_DEV) down

infra-nuke: ## Stop local infra AND delete volumes
	bash orchestrator/scripts/down.sh --nuke

# ── Production (on-host) ──────────────────────────────────────────────────────
prod: ## Start prod stack locally (requires infra/.env)
	$(COMPOSE_PROD) up -d

prod-ps: ## Show prod service status
	$(COMPOSE_PROD) ps

prod-logs: ## Follow all prod logs
	$(COMPOSE_PROD) logs -f

prod-logs-curator: ## Follow Curator logs
	$(COMPOSE_PROD) logs -f inkbytes-curator-api inkbytes-curator-worker

prod-down: ## Stop prod stack
	$(COMPOSE_PROD) down

# ── Deploy ────────────────────────────────────────────────────────────────────
deploy: deploy-hostinger ## Alias: deploy to Hostinger (default)

deploy-hostinger: ## Deploy to Hostinger VPS (galvanic.cloud / /docker/inkbytes)
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST) \
	  "cd $(DEPLOY_PATH) && git pull origin master && bash infra/deploy.sh"

deploy-do: ## Deploy to DigitalOcean pragmata-001 (inkbytes.org / /opt/inkbytes)
	ssh -i $(DEPLOY_KEY_DO) -t $(DEPLOY_USER_DO)@$(DEPLOY_HOST_DO) \
	  "cd $(DEPLOY_PATH_DO) && git pull origin master && bash infra/deploy.sh"

deploy-all: ## Deploy to BOTH servers in sequence
	$(MAKE) deploy-hostinger
	$(MAKE) deploy-do

deploy-build: ## Deploy + rebuild images on Hostinger
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST) "cd $(DEPLOY_PATH) && git pull origin master && bash infra/deploy.sh --build"

deploy-build-do: ## Deploy + rebuild images on DigitalOcean
	ssh -i $(DEPLOY_KEY_DO) -t $(DEPLOY_USER_DO)@$(DEPLOY_HOST_DO) "cd $(DEPLOY_PATH_DO) && git pull origin master && bash infra/deploy.sh --build"

# ── Maintenance ───────────────────────────────────────────────────────────────
migrate: ## Run Backoffice migrations (prod)
	ssh -i $(DEPLOY_KEY) $(DEPLOY_USER)@$(DEPLOY_HOST) "docker exec inkbytes-backoffice php artisan migrate --force"

migrate-status: ## Show migration status (prod)
	ssh -i $(DEPLOY_KEY) $(DEPLOY_USER)@$(DEPLOY_HOST) "docker exec inkbytes-backoffice php artisan migrate:status"

seed: ## Run Backoffice seeders (prod — caution)
	ssh -i $(DEPLOY_KEY) $(DEPLOY_USER)@$(DEPLOY_HOST) "docker exec inkbytes-backoffice php artisan db:seed --force"

backup: ## Backup Postgres DB to /var/backups/inkbytes
	bash scripts/backup.sh

shell-php: ## Open a shell in the Backoffice container
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST) "docker exec -it inkbytes-backoffice bash"

shell-db: ## Open psql in the Postgres container (remote)
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST) "docker exec -it inkbytes-postgres psql -U inkbytes -d inkbytes"

shell-curator: ## Open a shell in the Curator API container (remote)
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST) "docker exec -it inkbytes-curator-api bash"

health: ## Hit live endpoints on both servers
	@echo "── Hostinger (galvanic.cloud) ───────────────────"
	@printf "Reader:    "; curl -sk https://inkbytes.galvanic.cloud/ -o /dev/null -w '%{http_code}\n'
	@printf "Backoffice:"; curl -sk https://admin.inkbytes.galvanic.cloud/ -o /dev/null -w '%{http_code}\n'
	@echo "── DigitalOcean (inkbytes.org) ──────────────────"
	@printf "Reader:    "; curl -sk https://inkbytes.org/ -o /dev/null -w '%{http_code}\n'
	@printf "Backoffice:"; curl -sk https://admin.inkbytes.org/ -o /dev/null -w '%{http_code}\n'

status: ## Show container status + memory on Hostinger
	ssh -i $(DEPLOY_KEY) $(DEPLOY_USER)@$(DEPLOY_HOST) "\
	  docker ps --filter 'name=inkbytes-' --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}' | sort; \
	  echo ''; \
	  docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}' \$$(docker ps --filter 'name=inkbytes-' -q) 2>/dev/null | sort"

status-do: ## Show container status + memory on DigitalOcean
	ssh -i $(DEPLOY_KEY_DO) $(DEPLOY_USER_DO)@$(DEPLOY_HOST_DO) "\
	  docker ps --filter 'name=inkbytes-' --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}' | sort; \
	  echo ''; \
	  docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}' \$$(docker ps --filter 'name=inkbytes-' -q) 2>/dev/null | sort"

shell-do: ## SSH into DigitalOcean server
	ssh -i $(DEPLOY_KEY_DO) -t $(DEPLOY_USER_DO)@$(DEPLOY_HOST_DO)

logs-messor-do: ## Follow Messor logs from DigitalOcean server
	ssh -i $(DEPLOY_KEY_DO) -t $(DEPLOY_USER_DO)@$(DEPLOY_HOST_DO) "docker logs -f --tail 50 inkbytes-messor"

logs-curator-do: ## Follow Curator worker logs from DigitalOcean server
	ssh -i $(DEPLOY_KEY_DO) -t $(DEPLOY_USER_DO)@$(DEPLOY_HOST_DO) "docker logs -f --tail 50 inkbytes-curator-worker"

logs-do: ## Follow ALL service logs from DigitalOcean server (Ctrl-C to quit)
	ssh -i $(DEPLOY_KEY_DO) -t $(DEPLOY_USER_DO)@$(DEPLOY_HOST_DO) \
	  "docker compose -f /opt/inkbytes/infra/docker-compose.prod.yml --env-file /opt/inkbytes/infra/.env logs -f --tail 50"

watch: ## Live stats every 5 s (Ctrl-C to quit)
	watch -n 5 "ssh -i $(DEPLOY_KEY) $(DEPLOY_USER)@$(DEPLOY_HOST) \
	  \"docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}' \$$(docker ps --filter 'name=inkbytes-' -q) 2>/dev/null | sort\""

logs: ## Follow all prod logs from server (Ctrl-C to quit)
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST) \
	  "docker compose -f $(DEPLOY_PATH)/infra/docker-compose.prod.yml --env-file $(DEPLOY_PATH)/infra/.env logs -f --tail 50"

logs-messor: ## Follow Messor logs from server
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST) "docker logs -f --tail 50 inkbytes-messor"

logs-curator: ## Follow Curator worker logs from server
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST) "docker logs -f --tail 50 inkbytes-curator-worker"

logs-backoffice: ## Follow Backoffice logs from server
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST) "docker logs -f --tail 50 inkbytes-backoffice"

shell: ## SSH into server
	ssh -i $(DEPLOY_KEY) -t $(DEPLOY_USER)@$(DEPLOY_HOST)

# ── Network ───────────────────────────────────────────────────────────────────
network: ## Ensure traefik-public network exists (idempotent)
	@docker network inspect traefik-public &>/dev/null || docker network create traefik-public

# ── Compose validation ────────────────────────────────────────────────────────
validate-prod: ## Validate prod compose YAML (requires infra/.env)
	$(COMPOSE_PROD) config --quiet && echo "✓ docker-compose.prod.yml is valid"

# ── Help ──────────────────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-22s\033[0m %s\n",$$1,$$2}'

.PHONY: infra infra-full infra-down infra-nuke cycle cycle-stop cycle-status cycle-logs \
        prod prod-ps prod-logs prod-logs-curator prod-down \
        deploy deploy-build migrate migrate-status seed backup \
        shell-php shell-db shell-curator health network validate-prod help \
        watch logs logs-messor logs-curator logs-backoffice shell \
        deploy-hostinger deploy-do deploy-all deploy-build-do \
        status-do shell-do logs-messor-do logs-curator-do logs-do
