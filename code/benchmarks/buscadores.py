"""Adaptadores concretos do Protocol `BuscadorVetorial` (um por SGBD).

Cada adaptador é a ponte entre `cenario_a.medir_sistema` e a API nativa de
um SGBD. Contrato (vide `cenario_a.BuscadorVetorial`):

- `nome`: identificador do sistema (vai para `ResultadoBenchmark.sistema`).
- `configurar_ef_search(ef)`: ajusta o parâmetro de busca HNSW *daquele* SGBD.
- `buscar_uma(query, k)`: retorna os ids (`0..N-1`, consistentes com os
  seeders) dos `k` vizinhos mais próximos.

A consistência de id é garantida pelos seeders: pgvector usa `id` inteiro,
Qdrant usa point id inteiro, Weaviate guarda `external_id` (UUID interno é
ignorado). Distância: cosseno nos três (vetores normalizados L2).
"""

from __future__ import annotations

import numpy as np
import psycopg
import weaviate
from qdrant_client import QdrantClient
from qdrant_client.http.models import SearchParams
from weaviate.classes.config import Reconfigure


class PgvectorBuscador:
    """`SET hnsw.ef_search` por sessão; busca por operador de cosseno `<=>`."""

    nome = "pgvector"

    def __init__(self, *, conn: psycopg.Connection, nome_tabela: str) -> None:
        self._conn = conn
        self._tabela = nome_tabela
        from pgvector.psycopg import register_vector

        register_vector(conn)

    def configurar_ef_search(self, ef: int) -> None:
        with self._conn.cursor() as cur:
            # ef é int validado pela orquestração; SET não aceita placeholder.
            cur.execute(f"SET hnsw.ef_search = {int(ef)}")
        self._conn.commit()

    def buscar_uma(self, query: np.ndarray, k: int) -> list[int]:
        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT id FROM {self._tabela} ORDER BY embedding <=> %s LIMIT %s",
                (query, k),
            )
            return [linha[0] for linha in cur.fetchall()]


class QdrantBuscador:
    """`hnsw_ef` passado em `SearchParams` a cada `query_points`."""

    nome = "qdrant"

    def __init__(self, *, client: QdrantClient, nome_colecao: str) -> None:
        self._client = client
        self._colecao = nome_colecao
        self._ef: int | None = None

    def configurar_ef_search(self, ef: int) -> None:
        self._ef = int(ef)

    def buscar_uma(self, query: np.ndarray, k: int) -> list[int]:
        resposta = self._client.query_points(
            collection_name=self._colecao,
            query=query.tolist(),
            limit=k,
            search_params=SearchParams(hnsw_ef=self._ef),
        )
        return [p.id for p in resposta.points]


class WeaviateBuscador:
    """`ef` é config do índice HNSW — atualizado via `Reconfigure` no sweep.

    `near_vector` devolve a propriedade `external_id` (id 0..N-1 gravado pelo
    seeder); o UUID interno do Weaviate não é usado.
    """

    nome = "weaviate"

    def __init__(self, *, client: weaviate.WeaviateClient, nome_classe: str) -> None:
        self._col = client.collections.get(nome_classe)

    def configurar_ef_search(self, ef: int) -> None:
        # weaviate-client 4.21: `vector_index_config=` em config.update foi
        # deprecado (Dep017). O caminho atual é `vector_config=` envolvendo
        # Reconfigure.Vectors.update (name=None → vetor default do self_provided).
        self._col.config.update(
            vector_config=Reconfigure.Vectors.update(
                vector_index_config=Reconfigure.VectorIndex.hnsw(ef=int(ef)),
            )
        )

    def buscar_uma(self, query: np.ndarray, k: int) -> list[int]:
        resultado = self._col.query.near_vector(
            near_vector=query.tolist(),
            limit=k,
            return_properties=["external_id"],
        )
        return [int(o.properties["external_id"]) for o in resultado.objects]
