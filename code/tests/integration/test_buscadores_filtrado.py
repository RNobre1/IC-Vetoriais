"""Smoke de integração da busca filtrada (Cenário B) dos 3 adaptadores.

Cada adaptador `BuscadorVetorial` ganha `buscar_uma_filtrada(query, k, *, p_max)`
— os `k` vizinhos mais próximos *entre os vetores com `seletor < p_max`*
(vide ADR [[../../vault/decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]).

Valida ponta-a-ponta contra o ground truth filtrado exato
(`ground_truth.exact_search.top_k_exato_filtrado`): só ids que passam o
predicado são devolvidos, e o recall@K sob filtro é alto.

Marcado `integration` — exige `make up` (3 SGBDs healthy).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from typing import Any

import numpy as np
import psycopg
import pytest
import weaviate
from dotenv import load_dotenv
from qdrant_client import QdrantClient

from benchmarks.buscadores import (
    PgvectorBuscador,
    QdrantBuscador,
    WeaviateBuscador,
)
from ground_truth.exact_search import top_k_exato_filtrado
from lib.metrics import recall_at_k
from seeders.pgvector_seeder import seed_pgvector
from seeders.qdrant_seeder import seed_qdrant
from seeders.weaviate_seeder import seed_weaviate

pytestmark = pytest.mark.integration

K = 10
N_BASE = 300
N_QUERIES = 20
P_MAX = 0.1  # seletor < 0.1 ⇒ ids 0..29 (30 de 300) elegíveis


@pytest.fixture(scope="module")
def env() -> dict[str, str]:
    load_dotenv()
    return dict(os.environ)


@pytest.fixture(scope="module")
def dados() -> dict[str, Any]:
    """base + queries held-out + seletor determinístico + GT filtrado exato."""
    rng = np.random.default_rng(42)
    total = rng.normal(size=(N_BASE + N_QUERIES, 384)).astype(np.float32)
    total /= np.linalg.norm(total, axis=1, keepdims=True)
    base = total[:N_BASE]
    queries = total[N_BASE:]
    seletor = np.arange(N_BASE, dtype=np.float64) / N_BASE
    metadata = [{"seletor": float(seletor[i])} for i in range(N_BASE)]
    _, gt_ids = top_k_exato_filtrado(base, queries, seletor=seletor, p=P_MAX, k=K)
    return {
        "base": base,
        "queries": queries,
        "seletor": seletor,
        "metadata": metadata,
        "gt_ids": gt_ids,
        "n_elegiveis": int((seletor < P_MAX).sum()),
    }


def _assertivas(buscador: Any, dados: dict[str, Any]) -> None:
    ids_obtidos = np.empty((N_QUERIES, K), dtype=np.int64)
    for i in range(N_QUERIES):
        ids = buscador.buscar_uma_filtrada(dados["queries"][i], K, p_max=P_MAX)
        assert len(ids) == K
        # Nenhum id fora do subconjunto filtrado (seletor < P_MAX ⇒ id < n_elegiveis).
        assert all(0 <= x < dados["n_elegiveis"] for x in ids), f"id fora do filtro: {ids}"
        ids_obtidos[i] = ids
    recall = recall_at_k(ids_obtidos, dados["gt_ids"], k=K)
    assert recall >= 0.8, f"recall@{K} sob filtro = {recall}"


# --------------------------------------------------------------------------- #
# pgvector
# --------------------------------------------------------------------------- #


@pytest.fixture
def pg_conn(env: dict[str, str]) -> Iterator[psycopg.Connection]:
    conn_str = (
        f"host={env['PG_HOST']} port={env['PG_PORT']} "
        f"dbname={env['PG_DATABASE']} user={env['PG_USER']} password={env['PG_PASSWORD']}"
    )
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
        yield conn


def test_pgvector_busca_filtrada(pg_conn: psycopg.Connection, dados: dict[str, Any]) -> None:
    nome = f"bench_b_{uuid.uuid4().hex[:8]}"
    try:
        seed_pgvector(
            vetores=dados["base"],
            metadata=dados["metadata"],
            conn=pg_conn,
            nome_tabela=nome,
        )
        _assertivas(PgvectorBuscador(conn=pg_conn, nome_tabela=nome), dados)
    finally:
        with pg_conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {nome}")
        pg_conn.commit()


# --------------------------------------------------------------------------- #
# Qdrant
# --------------------------------------------------------------------------- #


@pytest.fixture
def qdrant_client(env: dict[str, str]) -> Iterator[QdrantClient]:
    c = QdrantClient(host=env["QDRANT_HOST"], port=int(env["QDRANT_HTTP_PORT"]))
    yield c
    c.close()


def test_qdrant_busca_filtrada(qdrant_client: QdrantClient, dados: dict[str, Any]) -> None:
    nome = f"bench_b_{uuid.uuid4().hex[:8]}"
    try:
        seed_qdrant(
            vetores=dados["base"],
            metadata=dados["metadata"],
            client=qdrant_client,
            nome_colecao=nome,
        )
        _assertivas(QdrantBuscador(client=qdrant_client, nome_colecao=nome), dados)
    finally:
        qdrant_client.delete_collection(collection_name=nome)


# --------------------------------------------------------------------------- #
# Weaviate
# --------------------------------------------------------------------------- #


@pytest.fixture
def weaviate_client(env: dict[str, str]) -> Iterator[weaviate.WeaviateClient]:
    c = weaviate.connect_to_local(
        host=env["WEAVIATE_HOST"],
        port=int(env["WEAVIATE_PORT"]),
    )
    yield c
    c.close()


def test_weaviate_busca_filtrada(
    weaviate_client: weaviate.WeaviateClient, dados: dict[str, Any]
) -> None:
    nome = f"BenchB{uuid.uuid4().hex[:8]}"
    try:
        seed_weaviate(
            vetores=dados["base"],
            metadata=dados["metadata"],
            client=weaviate_client,
            nome_classe=nome,
        )
        _assertivas(WeaviateBuscador(client=weaviate_client, nome_classe=nome), dados)
    finally:
        weaviate_client.collections.delete(nome)
