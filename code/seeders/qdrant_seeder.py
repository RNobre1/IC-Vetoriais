"""Seed determinístico para Qdrant.

Cria coleção com `VectorParams` e configuração HNSW, faz upsert em batch
(IDs = 0..N-1) e devolve a contagem inserida.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    HnswConfigDiff,
    PointStruct,
    VectorParams,
)


def seed_qdrant(
    *,
    vetores: np.ndarray,
    metadata: Sequence[dict[str, Any]] | None,
    client: QdrantClient,
    nome_colecao: str,
    m: int = 16,
    ef_construction: int = 200,
    batch_size: int = 256,
) -> int:
    """Cria coleção HNSW (parâmetro `m` = M do paper Malkov & Yashunin) e faz upsert."""
    if vetores.ndim != 2:
        raise ValueError(f"vetores precisa ser 2D, recebido shape={vetores.shape}")
    n, dim = vetores.shape
    if metadata is not None and len(metadata) != n:
        raise ValueError(f"metadata len={len(metadata)} != vetores N={n}")

    client.create_collection(
        collection_name=nome_colecao,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        hnsw_config=HnswConfigDiff(m=m, ef_construct=ef_construction),
    )

    buffer: list[PointStruct] = []
    for i in range(n):
        payload = dict(metadata[i]) if metadata else {}
        buffer.append(PointStruct(id=i, vector=vetores[i].tolist(), payload=payload))
        if len(buffer) >= batch_size:
            client.upsert(collection_name=nome_colecao, points=buffer, wait=True)
            buffer = []
    if buffer:
        client.upsert(collection_name=nome_colecao, points=buffer, wait=True)
    return n
