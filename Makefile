# ═══════════════════════════════════════════════════════════════════════════
# SlotSight — task runner
#
#   make setup    first-time setup (installs deps, wires git hooks)
#   make up       start the full stack in Docker
#   make gates    lint + types + tests, both apps.  Nothing ships without this.
#
# Works on Windows (Git Bash), macOS, and Linux.
# ═══════════════════════════════════════════════════════════════════════════

SHELL := /bin/bash
API   := apps/api
WEB   := apps/web

# Windows venvs put binaries in Scripts/, POSIX in bin/.
VENV_BIN := $(API)/.venv/Scripts
ifeq ($(wildcard $(VENV_BIN)),)
	VENV_BIN := $(API)/.venv/bin
endif

.DEFAULT_GOAL := help
.PHONY: help setup up down logs seed reseed gates lint types test test-golden \
        api web build clean scan verify-hooks

help: ## Show this help
	@echo ""
	@echo "  SlotSight — Neon Palms Casino Resort (all data synthetic)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[33m%-14s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Setup ──────────────────────────────────────────────────────────────────
setup: ## Install dependencies and enable the local git hooks
	@echo "→ wiring git hooks (they are opt-in; a clone does not enable them)"
	git config core.hooksPath .githooks
	@echo "→ installing API dependencies"
	cd $(API) && uv venv && uv pip install -e ".[dev]"
	@echo "→ installing web dependencies"
	cd $(WEB) && pnpm install
	@echo ""
	@echo "  Done. Next:  cp .env.example .env  &&  make up"
	@echo ""

verify-hooks: ## Confirm the local secret-scan hooks are active
	@test "$$(git config --get core.hooksPath)" = ".githooks" \
		&& echo "  ✓ git hooks active" \
		|| (echo "  ✗ git hooks NOT active — run: make setup" && exit 1)

# ── Stack ──────────────────────────────────────────────────────────────────
up: ## Start the full stack in Docker (db + seed + api + web)
	docker compose up --build -d
	@echo ""
	@echo "  web   http://localhost:$${WEB_PORT:-5173}"
	@echo "  api   http://localhost:$${API_PORT:-8000}/docs"
	@echo ""
	@echo "  NOTE: /api/chat needs Entra auth, which does NOT cross from a"
	@echo "        Windows or macOS host into a Linux container. Use 'make dev'"
	@echo "        for a local chat demo. See docs/troubleshooting.md."
	@echo ""

dev: ## Chat-capable local mode: db in Docker, api + web on the host
	@echo "→ starting database only"
	docker compose up -d db
	@echo "→ waiting for database"
	@until docker compose exec -T db pg_isready -U $${POSTGRES_USER:-slotsight} >/dev/null 2>&1; \
		do sleep 1; done
	@echo "→ seeding"
	docker compose run --rm seed
	@echo ""
	@echo "  Database is up. Now run these in two terminals:"
	@echo ""
	@echo "    make api      # http://localhost:8000  (uses your az login)"
	@echo "    make web      # http://localhost:5173"
	@echo ""

down: ## Stop the stack (keeps the database volume)
	docker compose down

clean: ## Stop the stack and DELETE the database volume
	docker compose down -v

logs: ## Tail all service logs
	docker compose logs -f

seed: ## Generate the synthetic floor (skips if already seeded)
	docker compose run --rm seed

reseed: ## Drop and regenerate the synthetic floor
	docker compose run --rm seed slotsight-seed --reset

# ── Gates.  Nothing is "done" until these pass. ────────────────────────────
gates: lint types test ## Run every gate

lint: ## Lint both apps
	cd $(API) && ../../$(VENV_BIN)/ruff check .
	cd $(API) && ../../$(VENV_BIN)/ruff format --check .
	cd $(WEB) && pnpm exec eslint src --max-warnings 0

types: ## Type-check both apps
	cd $(API) && ../../$(VENV_BIN)/mypy src
	cd $(WEB) && pnpm exec tsc --noEmit

test: ## Run every test
	cd $(API) && ../../$(VENV_BIN)/python -m pytest -q
	cd $(WEB) && pnpm exec vitest run

test-golden: ## Run only the four planted-signal tests
	cd $(API) && ../../$(VENV_BIN)/python -m pytest -m golden -v

scan: ## Scan the working tree and full history for secrets
	gitleaks detect --no-git --redact
	gitleaks detect --log-opts=--all --redact

# ── Local (no Docker) ──────────────────────────────────────────────────────
api: ## Run the API on the host (chat works here — uses your az login)
	cd $(API) && POSTGRES_HOST=localhost ../../$(VENV_BIN)/python -m uvicorn slotsight.main:app --reload --port 8000

web: ## Run the Vite dev server (proxies /api to localhost:8000)
	cd $(WEB) && pnpm dev

build: ## Build production artifacts
	cd $(WEB) && pnpm build
	docker compose build
