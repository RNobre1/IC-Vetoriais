---
tipo: lição-aprendida
data: 2026-05-06
contexto: Etapa 2 — bump das versões dos 3 SGBDs e clientes Python (vide [[../decisões/2026-05-06-bump-versoes-sgbds]])
tags: [docker, postgres, pgvector, qdrant, weaviate, breaking-change, dependencias]
---

# Pegadinhas no bump pg16→pg18 / Qdrant 1.12→1.17 / Weaviate 1.27→1.37

## Situação
Em 2026-05-06, ao bumpar as 3 imagens Docker e seus clientes Python correspondentes (vide ADR), três armadilhas precisaram de correção antes do `make smoke` voltar a 6/6 verde. Nenhuma delas estava prevista nem documentada de forma destacada nos changelogs principais — todas exigiram ler logs/mensagens de erro com atenção.

## Armadilha 1 — Postgres 18 mudou o mount point do volume Docker

**Sintoma:** `ic-pgvector` em loop de restart logo após `make up`. Logs mostravam:

```
Error: in 18+, these Docker images are configured to store database data in a
       format which is compatible with "pg_ctlcluster" (specifically, using
       major-version-specific directory names).
       (...)
       Counter to that, there appears to be PostgreSQL data in:
         /var/lib/postgresql/data (unused mount/volume)
```

**Causa:** A partir do Postgres 18, a imagem oficial mudou o ponto de montagem padrão do volume de **`/var/lib/postgresql/data`** para **`/var/lib/postgresql`** (PGDATA passa a ser `/var/lib/postgresql/18/docker`, agrupado por major version). Isso facilita uso futuro de `pg_upgrade --link` sem boundary issues. Ver [docker-library/postgres#1259](https://github.com/docker-library/postgres/pull/1259) e [issue#37](https://github.com/docker-library/postgres/issues/37).

**Correção:** trocar no `docker-compose.yml`:

```yaml
volumes:
  - pgdata:/var/lib/postgresql   # antes: /var/lib/postgresql/data
```

E `docker compose down -v` para apagar o volume anterior incompatível.

**Aplicação a futuro:**
- Em qualquer próximo bump de major version do Postgres, **conferir o changelog da imagem oficial** (não só do Postgres em si) — a base Docker tem decisões próprias.
- Se houver dados reais antes do bump, NÃO basta trocar mount: precisa de `pg_upgrade --link` (vide README upstream).

## Armadilha 2 — `qdrant-client` 1.17 removeu `client.search()`

**Sintoma:** `AttributeError: 'QdrantClient' object has no attribute 'search'` no smoke test, mesmo com a coleção criada e o upsert OK.

**Causa:** A partir de qdrant-client 1.10 a API recomendada virou `query_points` (mais flexível, suporta vetores prefixados, multivetores e prefetch). Em 1.17 o método legado `search` **foi removido** sem warning de deprecação visível em runtime — só breaking change.

**Correção:** trocar:

```python
# antes
resultados = client.search(
    collection_name=col,
    query_vector=v,
    limit=1,
)
assert resultados[0].id == 1

# agora
resposta = client.query_points(
    collection_name=col,
    query=v,
    limit=1,
)
assert resposta.points[0].id == 1
```

Notar que o retorno mudou de `list[ScoredPoint]` para `QueryResponse` (objeto com `.points`).

**Aplicação a futuro:**
- Ao escrever os seeders e cenários (Dia 2 e Dia 3), assumir que **toda chamada ao Qdrant deve usar a API nova** (`query_points`, `query_batch_points`, `recommend_query`, etc.).
- Quando atualizar bibliotecas com versão major-baixa-mas-rápida (Qdrant lança ~minor por mês), revisar changelog da minor entre as duas versões pinadas, não só da última.

## Armadilha 3 — `weaviate-client` 4.21 deprecou `vectorizer_config` e `vector_index_config` top-level

**Sintoma:** smoke test passou, mas com 2 warnings:

```
DeprecationWarning: Dep024: You are using the `vectorizer_config` argument in `collection.config.create()`, which is deprecated.
            Use the `vector_config` argument instead.

DeprecationWarning: Dep025: You are using the `vector_index_config` argument in `collection.config.create()`, which is deprecated.
            Use the `vector_config` argument instead defining `vector_index_config` as a sub-argument.
```

**Causa:** Weaviate v4.x consolidou os dois argumentos em um único `vector_config`, com `vector_index_config` virando sub-argumento. Suporte ao formato antigo continua, mas vai ser removido. Para single unnamed vector, o equivalente direto é `Configure.Vectors.self_provided(...)`.

**Correção:**

```python
# antes
client.collections.create(
    name=N,
    vectorizer_config=Configure.Vectorizer.none(),
    vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE),
    properties=[...],
)

# agora
client.collections.create(
    name=N,
    vector_config=Configure.Vectors.self_provided(
        vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE),
    ),
    properties=[...],
)
```

`Configure.Vectors.self_provided` substitui semanticamente o antigo `Vectorizer.none()` (Weaviate não vetoriza, o cliente injeta).

**Aplicação a futuro:**
- Ao escrever o `seeders/weaviate_seeder.py` no Dia 2, **já nascer com a API nova**. Não introduzir débito técnico.
- Ao criar coleções com múltiplos vetores nomeados (e.g. para experimentos com múltiplos embeddings na Etapa 4), usar `Configure.NamedVectors.self_provided(name="...", vector_index_config=...)` — mesma família de API.
- Configurar pytest para tratar DeprecationWarning como erro nos testes (`filterwarnings = error::DeprecationWarning`) **só depois** de revisar todas as chamadas Weaviate; do contrário CI falha em features periféricas.

## Lição geral

**Bumpar imagens Docker e clientes Python juntos, mas validar separadamente.**

A tentação é fazer um único bump grande. O que funciona melhor:
1. Bump das imagens primeiro; smoke com clientes antigos confirma que a infra subiu.
2. Bump dos clientes em seguida; smoke com clientes novos confirma que a API se manteve compatível.

Aqui fizemos os dois ao mesmo tempo, e os 2 erros (qdrant `search` removido + weaviate `vectorizer_config` deprecated) só apareceram no segundo `make smoke`. Funcionou, mas se algo desse errado seria difícil isolar a fonte. Para o próximo bump:
- ✓ Pinning é reprodutibilidade, não compatibilidade automática.
- ✓ Sempre re-rodar `make smoke` a cada bump significativo.
- ✓ Tratar DeprecationWarning como sinal: hoje warning, daqui a 6 meses erro.

## Backlinks
- [[../decisões/2026-05-06-bump-versoes-sgbds]]
- [[../decisões/2026-05-05-versoes-imagens-docker]] (superseded)
- [[2026-05-05-armadilhas-dia-1-etapa-2]] (lição irmã, pegadinhas do Dia 1)
