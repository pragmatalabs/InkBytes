SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE_DEV  = docker compose -f orchestrator/docker-compose.dev.yaml
COMPOSE_PROD = docker compose -f infra/docker-compose.prod.yml --env-file infra/.env
DEPLOY_USER  ?= root
DEPLOY_HOST  ?= pragmata-001

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
deploy: ## Deploy to pragmata-001 via SSH (pull registry images)
	ssh -t $(DEPLOY_USER)@$(DEPLOY_HOST) "cd /opt/inkbytes && bash infra/deploy.sh"

deploy-build: ## Deploy + build images on the server (no registry needed)
	ssh -t $(DEPLOY_USER)@$(DEPLOY_HOST) "cd /opt/inkbytes && bash infra/deploy.sh --build"

# ── Maintenance ───────────────────────────────────────────────────────────────
migrate: ## Run Backoffice migrations (prod)
	docker exec inkbytes-backoffice-fpm php artisan migrate --force

migrate-status: ## Show migration status (prod)
	docker exec inkbytes-backoffice-fpm php artisan migrate:status

seed: ## Run Backoffice seeders (prod — caution)
	docker exec inkbytes-backoffice-fpm php artisan db:seed --force

backup: ## Backup Postgres DB to /var/backups/inkbytes
	bash scripts/backup.sh

shell-php: ## Open a shell in the Backoffice FPM container
	docker exec -it inkbytes-backoffice-fpm bash

shell-db: ## Open psql in the Postgres container
	docker exec -it inkbytes-postgres psql -U inkbytes -d inkbytes

shell-curator: ## Open a shell in the Curator API container
	docker exec -it inkbytes-curator-api bash

health: ## Hit Reader + Curator health endpoints
	@echo "Reader:"; curl -sf https://inkbytes.org/ > /dev/null && echo "OK" || echo "FAIL"
	@echo "Curator:"; curl -sf http://localhost:8060/healthz && echo "" || echo "FAIL (check tunnel)"

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
        shell-php shell-db shell-curator health network validate-prod help
