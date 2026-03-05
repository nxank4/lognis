FPT_PROXY = http://proxy.hcm.fpt.vn:80

.DEFAULT_GOAL := help

COMPOSE = docker compose
BACKEND  = backend
FRONTEND = frontend

# ── Help ──────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  make dev          Start all services with hot-reload"
	@echo "  make dev-proxy    Same as dev, but routes downloads through FPT proxy"
	@echo "  make build        Build all Docker images for production"
	@echo "  make build-proxy  Same as build, but routes downloads through FPT proxy"
	@echo "  make clean        Stop containers and remove volumes"
	@echo "  make reset-modules  Remove the frontend node_modules volume (forces clean reinstall on next dev)"
	@echo "  make logs         Tail logs from all services"
	@echo "  make migrate      Run database initialisation / migrations"
	@echo ""

# ── Dev ───────────────────────────────────────────────────────────────────────
.PHONY: dev
dev:
	$(COMPOSE) up --build

# Dev with FPT proxy (use when direct downloads fail on the local network)
.PHONY: dev-proxy
dev-proxy:
	HTTP_PROXY=$(FPT_PROXY) HTTPS_PROXY=$(FPT_PROXY) $(COMPOSE) up --build

# ── Build ─────────────────────────────────────────────────────────────────────
.PHONY: build
build:
	$(COMPOSE) build

# Build with FPT proxy (use when direct downloads fail on the local network)
.PHONY: build-proxy
build-proxy:
	HTTP_PROXY=$(FPT_PROXY) HTTPS_PROXY=$(FPT_PROXY) $(COMPOSE) build

# ── Clean ─────────────────────────────────────────────────────────────────────
.PHONY: clean
clean:
	$(COMPOSE) down -v --remove-orphans

# Remove only the frontend node_modules volume (after adding/removing packages).
# Leaves postgres_data and redis_data intact.
.PHONY: reset-modules
reset-modules:
	docker volume rm lognis_frontend_node_modules 2>/dev/null || true

# ── Logs ──────────────────────────────────────────────────────────────────────
.PHONY: logs
logs:
	$(COMPOSE) logs -f

# ── Migrate ───────────────────────────────────────────────────────────────────
# The app uses SQLAlchemy Base.metadata.create_all at startup (no Alembic yet).
# This target runs it explicitly as a one-shot job if needed.
.PHONY: migrate
migrate:
	$(COMPOSE) run --rm $(BACKEND) python -c \
		"import asyncio; from app.core.database import init_db; asyncio.run(init_db())"
