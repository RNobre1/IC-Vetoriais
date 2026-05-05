# Plano da Etapa 2 — Preparação de dados e ambiente

> **Status:** plano definido em 2026-05-05; execução prevista 2026-05-05 → 2026-05-08 (4 dias).
> **Cronograma oficial (docx):** Mar–Abr (Etapa 2 no cronograma Jan–Dez).
> **Cronograma real (CLAUDE.md):** Mai–Jun, comprimido pelo início efetivo do projeto.

## Objetivo
Entregar um ambiente experimental reproduzível com os 3 SGBDs vetoriais, pipeline de embeddings determinístico e scripts de benchmark prontos para a **Etapa 3** (cenários A e B em 100k/500k).

## Decisões metodológicas que governam esta etapa
Cada item da Etapa 2 deve respeitar literalmente estas ADRs. Não revisitar sem motivo técnico forte registrado em nova ADR.

- [[../../vault/decisões/2026-04-28-sistemas-avaliados]] — pgvector + Qdrant + Weaviate
- [[../../vault/decisões/2026-04-28-índice-hnsw-em-todos]] — HNSW nos três
- [[../../vault/decisões/2026-04-28-modelo-embedding-minilm]] — `sentence-transformers/all-MiniLM-L6-v2`, 384 dim, normalizado L2
- [[../../vault/decisões/2026-04-28-dataset-ms-marco]] — subset reproduzível de MS MARCO passages
- [[../../vault/decisões/2026-04-28-tamanhos-100k-500k-1m]] — três escalas; 1M só na Etapa 4
- [[../../vault/decisões/2026-04-28-cenarios-A-B-C]] — A pura, B com filtros, C carga mista RAG

## Arquitetura proposta

### Stack
- Python 3.11+
- Docker Compose (3 serviços principais + extras de teste)
- Pacotes: `sentence-transformers`, `psycopg[binary,pool]` (com `pgvector`), `qdrant-client`, `weaviate-client`, `faiss-cpu` (ground truth), `pytest`, `httpx`, `numpy`, `python-dotenv`
- Comandos uniformes via `Makefile`
- Reprodutibilidade: versões **pinadas** em `requirements.txt` (sem ranges)

### Layout em `code/`
```
code/
├── docker-compose.yml          # 3 SGBDs + healthchecks + volumes
├── pyproject.toml              # metadados do projeto
├── requirements.txt            # versões pinadas
├── Makefile                    # comandos uniformes
├── README.md                   # como rodar (em PT-BR)
├── .env.example                # variáveis de configuração
├── pipeline/
│   ├── __init__.py
│   ├── ms_marco_loader.py      # download + sampling determinístico
│   └── embeddings.py           # geração + cache local em data/
├── seeders/
│   ├── __init__.py
│   ├── pgvector_seeder.py
│   ├── qdrant_seeder.py
│   └── weaviate_seeder.py
├── ground_truth/
│   ├── __init__.py
│   └── exact_search.py         # FAISS IndexFlatIP para recall@K
├── benchmarks/
│   ├── __init__.py
│   ├── cenario_a.py            # busca pura
│   ├── cenario_b.py            # busca com filtros
│   └── cenario_c.py            # esqueleto p/ Etapa 4
├── lib/
│   ├── __init__.py
│   ├── metrics.py              # p50/p95/p99, QPS, recall@K
│   └── reporting.py            # JSON normalizado + (opcional) plot Pareto
└── tests/
    ├── conftest.py
    ├── unit/                   # rápidos, sem Docker
    └── integration/            # contra Docker rodando
```

### Reprodutibilidade
- Versões pinadas em `requirements.txt` e tags Docker imutáveis (não usar `:latest`).
- Seeds fixos para sampling, particionamento, shuffle.
- Embeddings cached em `data/embeddings/<dataset>-<model>-<version>.npy` com hash determinístico.
- Subsets de MS MARCO determinísticos (ordenação por `passage_id`, slice top-N).
- Hardware documentado em cada nota de [[../../vault/experimentos/]].

## Cronograma diário (4 dias)

### Dia 1 — 2026-05-05 ✅ CONCLUÍDO
**Foco: esqueleto de `code/`, docker-compose dos 3 sistemas, smoke test em TDD e CI mínimo no ar.**

Entregáveis:
- [x] Esqueleto do projeto Python em `code/`:
  - `pyproject.toml` (com config de `ruff` para lint+format e `pytest` markers)
  - `requirements.txt` com versões pinadas + `requirements.lock` (transitivos resolvidos)
  - `Makefile` (alvos: `up`, `down`, `smoke`, `test`, `test-unit`, `test-integration`, `lint`, `fmt`, `clean`, `deps`, `logs`, `help`)
  - `README.md` (esqueleto em PT-BR com troubleshooting)
  - `.env.example`
- [x] `code/docker-compose.yml` com:
  - `postgres-pgvector` (`pgvector/pgvector:pg16`)
  - `qdrant` (`qdrant/qdrant:v1.12.0`)
  - `weaviate` (`semitechnologies/weaviate:1.27.0`)
  - Healthchecks (TCP/HTTP/`pg_isready`) com `start_period` e retries adequados
  - Named volumes gerenciados pelo Docker
  - Porta gRPC 50051 do Weaviate exposta (necessária para o cliente v4)
- [x] **Smoke test em TDD** (escrito antes do `docker compose up`):
  - `tests/integration/test_smoke.py` — 6 cenários cobrindo conexão + CREATE + INSERT + SEARCH nos 3 sistemas
  - `tests/unit/test_basic.py` — mantém o pipeline de CI vivo
  - **Resultado:** 6/6 integrados verde, 2/2 unitários verde após `docker compose up -d --wait`.
- [x] **CI mínimo no GitHub Actions** (`.github/workflows/test.yml`):
  - Lint via `ruff check` + `ruff format --check`
  - Testes unitários via `pytest tests/unit`
  - Cache de pip
  - Executa em push/PR para `main`
- [x] **ADR**: [[../../vault/decisões/2026-05-05-versoes-imagens-docker]] (versões fixadas).
- [x] **Lição**: [[../../vault/lições/2026-05-05-armadilhas-dia-1-etapa-2]] (3 armadilhas corrigidas: httpx vs weaviate, psycopg sem wheel py3.14, gRPC do Weaviate).

**Estado de infraestrutura ao final do Dia 1:** containers `ic-pgvector`, `ic-qdrant`, `ic-weaviate` de pé e healthy; venv `code/.venv` instalado; `code/.env` aplicado.

### Dia 2 — 2026-05-06
**Foco: pipeline de embeddings + seeders dos 3 sistemas.**

Entregáveis:
- [ ] `pipeline/ms_marco_loader.py`:
  - Baixa `collection.tsv` de MS MARCO em `data/ms_marco/` (gitignored)
  - Valida MD5 do download
  - Sampling determinístico de 100k, 500k, 1M
- [ ] `tests/unit/test_loader.py`: determinismo, tamanhos, IDs distintos, robustez a re-execução
- [ ] `pipeline/embeddings.py`:
  - Gera embeddings em batch (CPU baseline, GPU opcional)
  - Normaliza L2
  - Cache em `data/embeddings/`
- [ ] `tests/unit/test_embeddings.py`: shape (N×384), norma ≈ 1.0, cache hit, reprodutibilidade entre execuções
- [ ] `seeders/pgvector_seeder.py`, `seeders/qdrant_seeder.py`, `seeders/weaviate_seeder.py`:
  - Cada um expõe `seed(vectors, metadata, *, M, efConstruction)`
  - Cria coleção/tabela com índice HNSW e parâmetros uniformes
- [ ] `tests/integration/test_seeders.py`: para cada sistema, seed 1k vetores, conta total, busca 1 vetor conhecido (sanity)
- [ ] Início do download de MS MARCO em background (~3 GB)

### Dia 3 — 2026-05-07
**Foco: ground truth + Cenário A + Cenário B.**

Entregáveis:
- [ ] `ground_truth/exact_search.py`:
  - FAISS `IndexFlatIP` (produto interno, vetores já normalizados)
  - Calcula top-K exato para um conjunto de queries; salva em `data/ground_truth/`
- [ ] `tests/unit/test_ground_truth.py`: recall vs. ele mesmo = 1.0; consistência entre execuções
- [ ] `lib/metrics.py`: p50/p95/p99 (via `numpy.percentile`), QPS, recall@K
- [ ] `tests/unit/test_metrics.py`: cálculo de percentis em distribuições conhecidas, recall em casos de canto
- [ ] `lib/reporting.py`: JSON normalizado em `code/results/`
- [ ] `benchmarks/cenario_a.py`:
  - Carga: 1000 queries de teste do MS MARCO (não usadas no seed)
  - Varre `efSearch ∈ {16, 32, 64, 128, 256}`
  - Mede latência p50/p95/p99, QPS, recall@10 por sistema, por valor de efSearch
- [ ] `benchmarks/cenario_b.py`:
  - Adiciona predicado de seletividade variável (1%, 10%, 50%, 100%)
  - Sintetiza coluna `categoria` no metadata durante o seed
  - Mede mesmas métricas

### Dia 4 — 2026-05-08
**Foco: Cenário C esqueleto, ferramental, README.**

Entregáveis:
- [ ] `benchmarks/cenario_c.py`:
  - **Esqueleto apenas** — não rodar carga real (1M fica para Etapa 4)
  - Estrutura: produtor concorrente de inserções + consumidor de buscas
  - Mede impacto de taxa de inserção (0, 10, 100, 1000 ins/s) em latência p99 de leitura
- [ ] `Makefile` estendido com `seed`, `bench-A`, `bench-B`, `bench-C-dryrun` (alvos básicos `up`, `down`, `smoke`, `test*`, `lint`, `fmt`, `clean` já vieram do Dia 1)
- [ ] `code/README.md` finalizado em PT-BR com:
  - Pré-requisitos (Docker ≥ 24, Python 3.11+, ~8 GB livres em disco, ~12 GB RAM em pico)
  - Comandos (mesmos do Makefile)
  - Troubleshooting (porta ocupada, container saudável mas Python falha conectar, etc.)
- [ ] CI estendido (decisão pendente — avaliar Dia 4): ampliar workflow para rodar testes de integração com `services:` do GitHub Actions. Custo: workflow mais frágil, runners gratuitos limitados. Recomendação atual: **manter integração local**, só ampliar se o orientador requisitar.
- [ ] Smoke completo de validação: `make up && make seed N=10000 && make bench-A` produz JSON em `code/results/`

## Definição de "pronto" para a Etapa 2
1. `make up` sobe os 3 containers em ≤ 60 s; `make smoke` passa.
2. `make seed N=100000` carrega 100k embeddings em cada um dos 3 sistemas em ≤ 30 min (notebook-alvo).
3. `make bench-A` produz `code/results/cenario_a_<sistema>_<N>_<timestamp>.json` para cada um dos 3 sistemas.
4. Cobertura de testes:
   - Unitários: ≥ 80 % de linhas em `pipeline/`, `lib/`, `ground_truth/`
   - Integração: ≥ 1 teste por seeder, ≥ 1 teste por cenário (A e B)
5. `code/README.md` permite a um terceiro sem contexto reproduzir `make up && make smoke` em ≤ 15 min.
6. Toda decisão técnica nova surgida durante a execução vira ADR em `vault/decisões/`.

## Riscos & mitigações
1. **Hardware apertado em 1M.** 16 GB RAM com 3 SGBDs simultâneos é justo. *Mitigação:* na Etapa 2 não rodar 1M; deixar a infra preparada e validar isoladamente um sistema por vez quando chegar a Etapa 4.
2. **Download do MS MARCO (~3 GB).** Pode falhar em conexões instáveis. *Mitigação:* iniciar cedo no Dia 2; validar MD5; permitir retomada incremental.
3. **Drivers Python (psycopg, qdrant-client, weaviate-client).** Versões podem quebrar entre minor releases. *Mitigação:* pinar versões testadas; documentar em `requirements.txt`.
4. **Tentação de pular TDD para "ganhar tempo".** Bugs silenciosos em scripts de benchmark contaminam todos os experimentos da Etapa 3. *Mitigação:* TDD inegociável (Regra 2 do CLAUDE.md). Cada peça de código nasce com teste.
5. **Cluster HPC do IEG não confirmado.** Se viabilizar, parte da Etapa 2 precisará revisão. *Mitigação:* manter scripts portáveis (sem dependência forte do `docker compose` específico do notebook).

## Pendências decisórias durante a execução
A registrar como ADR no momento em que a decisão for tomada:

- Versões exatas das imagens Docker (Dia 1).
- Estratégia de chunking (passage = parágrafo do MS MARCO sem chunking adicional, ou re-chunking?). Default: usar passage como vem.
- Ampliação do CI para integração via `services:` do GitHub Actions (avaliação no Dia 4).

## Backlinks
- [[../../vault/decisões/2026-04-28-sistemas-avaliados]]
- [[../../vault/decisões/2026-04-28-cenarios-A-B-C]]
- [[../../vault/decisões/2026-04-28-modelo-embedding-minilm]]
- [[../../vault/lições/2026-05-05-rigor-citacoes-abnt]]
- [[../../vault/referência/metodologia-benchmarking-ann]]
