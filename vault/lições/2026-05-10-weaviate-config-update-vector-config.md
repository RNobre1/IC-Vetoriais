---
tipo: lição-aprendida
data: 2026-05-10
contexto: Dia 3 da Etapa 2 — implementação do `WeaviateBuscador` (adaptador do Cenário A). O smoke de integração quebrou ao tentar ajustar `efSearch` via `collection.config.update`. Vide [[../sessões/2026-05-10]] e [[../decisões/2026-05-10-cenario-a-queries-warmup]].
tags: [weaviate, weaviate-client, hnsw, ef, deprecation, api, dependencias]
---

# weaviate-client 4.21: `config.update(vector_index_config=)` deprecado → `vector_config=`

## Situação
`WeaviateBuscador.configurar_ef_search(ef)` precisa ajustar o `ef` (efSearch) do índice HNSW entre cada ponto do sweep do Cenário A. A primeira implementação usou:

```python
self._col.config.update(vector_index_config=Reconfigure.VectorIndex.hnsw(ef=int(ef)))
```

O teste de integração falhou com:

```
DeprecationWarning: Dep017: You are using the `vector_index_config` argument in the
`collection.config.update()` method, which is deprecated. Use the `vector_config` argument instead.
...
KeyError: 'vectorIndexConfig'
```

Não foi só warning — quebrou com `KeyError` dentro do próprio client (`config.py:1547`), abortando o update. pgvector e Qdrant passaram de primeira; só o Weaviate quebrou.

## Causa
A coleção foi criada pelo seeder com `Configure.Vectors.self_provided(vector_index_config=Configure.VectorIndex.hnsw(...))` — estilo "vetor único default" da API nova (v4). No `weaviate-client` 4.21, o argumento `vector_index_config=` de `collection.config.update()` foi **deprecado e está quebrado** para coleções criadas nesse estilo (espera a chave legada `vectorIndexConfig` no schema, que não existe mais). O caminho atual é o argumento `vector_config=`, envolvendo `Reconfigure.Vectors.update(...)`.

## Correção aplicada
Superfície real sondada via `inspect.signature` (não chutar API):

- `Reconfigure.Vectors.update(*, name: str | None = None, vector_index_config=...)` → `_VectorConfigUpdate`.
- HNSW update fica em `Reconfigure.VectorIndex.hnsw(ef=...)` (não existe `Reconfigure.hnsw`).
- `name=None` referencia o vetor default do `self_provided`.

```python
self._col.config.update(
    vector_config=Reconfigure.Vectors.update(
        vector_index_config=Reconfigure.VectorIndex.hnsw(ef=int(ef)),
    )
)
```

Smoke de integração dos 3 adaptadores: **3/3 verde**. Suíte total 109/109.

## Aplicação a futuro
- **No `weaviate-client` v4.2x+, usar sempre `vector_config=Reconfigure.Vectors.update(...)`** para alterar config de índice de coleções criadas com `Configure.Vectors.self_provided(...)`. `vector_index_config=` direto em `config.update` é legado.
- **Diante de `DeprecationWarning` de client de SGBD, não ignorar como ruído** — neste caso o "deprecado" já vinha acompanhado de `KeyError` que abortava a operação. Tratar Dep* do weaviate-client como erro até prova em contrário.
- **Sondar API com `inspect.signature`/`dir()` antes de implementar adaptador** contra lib que muda rápido (weaviate-client teve várias quebras v4.x). Mais barato que iterar pelo traceback.
- O `ef` do Weaviate é parâmetro de *config do índice* (precisa `config.update` entre execuções do sweep), diferente do Qdrant (`hnsw_ef` por query em `SearchParams`) e do pgvector (`SET hnsw.ef_search` por sessão). Os três têm modelos distintos de onde o efSearch vive — documentado nos docstrings de `benchmarks/buscadores.py`.

## Backlinks
- [[../sessões/2026-05-10]]
- [[../decisões/2026-05-10-cenario-a-queries-warmup]]
- [[2026-05-06-pegadinhas-bump-versoes-sgbds]]
