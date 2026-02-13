# ── RPA Automation Engine — Docker Commands ──

.PHONY: help dev prod down logs build clean migrate seed test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Development ──

dev: ## Start development stack
	docker compose up -d
	@echo "\n✅ Dev stack running:"
	@echo "   Frontend:  http://localhost:3000"
	@echo "   Backend:   http://localhost:8000"
	@echo "   API docs:  http://localhost:8000/docs"

dev-build: ## Rebuild and start development stack
	docker compose up -d --build

dev-logs: ## Tail development logs
	docker compose logs -f --tail=100

# ── Production ──

prod: ## Start production stack (requires .env)
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-build: ## Build and start production stack
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

prod-logs: ## Tail production logs
	docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=100

prod-down: ## Stop production stack
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# ── Common ──

down: ## Stop all services
	docker compose down

build: ## Build all images
	docker compose build

clean: ## Stop and remove volumes (⚠️ destroys data)
	docker compose down -v --remove-orphans
	docker image prune -f

# ── Database ──

migrate: ## Run database migrations
	docker compose exec backend alembic upgrade head

seed: ## Seed database with sample data
	docker compose exec backend python -m scripts.seed

db-shell: ## Open PostgreSQL shell
	docker compose exec postgres psql -U rpa_user -d rpa_engine

# ── Testing ──

test-backend: ## Run backend tests
	docker compose exec backend pytest -v

test-frontend: ## Run frontend E2E tests (requires dev stack)
	cd frontend && npx playwright test --project=chromium

# ── Monitoring ──

monitoring: ## Start monitoring stack (Prometheus + Grafana)
	docker compose -f monitoring/docker-compose.monitoring.yml up -d
	@echo "\n📊 Monitoring:"
	@echo "   Prometheus: http://localhost:9090"
	@echo "   Grafana:    http://localhost:3001 (admin/admin)"

monitoring-down: ## Stop monitoring stack
	docker compose -f monitoring/docker-compose.monitoring.yml down
