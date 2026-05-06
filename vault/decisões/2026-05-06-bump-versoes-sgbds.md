---
tipo: decisão
data: 2026-05-06
status: aceita
supersede: 2026-05-05-versoes-imagens-docker
autores: ["Rafael Nobre", "Celson Lima"]
tags: [infraestrutura, docker, versões, reprodutibilidade, bump]
---

# Bump das versões dos 3 SGBDs e respectivos clientes Python

## Contexto
A ADR anterior ([[2026-05-05-versoes-imagens-docker]]) fixou Qdrant `v1.12.0` (out/2024), Weaviate `1.27.0` (out/2024) e pgvector sobre Postgres 16 — versões com ~18 meses de defasagem em relação às mais recentes na data de execução do projeto (2026-05).

A ADR antiga acertou em **fixar versões** para reprodutibilidade científica, mas **não justificou por que essas versões específicas** em vez das mais novas estáveis. Reprodutibilidade exige snapshot fixo, não versão antiga. Sustentar v1.12/1.27 numa banca seria difícil — o estudo estaria medindo um estado-da-arte defasado, ignorando melhorias materiais em quantização (Qdrant), BQ/RQ (Weaviate) e Postgres 18 (LTS, com melhorias de performance no planner para varreduras vetoriais via pgvector 0.8).

Como nenhum benchmark ainda rodou (apenas o smoke test do Dia 1), o custo de bump é mínimo — basicamente re-validar smoke. O custo de adiar disparou após começarem os experimentos da Etapa 3.

## Opções consideradas
1. **Manter v1.12 / 1.27 / pg16** (status quo)
   - Prós: smoke já validado.
   - Contras: difícil defender "por que essas versões?"; perde melhorias de performance e funcionalidades (HNSW filtrado, BQ no Weaviate, etc.).
2. **Bump para versões mais recentes estáveis em 2026-05** (escolhida)
   - Prós: estado-da-arte alinhado ao momento do projeto; defensável em banca; aproveitamos otimizações reais.
   - Contras: re-validar smoke; lidar com breaking changes em clientes Python.
3. **Bump apenas dos servers, manter clientes antigos**
   - Prós: menos retrabalho de código.
   - Contras: clientes antigos perdem acesso a features novas; risco de incompatibilidade silenciosa.

## Decisão

### Imagens Docker (versões pinadas)

| Componente | Versão | Release upstream | Imagem (Docker Hub push) | Verificação |
|---|---|---|---|---|
| `pgvector/pgvector:0.8.2-pg18-bookworm` | pgvector 0.8.2 + Postgres **18.3** | 2025-09-22 (pg18.0); 2026-02-23 (pg18.3); 2026-02-26 (push pgvector pg18) | 2026-02-26 | `docker run --rm pgvector/pgvector:0.8.2-pg18-bookworm postgres --version` → `PostgreSQL 18.3 (Debian 18.3-1.pgdg12+1)` |
| `qdrant/qdrant:v1.17.1` | Qdrant 1.17.1 | 2026-03-27 | 2026-03-26 | [GitHub release](https://github.com/qdrant/qdrant/releases/tag/v1.17.1) |
| `semitechnologies/weaviate:1.37.2` | Weaviate 1.37.2 | 2026-04-23 | 2026-04-23 | [GitHub release](https://github.com/weaviate/weaviate/releases/tag/v1.37.2) |

### Clientes Python (em `code/requirements.txt`)

| Pacote | Antes | Agora |
|---|---|---|
| `psycopg[binary,pool]` | 3.2.13 | **3.3.4** |
| `pgvector` (adapter Python) | 0.3.6 | **0.4.2** |
| `qdrant-client` | 1.12.1 | **1.17.1** (pareado com server) |
| `weaviate-client` | 4.9.6 | **4.21.0** |
| `httpx` | 0.27.0 | **0.28.1** (desbloqueado pelo bump do weaviate-client) |

## Justificativa

- **PostgreSQL 18** é LTS (released 2025-09-25) com melhorias de planner relevantes para queries vetoriais. **18.3** é o último patch da family na data desta ADR.
- **pgvector 0.8.2** introduz suporte a iterative HNSW scans e melhor uso de quantização — alinhado ao Cenário B (filtros + HNSW).
- **Qdrant 1.17** trouxe quantização aprimorada (Binary Quantization estável) e a API `query_points` que substitui o legado `search` (breaking change documentado).
- **Weaviate 1.37** consolidou a API de configuração de coleções em `vector_config` e melhorou BQ/RQ.
- **Pareamento server↔cliente:** Qdrant client e server são distribuídos em sincronia; usar v1.17.1 nos dois evita degradação silenciosa de features.
- Versões verificadas em **2026-05-05** consultando: Docker Hub Registry API v2, GitHub Releases API e PyPI JSON API. Nenhum número veio de memória do modelo.

## Consequência

### Mudanças aplicadas
- `code/docker-compose.yml`: 3 tags atualizadas; **mount point do Postgres** mudou de `/var/lib/postgresql/data` para `/var/lib/postgresql` (breaking change da imagem oficial Postgres 18 — vide [docker-library/postgres#1259](https://github.com/docker-library/postgres/pull/1259)).
- `code/requirements.txt` e `code/requirements.lock`: bump dos 5 pacotes.
- `code/tests/integration/test_smoke.py`: ajuste para `qdrant_client.query_points` e Weaviate `vector_config=Configure.Vectors.self_provided(...)`.
- Detalhes das pegadinhas em [[../lições/2026-05-06-pegadinhas-bump-versoes-sgbds]].

### Volume de dados antigo é incompatível
Volumes nomeados (`code_pgdata`, `code_qdrantdata`, `code_weaviatedata`) criados na ADR anterior **foram destruídos** com `docker compose down -v`. Não havia dados experimentais úteis (apenas smoke). Se houvesse, exigiria `pg_upgrade --link` (vide warning do entrypoint do Postgres 18) e migrações específicas de Qdrant/Weaviate.

### Validação após bump
- `make smoke` → **6/6 verde** (pgvector, Qdrant e Weaviate todos OK).
- `make test-unit` → **2/2 verde**.
- `make lint` → ✓ (ruff check + format).

### Próximas pegadinhas a vigiar
- Driver `qdrant-client` 1.17 deprecou outras chamadas além de `search` (e.g. `recommend` virou `recommend_query`). Conferir ao escrever os seeders no Dia 2.
- API do Weaviate v4.x consolidou config — `Configure.Vectorizer.none()` e `vector_index_config` no top-level estão **deprecated** (Dep024/Dep025) e podem virar erro em minor releases futuras. Toda config nova usa `vector_config=Configure.Vectors.self_provided(...)`.

## Critério de revisão
Reabrir esta ADR se: (a) bug específico de uma das versões afetar experimentos; (b) o orientador requisitar versão diferente; (c) for descoberto comportamento materialmente diferente em versão mais nova que impacte os resultados; (d) versão sair de suporte de segurança crítico durante o projeto; ou (e) os experimentos reais mostrarem que uma versão alternativa muda o ranking comparativo entre os 3 sistemas.

## Backlinks
- [[2026-05-05-versoes-imagens-docker]] (superseded por esta)
- [[2026-04-28-sistemas-avaliados]]
- [[2026-04-28-índice-hnsw-em-todos]]
- [[2026-04-28-cenarios-A-B-C]]
- [[../lições/2026-05-06-pegadinhas-bump-versoes-sgbds]]
- [[../referência/metodologia-benchmarking-ann]]
