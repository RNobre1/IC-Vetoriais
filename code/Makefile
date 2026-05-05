.PHONY: help up down logs smoke clean test test-unit test-integration lint fmt deps ui-up ui-down ui-logs

# Compose principal (3 SGBDs) e merge com UI (Verba). Vide:
#   vault/decisões/2026-05-05-isolamento-ui-vs-benchmark.md
COMPOSE      := docker compose
COMPOSE_UI   := docker compose -f docker-compose.yml -f docker-compose.ui.yml

VENV := .venv
# Se o venv existe, usa seus binários; caso contrário, cai pro PATH (necessário pra CI sem venv).
PYTHON := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python)
PIP    := $(if $(wildcard $(VENV)/bin/pip),$(VENV)/bin/pip,pip)
PYTEST := $(if $(wildcard $(VENV)/bin/pytest),$(VENV)/bin/pytest,pytest)
RUFF   := $(if $(wildcard $(VENV)/bin/ruff),$(VENV)/bin/ruff,ruff)

help:  ## Lista os alvos do Makefile
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

deps:  ## Cria venv local e instala dependências pinadas
	python -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

up:  ## Sobe os 3 SGBDs em background (pgvector + qdrant + weaviate)
	$(COMPOSE) up -d

down:  ## Derruba os 3 SGBDs (preserva volumes)
	$(COMPOSE) down

logs:  ## Acompanha logs dos 3 sistemas
	$(COMPOSE) logs -f

ui-up:  ## Sobe Verba (UI do Weaviate) — NÃO rodar durante benchmarks
	$(COMPOSE_UI) up -d verba
	@echo ""
	@echo "Verba disponível em: http://localhost:$${VERBA_PORT:-8000}"
	@echo "Lembrete: derrubar com 'make ui-down' antes de medições."

ui-down:  ## Derruba Verba (preserva os 3 SGBDs)
	$(COMPOSE_UI) stop verba
	$(COMPOSE_UI) rm -f verba

ui-logs:  ## Acompanha logs do Verba
	$(COMPOSE_UI) logs -f verba

smoke:  ## Smoke test integrado (requer 'make up')
	$(PYTEST) tests/integration/test_smoke.py -v

test: test-unit  ## Alvo padrão (= test-unit)

test-unit:  ## Testes unitários (sem Docker)
	$(PYTEST) tests/unit -v

test-integration:  ## Testes de integração (requer 'make up')
	$(PYTEST) tests/integration -v

lint:  ## Lint via ruff (check + format)
	$(RUFF) check .
	$(RUFF) format --check .

fmt:  ## Aplica formatação ruff
	$(RUFF) format .

clean:  ## Remove containers, volumes Docker e caches Python
	docker compose down -v
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
