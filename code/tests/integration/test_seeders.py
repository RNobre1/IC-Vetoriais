"""Testes de integração dos 3 seeders (pgvector, Qdrant, Weaviate).

Cada seeder expõe `seed_X(*, vetores, metadata, <cliente>, nome, M, ef_construction)`
e devolve a contagem de itens efetivamente inseridos. Validamos:

1. **Count**: 1000 vetores entram, 1000 saem.
2. **Sanity de busca**: dado um vetor `v` que foi inserido com id `k`, a busca
   por similaridade do top-1 com `query=v` retorna `id=k`.

Os testes são marcados `integration` e exigem `make up` antes de rodar.
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

from seeders.pgvector_seeder import seed_pgvector
from seeders.qdrant_seeder import seed_qdrant
from seeders.weaviate_seeder import seed_weaviate

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures comuns
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def env() -> dict[str, str]:
    load_dotenv()
    return dict(os.environ)


@pytest.fixture(scope="module")
def vetores_1k() -> np.ndarray:
    """1000 vetores 384-D normalizados L2, gerados com seed fixo (42)."""
    rng = np.random.default_rng(42)
    arr = rng.normal(size=(1000, 384)).astype(np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    return arr


@pytest.fixture(scope="module")
def metadata_1k() -> list[dict[str, Any]]:
    """Metadata sintético: 50% cat-A, 50% cat-B (preparando Cenário B)."""
    return [{"categoria": "cat-A" if i % 2 == 0 else "cat-B"} for i in range(1000)]


# ---------------------------------------------------------------------------
# pgvector
# ---------------------------------------------------------------------------


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


def test_pgvector_seed_count(
    pg_conn: psycopg.Connection,
    vetores_1k: np.ndarray,
    metadata_1k: list[dict[str, Any]],
) -> None:
    nome = f"seed_test_{uuid.uuid4().hex[:8]}"
    try:
        n = seed_pgvector(
            vetores=vetores_1k,
            metadata=metadata_1k,
            conn=pg_conn,
            nome_tabela=nome,
            m=16,
            ef_construction=200,
        )
        assert n == 1000
        with pg_conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {nome}")
            assert cur.fetchone()[0] == 1000
    finally:
        with pg_conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {nome}")
        pg_conn.commit()


def test_pgvector_busca_recupera_id_inserido(
    pg_conn: psycopg.Connection,
    vetores_1k: np.ndarray,
    metadata_1k: list[dict[str, Any]],
) -> None:
    nome = f"seed_busca_{uuid.uuid4().hex[:8]}"
    try:
        seed_pgvector(
            vetores=vetores_1k,
            metadata=metadata_1k,
            conn=pg_conn,
            nome_tabela=nome,
        )
        # Busca top-1 do vetor 0 deve retornar id 0.
        v0 = "[" + ",".join(f"{x:.8f}" for x in vetores_1k[0]) + "]"
        with pg_conn.cursor() as cur:
            cur.execute(f"SELECT id FROM {nome} ORDER BY embedding <=> %s LIMIT 1", (v0,))
            assert cur.fetchone()[0] == 0
    finally:
        with pg_conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {nome}")
        pg_conn.commit()


# ---------------------------------------------------------------------------
# Qdrant
# ---------------------------------------------------------------------------


@pytest.fixture
def qdrant_client(env: dict[str, str]) -> Iterator[QdrantClient]:
    c = QdrantClient(host=env["QDRANT_HOST"], port=int(env["QDRANT_HTTP_PORT"]))
    yield c
    c.close()


def test_qdrant_seed_count(
    qdrant_client: QdrantClient,
    vetores_1k: np.ndarray,
    metadata_1k: list[dict[str, Any]],
) -> None:
    nome = f"seed_test_{uuid.uuid4().hex[:8]}"
    try:
        n = seed_qdrant(
            vetores=vetores_1k,
            metadata=metadata_1k,
            client=qdrant_client,
            nome_colecao=nome,
            m=16,
            ef_construction=200,
        )
        assert n == 1000
        info = qdrant_client.get_collection(collection_name=nome)
        assert info.points_count == 1000
    finally:
        qdrant_client.delete_collection(collection_name=nome)


def test_qdrant_busca_recupera_id_inserido(
    qdrant_client: QdrantClient,
    vetores_1k: np.ndarray,
    metadata_1k: list[dict[str, Any]],
) -> None:
    nome = f"seed_busca_{uuid.uuid4().hex[:8]}"
    try:
        seed_qdrant(
            vetores=vetores_1k,
            metadata=metadata_1k,
            client=qdrant_client,
            nome_colecao=nome,
        )
        resposta = qdrant_client.query_points(
            collection_name=nome,
            query=vetores_1k[0].tolist(),
            limit=1,
        )
        assert resposta.points[0].id == 0
    finally:
        qdrant_client.delete_collection(collection_name=nome)


# ---------------------------------------------------------------------------
# Weaviate
# ---------------------------------------------------------------------------


@pytest.fixture
def weaviate_client(env: dict[str, str]) -> Iterator[weaviate.WeaviateClient]:
    c = weaviate.connect_to_local(
        host=env["WEAVIATE_HOST"],
        port=int(env["WEAVIATE_PORT"]),
    )
    yield c
    c.close()


def test_weaviate_seed_count(
    weaviate_client: weaviate.WeaviateClient,
    vetores_1k: np.ndarray,
    metadata_1k: list[dict[str, Any]],
) -> None:
    nome = f"SeedTest{uuid.uuid4().hex[:8]}"
    try:
        n = seed_weaviate(
            vetores=vetores_1k,
            metadata=metadata_1k,
            client=weaviate_client,
            nome_classe=nome,
            m=16,
            ef_construction=200,
        )
        assert n == 1000
        col = weaviate_client.collections.get(nome)
        agg = col.aggregate.over_all(total_count=True)
        assert agg.total_count == 1000
    finally:
        weaviate_client.collections.delete(nome)


def test_weaviate_busca_recupera_id_inserido(
    weaviate_client: weaviate.WeaviateClient,
    vetores_1k: np.ndarray,
    metadata_1k: list[dict[str, Any]],
) -> None:
    nome = f"SeedBusca{uuid.uuid4().hex[:8]}"
    try:
        seed_weaviate(
            vetores=vetores_1k,
            metadata=metadata_1k,
            client=weaviate_client,
            nome_classe=nome,
        )
        col = weaviate_client.collections.get(nome)
        resultado = col.query.near_vector(near_vector=vetores_1k[0].tolist(), limit=1)
        assert resultado.objects[0].properties["external_id"] == 0
    finally:
        weaviate_client.collections.delete(nome)
