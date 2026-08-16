"""Seed determinístico para PostgreSQL+pgvector.

Cria a tabela alvo, insere os vetores em batch (id = 0..N-1, ordem de entrada)
e constrói índice HNSW com parâmetros uniformes aos demais sistemas.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import psycopg
from pgvector.psycopg import register_vector


def seed_pgvector(
    *,
    vetores: np.ndarray,
    metadata: Sequence[dict[str, Any]] | None,
    conn: psycopg.Connection,
    nome_tabela: str,
    m: int = 16,
    ef_construction: int = 200,
    indexar_seletor: bool = False,
) -> int:
    """Cria `<nome_tabela>` (id, embedding, categoria, seletor), insere e indexa HNSW.

    `indexar_seletor=True` cria B-tree em `seletor`. Sem ele, o pgvector é o
    único dos três sistemas sem índice no atributo de filtro (o Qdrant recebe
    índice de payload e o Weaviate indexa propriedades por padrão) — assimetria
    que invalidaria a comparação do Cenário B. Default `False` preserva o que
    rodou em julho/2026. Vide `vault/decisões/2026-08-16-equalizacao-cenario-b`.

    `seletor` (`real`, nullable) é o atributo numérico do Cenário B — lido de
    `metadata[i]["seletor"]` quando presente, `NULL` caso contrário (Cenário A
    passa `metadata=None`/sem a chave, mantendo-se intacto).

    `m` é o parâmetro `M` do paper HNSW (Malkov & Yashunin, 2018) — número
    de conexões por nó nas camadas superiores. Mantido em minúsculo por PEP 8.

    Retorna a contagem de linhas inseridas.
    """
    if vetores.ndim != 2:
        raise ValueError(f"vetores precisa ser 2D, recebido shape={vetores.shape}")
    n, dim = vetores.shape
    if metadata is not None and len(metadata) != n:
        raise ValueError(f"metadata len={len(metadata)} != vetores N={n}")

    register_vector(conn)
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE TABLE {nome_tabela} (id integer PRIMARY KEY, "
            f"embedding vector({dim}), categoria text, seletor real)"
        )

        linhas = [
            (
                i,
                vetores[i],
                metadata[i].get("categoria") if metadata else None,
                metadata[i].get("seletor") if metadata else None,
            )
            for i in range(n)
        ]
        cur.executemany(
            f"INSERT INTO {nome_tabela} (id, embedding, categoria, seletor) "
            f"VALUES (%s, %s, %s, %s)",
            linhas,
        )

        # Índice HNSW após o INSERT (recomendação do pgvector para grandes lotes).
        cur.execute(
            f"CREATE INDEX ON {nome_tabela} USING hnsw (embedding vector_cosine_ops) "
            f"WITH (m = {m}, ef_construction = {ef_construction})"
        )

        # Cenário B equalizado: índice no atributo de filtro. Só faz sentido
        # quando `seletor` foi de fato gravado (Cenário A passa metadata=None).
        if indexar_seletor and metadata is not None:
            cur.execute(f"CREATE INDEX ON {nome_tabela} USING btree (seletor)")
    conn.commit()
    return n
