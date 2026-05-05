# IC-Vetoriais — `code/`

Ambiente experimental para a IC **"Comparação de Desempenho de Soluções de Bancos de Dados Vetoriais para Busca Semântica"** (UFOPA/IEG; bolsista: Rafael Nobre; orientador: Prof. Dr. Celson Pantoja Lima).

> **Status:** Etapa 2, Dia 1 — esqueleto do ambiente. Plano completo em [`../docs/tasks/etapa-2-preparacao-ambiente.md`](../docs/tasks/etapa-2-preparacao-ambiente.md). Decisões metodológicas em [`../vault/decisões/`](../vault/decisões/).

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
| `make test-integration`  | Testes de integração (com Docker)                        |
| `make lint`              | `ruff check` + `ruff format --check`                     |
| `make fmt`               | Aplica formatação `ruff`                                 |
| `make clean`             | Remove containers, volumes e caches Python               |

## Estrutura

```
code/
├── docker-compose.yml      # 3 SGBDs com healthchecks
├── pyproject.toml          # config ruff + pytest
├── requirements.txt        # versões pinadas
├── Makefile                # comandos uniformes
├── .env.example
└── tests/
    ├── unit/
    └── integration/
```

A árvore se expande nos Dias 2–4 com `pipeline/`, `seeders/`, `ground_truth/`, `benchmarks/`, `lib/`. Detalhes em [`../docs/tasks/etapa-2-preparacao-ambiente.md`](../docs/tasks/etapa-2-preparacao-ambiente.md).

## Troubleshooting

### Porta ocupada
Se 5432 / 6333 / 6334 / 8080 estiverem em uso no host, sobrescreva no `.env` antes do `make up`.

### Smoke test falha mesmo com containers "up"
Verifique `docker compose ps` — `STATUS` deve estar `healthy`. Os healthchecks levam até ~30s na primeira execução. Se ficar `unhealthy`, `make logs` aponta o serviço problemático.

### Driver Python falha mesmo com container saudável
Erro comum: cliente psycopg conecta antes do PostgreSQL aceitar conexões TCP. O healthcheck cuida disso pra `make smoke`. Se rodar scripts manuais, aguarde `pg_isready` retornar 0.
