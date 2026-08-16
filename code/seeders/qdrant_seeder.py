"""Seed determinístico para Qdrant.

Cria coleção com `VectorParams` e configuração HNSW, faz upsert em batch
(IDs = 0..N-1) e devolve a contagem inserida.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    HnswConfigDiff,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

# Menor `full_scan_threshold` que o servidor aceita. Ao contrário do Weaviate
# — cuja documentação manda usar `flatSearchCutoff: 0` para forçar o índice
# vetorial —, o Qdrant v1.17 rejeita 0 com HTTP 422:
#     "hnsw_config.full_scan_threshold: value 0 invalid, must be 10 or larger"
# O limiar é medido em KB. Com vetores de 384 dimensões em float32 (1,5 KB
# cada), 10 KB equivalem a ~7 vetores: na prática, qualquer subconjunto
# filtrado de interesse passa a ser respondido por HNSW.
FULL_SCAN_MINIMO = 10


def seed_qdrant(
    *,
    vetores: np.ndarray,
    metadata: Sequence[dict[str, Any]] | None,
    client: QdrantClient,
    nome_colecao: str,
    m: int = 16,
    ef_construction: int = 200,
    batch_size: int = 256,
    full_scan_threshold: int | None = None,
    aguardar_indexacao: bool = True,
    tentativas_indexacao: int = 120,
    intervalo_indexacao: float = 2.0,
) -> int:
    """Cria coleção HNSW (parâmetro `m` = M do paper Malkov & Yashunin) e faz upsert.

    `full_scan_threshold` (em KB) é o limiar abaixo do qual o *query planner* do
    Qdrant prefere varredura completa ao HNSW em buscas filtradas — default do
    servidor é 10000 KB. Com o default, seletividades baixas do Cenário B são
    respondidas por **busca exata**, o que produz `recall = 1,0` artificial e
    inviabiliza a comparação de ANN filtrado. Passar `FULL_SCAN_MINIMO` (10, o
    menor valor que o servidor aceita — 0 é rejeitado com HTTP 422) força HNSW
    para qualquer subconjunto de interesse.
    `None` preserva o default do servidor. Vide
    `vault/decisões/2026-08-16-equalizacao-cenario-b`.

    Os `upsert` usam `wait=False` (carga de 500k estourava o timeout com
    `wait=True`), então a construção do HNSW segue em background depois da
    última chamada. Com `aguardar_indexacao=True` — o default — o seeder só
    retorna quando a coleção atinge o status `green`, garantindo que ninguém
    meça latência ou recall sobre um índice pela metade. Levanta `TimeoutError`
    se o índice não ficar pronto em `tentativas_indexacao` consultas.
    """
    if vetores.ndim != 2:
        raise ValueError(f"vetores precisa ser 2D, recebido shape={vetores.shape}")
    n, dim = vetores.shape
    if metadata is not None and len(metadata) != n:
        raise ValueError(f"metadata len={len(metadata)} != vetores N={n}")

    client.create_collection(
        collection_name=nome_colecao,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        hnsw_config=HnswConfigDiff(
            m=m,
            ef_construct=ef_construction,
            full_scan_threshold=full_scan_threshold,
        ),
    )

    # Cenário B: índice de payload em `seletor` só quando o atributo existe.
    # Necessário para o filtered-ANN do Qdrant ser comparável (pgvector usa a
    # coluna; Weaviate indexa propriedades por padrão). Cenário A não tem
    # `seletor` no metadata ⇒ nenhum índice criado ⇒ coleção idêntica.
    if metadata is not None and any("seletor" in md for md in metadata):
        client.create_payload_index(
            collection_name=nome_colecao,
            field_name="seletor",
            field_schema=PayloadSchemaType.FLOAT,
            wait=True,
            timeout=120,
        )

    buffer: list[PointStruct] = []
    for i in range(n):
        payload = dict(metadata[i]) if metadata else {}
        buffer.append(PointStruct(id=i, vector=vetores[i].tolist(), payload=payload))
        if len(buffer) >= batch_size:
            client.upsert(collection_name=nome_colecao, points=buffer, wait=False)
            buffer = []
    if buffer:
        client.upsert(collection_name=nome_colecao, points=buffer, wait=False)

    if aguardar_indexacao:
        _aguardar_green(
            client,
            nome_colecao,
            tentativas=tentativas_indexacao,
            intervalo=intervalo_indexacao,
        )
    return n


def _aguardar_green(
    client: QdrantClient, nome_colecao: str, *, tentativas: int, intervalo: float
) -> None:
    """Bloqueia até a coleção sair de `yellow` (indexação em background)."""
    status = "desconhecido"
    for tentativa in range(tentativas):
        status = str(client.get_collection(nome_colecao).status)
        if status == "green":
            return
        if tentativa < tentativas - 1:
            time.sleep(intervalo)
    raise TimeoutError(
        f"coleção '{nome_colecao}' não atingiu status green após {tentativas} "
        f"consultas (último status: {status}); índice HNSW ainda em construção"
    )
