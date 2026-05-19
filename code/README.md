# IC-Vetoriais — `code/`

Ambiente experimental para a IC **"Comparação de Desempenho de Soluções de Bancos de Dados Vetoriais para Busca Semântica"** (UFOPA/IEG; bolsista: Rafael Nobre; orientador: Prof. Dr. Celson Pantoja Lima).

> **Status:** Etapa 2 **concluída** — ambiente + pipeline de embeddings + ground truth + Cenários A e B completos (em TDD, com smoke real nos 3 SGBDs) + esqueleto do Cenário C. Plano completo em [`../docs/tasks/etapa-2-preparacao-ambiente.md`](../docs/tasks/etapa-2-preparacao-ambiente.md). Decisões metodológicas em [`../vault/decisões/`](../vault/decisões/).
>
> **Snapshot atual de versões dos SGBDs** (vide [`../vault/decisões/2026-05-06-bump-versoes-sgbds.md`](../vault/decisões/2026-05-06-bump-versoes-sgbds.md)):
> - `pgvector/pgvector:0.8.2-pg18-bookworm` (Postgres 18.3 + pgvector 0.8.2)
> - `qdrant/qdrant:v1.17.1`
> - `semitechnologies/weaviate:1.37.2`

## Pré-requisitos

- Docker ≥ 24 (com Docker Compose v2)
- Python 3.11+
- ~8 GB livres em disco (imagens Docker + datasets nas Etapas seguintes)
- ~12 GB de RAM disponível em pico (3 SGBDs simultaneamente)

## Setup

```bash
cd code

# 1. Cria venv e instala dependências pinadas
make deps
source .venv/bin/activate

# 2. Configura variáveis (defaults já funcionam)
cp .env.example .env

# 3. Sobe os 3 SGBDs
make up

# 4. Smoke test (valida conexão básica nos 3 sistemas)
make smoke
```

**Reprodução mínima (≤ 15 min, terceiro sem contexto):** `cd code && make deps && cp .env.example .env && make up && make smoke` — sobe os 3 SGBDs e valida conexão+CRUD+busca. Não exige dataset (usa vetores sintéticos no smoke).

### Rodar os benchmarks

Os Cenários precisam do subset MS MARCO baixado (`make` baixa sob demanda no primeiro uso; ~3 GB) e dos 3 SGBDs no ar (`make up`).

```bash
make seed N=10000                       # semeia 10k embeddings nos 3 SGBDs (idempotente)
make bench-A N=10000 Q=1000             # Cenário A — busca pura (curva recall×QPS por sistema)
make bench-B N=10000 Q=1000             # Cenário B — busca com filtro de seletividade
make bench-C-dryrun                     # Cenário C — só imprime o plano de carga (roda na Etapa 4)
```

Saída: um JSON de curva por sistema em `code/results/cenario_<A|B>_<sistema>_<n>_<timestamp>.json`; ground truth exato em `data/ground_truth/`. Todos os alvos aceitam `N Q K EF WARMUP SYS` (e `SEL` no `bench-B`); ver `make help`.

## Comandos

`make help` lista todos. Resumo:

| Comando                  | O que faz                                                |
|--------------------------|----------------------------------------------------------|
| `make deps`              | Cria `.venv` e instala dependências pinadas              |
| `make up`                | Sobe pgvector + Qdrant + Weaviate em background          |
| `make down`              | Derruba os 3 (preserva volumes)                          |
| `make logs`              | Acompanha logs em tempo real                             |
| `make smoke`             | Smoke test integrado (precisa de `make up` antes)        |
| `make test`              | Testes unitários (sem Docker) — alvo padrão              |
| `make test-integration`  | Testes de integração (com Docker; **roda local**, não no CI) |
| `make seed`              | Semeia N embeddings nos 3 SGBDs (sem benchmark)          |
| `make bench-A`           | Cenário A — busca pura (curva recall×QPS)                |
| `make bench-B`           | Cenário B — busca com filtro de seletividade             |
| `make bench-C-dryrun`    | Cenário C — imprime plano de carga (execução na Etapa 4) |
| `make lint`              | `ruff check` + `ruff format --check`                     |
| `make fmt`               | Aplica formatação `ruff`                                 |
| `make clean`             | Remove containers, volumes e caches Python               |

> **CI:** o GitHub Actions roda só `lint` + testes unitários. Integração é local por decisão registrada ([`../vault/decisões/2026-05-19-ci-integracao-local.md`](../vault/decisões/2026-05-19-ci-integracao-local.md)) — rode `make up && make test-integration` antes de commitar mudança de cenário.

## Estrutura

```
code/
├── docker-compose.yml      # 3 SGBDs com healthchecks
├── pyproject.toml          # config ruff + pytest
├── requirements.txt        # versões pinadas (+ requirements.lock)
├── Makefile                # comandos uniformes
├── .env.example
├── pipeline/               # ms_marco_loader, embeddings (cache determinístico)
├── seeders/                # pgvector / qdrant / weaviate (HNSW + atributo seletor)
├── ground_truth/           # exact_search (FAISS; top-K exato e filtrado)
├── lib/                    # metrics (p50/p95/p99, QPS, recall@K), reporting
├── benchmarks/             # cenario_a, cenario_b, cenario_c (esqueleto),
│                           #   buscadores (adaptadores), run_cenario_a/b, run_seed
└── tests/
    ├── unit/               # rápidos, sem Docker (alvo padrão do CI)
    └── integration/        # contra os 3 SGBDs (local)
```

Detalhes e racional de cada peça em [`../docs/tasks/etapa-2-preparacao-ambiente.md`](../docs/tasks/etapa-2-preparacao-ambiente.md) e nas decisões do vault.

## Troubleshooting

### Porta ocupada
Se 5432 / 6333 / 6334 / 8080 estiverem em uso no host, sobrescreva no `.env` antes do `make up`.

### Smoke test falha mesmo com containers "up"
Verifique `docker compose ps` — `STATUS` deve estar `healthy`. Os healthchecks levam até ~30s na primeira execução. Se ficar `unhealthy`, `make logs` aponta o serviço problemático.

### Driver Python falha mesmo com container saudável
Erro comum: cliente psycopg conecta antes do PostgreSQL aceitar conexões TCP. O healthcheck cuida disso pra `make smoke`. Se rodar scripts manuais, aguarde `pg_isready` retornar 0.
