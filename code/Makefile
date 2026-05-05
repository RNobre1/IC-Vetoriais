.PHONY: help up down logs smoke clean test test-unit test-integration lint fmt deps

help:  ## Lista os alvos do Makefile
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

deps:  ## Cria venv local e instala dependências pinadas
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

up:  ## Sobe os 3 SGBDs em background (pgvector + qdrant + weaviate)
	docker compose up -d

down:  ## Derruba os 3 SGBDs (preserva volumes)
	docker compose down

logs:  ## Acompanha logs dos 3 sistemas
	docker compose logs -f

smoke:  ## Smoke test integrado (requer 'make up')
	pytest tests/integration/test_smoke.py -v

test: test-unit  ## Alvo padrão (= test-unit)

test-unit:  ## Testes unitários (sem Docker)
	pytest tests/unit -v

test-integration:  ## Testes de integração (requer 'make up')
	pytest tests/integration -v

lint:  ## Lint via ruff (check + format)
	ruff check .
	ruff format --check .

fmt:  ## Aplica formatação ruff
	ruff format .

clean:  ## Remove containers, volumes Docker e caches Python
	docker compose down -v
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
