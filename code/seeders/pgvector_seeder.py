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
) -> int:
    """Cria `<nome_tabela>` (id, embedding, categoria), insere e indexa via HNSW.

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
            f"embedding vector({dim}), categoria text)"
        )

        linhas = [
            (
                i,
                vetores[i],
                metadata[i].get("categoria") if metadata else None,
            )
            for i in range(n)
        ]
        cur.executemany(
            f"INSERT INTO {nome_tabela} (id, embedding, categoria) VALUES (%s, %s, %s)",
            linhas,
        )

        # Índice HNSW após o INSERT (recomendação do pgvector para grandes lotes).
        cur.execute(
            f"CREATE INDEX ON {nome_tabela} USING hnsw (embedding vector_cosine_ops) "
            f"WITH (m = {m}, ef_construction = {ef_construction})"
        )
    conn.commit()
    return n
