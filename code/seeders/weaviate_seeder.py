"""Seed determinístico para Weaviate.

Cria classe com vector index HNSW, insere em batch fixo e devolve contagem.

Mantém a propriedade `external_id` (int, 0..N-1) — Weaviate usa UUID interno como
PK, então preservamos o id externo no payload para sanity de busca pós-seed.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import weaviate
from weaviate.classes.config import Configure, DataType, Property, VectorDistances


def seed_weaviate(
    *,
    vetores: np.ndarray,
    metadata: Sequence[dict[str, Any]] | None,
    client: weaviate.WeaviateClient,
    nome_classe: str,
    m: int = 16,
    ef_construction: int = 200,
    batch_size: int = 100,
) -> int:
    """Cria classe HNSW (parâmetro `m` = M do paper Malkov & Yashunin) e insere em batch."""
    if vetores.ndim != 2:
        raise ValueError(f"vetores precisa ser 2D, recebido shape={vetores.shape}")
    n, _dim = vetores.shape
    if metadata is not None and len(metadata) != n:
        raise ValueError(f"metadata len={len(metadata)} != vetores N={n}")

    client.collections.create(
        name=nome_classe,
        vector_config=Configure.Vectors.self_provided(
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
                max_connections=m,
                ef_construction=ef_construction,
            ),
        ),
        properties=[
            Property(name="external_id", data_type=DataType.INT),
            Property(name="categoria", data_type=DataType.TEXT),
        ],
    )

    col = client.collections.get(nome_classe)
    with col.batch.fixed_size(batch_size=batch_size) as batch:
        for i in range(n):
            props: dict[str, Any] = {"external_id": i}
            if metadata is not None:
                cat = metadata[i].get("categoria")
                if cat is not None:
                    props["categoria"] = cat
            batch.add_object(properties=props, vector=vetores[i].tolist())
    return n
