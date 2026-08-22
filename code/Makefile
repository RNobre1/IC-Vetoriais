.PHONY: help up down logs smoke clean test test-unit test-integration lint fmt deps ui-up ui-down ui-logs seed bench-A bench-B bench-C-dryrun reset-medicao

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

reset-medicao:  ## DESTRUTIVO: zera volumes e reinicia os 3 SGBDs (linha de base limpa)
	@echo "Isto APAGA os volumes dos 3 SGBDs (coleções de execuções anteriores)."
	@echo "Os JSONs de code/results/ não são tocados. Ctrl-C em 5s para abortar."
	@sleep 5
	$(COMPOSE) down -v
	$(COMPOSE) up -d
	@echo "Aguardando healthcheck dos 3 serviços..."
	@for i in $$(seq 1 60); do \
		n=$$($(COMPOSE) ps --format '{{.Health}}' | grep -c healthy); \
		[ "$$n" = "3" ] && echo "3/3 healthy" && exit 0; \
		sleep 2; \
	done; echo "ERRO: nem todos ficaram healthy" >&2; exit 1

smoke:  ## Smoke test integrado (requer 'make up')
	$(PYTEST) tests/integration/test_smoke.py -v

test: test-unit  ## Alvo padrão (= test-unit)

test-unit:  ## Testes unitários (sem Docker)
	$(PYTEST) tests/unit -v

test-integration:  ## Testes de integração (requer 'make up')
	$(PYTEST) tests/integration -v

# Defaults sobrescrevíveis na linha de comando (ex.: make bench-A N=200 SYS=pgvector).
# `?=` evita a pegadinha de $(or ...) tratar vírgulas de listas como argumentos.
N      ?= 10000
Q      ?= 1000
K      ?= 10
EF     ?= 16,32,64,128,256
WARMUP ?= 50
SYS    ?= pgvector,qdrant,weaviate
SEL    ?= 0.01,0.1,0.5,1.0

seed:  ## Semeia N embeddings nos SGBDs sem benchmark (requer 'make up'). Vars: N SYS
	$(PYTHON) -m benchmarks.run_seed --n $(N) --sistemas $(SYS)

bench-A:  ## Cenário A — busca pura (requer 'make up'). Vars: N Q K EF WARMUP SYS
	$(PYTHON) -m benchmarks.run_cenario_a \
		--n $(N) --queries $(Q) --k $(K) \
		--ef-search $(EF) --warmup $(WARMUP) --sistemas $(SYS)

bench-B:  ## Cenário B — busca com filtro (requer 'make up'). Vars: N Q K EF WARMUP SYS SEL EQ
	$(PYTHON) -m benchmarks.run_cenario_b \
		--n $(N) --queries $(Q) --k $(K) \
		--ef-search $(EF) --warmup $(WARMUP) --sistemas $(SYS) \
		--seletividades $(SEL) $(if $(EQ),--equalizado,)

bench-C-dryrun:  ## Cenário C — esqueleto: imprime o plano de carga (Etapa 4), não roda
	$(PYTHON) -c "from benchmarks.cenario_c import ConfigC, intervalo_entre_insercoes as iv; \
c=ConfigC(); print('Cenário C (esqueleto — execução real na Etapa 4)'); \
print('n_base=%d duracao_s=%d sistemas=%s' % (c.n_base, c.duracao_s, c.sistemas)); \
[print('  taxa=%4d ins/s -> intervalo=%s s' % (t, iv(t))) for t in c.taxas_insercao]"

lint:  ## Lint via ruff (check + format)
	$(RUFF) check .
	$(RUFF) format --check .

fmt:  ## Aplica formatação ruff
	$(RUFF) format .

clean:  ## Remove containers, volumes Docker e caches Python
	docker compose down -v
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
