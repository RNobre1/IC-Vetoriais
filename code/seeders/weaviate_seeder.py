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
from weaviate.classes.config import (
    Configure,
    DataType,
    Property,
    VectorDistances,
    VectorFilterStrategy,
)


def seed_weaviate(
    *,
    vetores: np.ndarray,
    metadata: Sequence[dict[str, Any]] | None,
    client: weaviate.WeaviateClient,
    nome_classe: str,
    m: int = 16,
    ef_construction: int = 200,
    batch_size: int = 100,
    flat_search_cutoff: int | None = None,
    filter_strategy: str | None = None,
) -> int:
    """Cria classe HNSW (parâmetro `m` = M do paper Malkov & Yashunin) e insere em batch.

    Propriedades: `external_id` (int), `categoria` (text), `seletor` (number,
    atributo do Cenário B). `seletor`/`categoria` só são gravados quando
    presentes em `metadata[i]` — Cenário A (`metadata=None`) fica intacto.

    `flat_search_cutoff` é o limiar de objetos elegíveis abaixo do qual o
    Weaviate troca o HNSW por busca exata (*flat*) em consultas filtradas —
    default do servidor é **40000**. Com o default, as seletividades baixas do
    Cenário B são respondidas por varredura exata, produzindo `recall = 1,0`
    que mede o *fallback*, não a qualidade do ANN filtrado. A documentação
    oficial indica `flatSearchCutoff: 0` para forçar o índice vetorial.
    `filter_strategy` registra explicitamente a estratégia (`acorn` é default a
    partir da v1.34; nossa imagem é a 1.37.2). `None` em ambos preserva o
    default do servidor. Vide `vault/decisões/2026-08-16-equalizacao-cenario-b`.
    """
    if vetores.ndim != 2:
        raise ValueError(f"vetores precisa ser 2D, recebido shape={vetores.shape}")
    n, _dim = vetores.shape
    if metadata is not None and len(metadata) != n:
        raise ValueError(f"metadata len={len(metadata)} != vetores N={n}")

    estrategia = VectorFilterStrategy(filter_strategy) if filter_strategy is not None else None
    client.collections.create(
        name=nome_classe,
        vector_config=Configure.Vectors.self_provided(
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
                max_connections=m,
                ef_construction=ef_construction,
                flat_search_cutoff=flat_search_cutoff,
                filter_strategy=estrategia,
            ),
        ),
        properties=[
            Property(name="external_id", data_type=DataType.INT),
            Property(name="categoria", data_type=DataType.TEXT),
            Property(name="seletor", data_type=DataType.NUMBER),
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
                sel = metadata[i].get("seletor")
                if sel is not None:
                    props["seletor"] = float(sel)
            batch.add_object(properties=props, vector=vetores[i].tolist())
    return n
