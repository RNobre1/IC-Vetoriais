"""Smoke de integração dos adaptadores `BuscadorVetorial` (Cenário A ponta-a-ponta).

Para cada SGBD: seeda uma base pequena, gera queries held-out (vetores fora do
seed, conforme ADR [[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]]),
calcula o ground truth exato com FAISS e roda `medir_sistema` com o adaptador
REAL sobre um sweep curto de `efSearch`.

Valida o contrato ponta-a-ponta: o adaptador implementa o Protocol, a busca
recupera ids consistentes com o seed (0..N-1), e o recall sobe (ou se mantém
alto) quando `efSearch` cresce.

Marcado `integration` — exige `make up` (3 SGBDs healthy).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

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
from benchmarks.cenario_a import medir_sistema
from ground_truth.exact_search import top_k_exato
from seeders.pgvector_seeder import seed_pgvector
from seeders.qdrant_seeder import seed_qdrant
from seeders.weaviate_seeder import seed_weaviate

pytestmark = pytest.mark.integration

K = 10
EF_SWEEP = [16, 64]
N_BASE = 300
N_QUERIES = 20


# ---------------------------------------------------------------------------
# Dados: base seedada + queries held-out + ground truth exato
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def env() -> dict[str, str]:
    load_dotenv()
    return dict(os.environ)


@pytest.fixture(scope="module")
def dados() -> dict[str, np.ndarray]:
    """`base` (N_BASE seedados) + `queries` (N_QUERIES held-out) + `gt_ids` exato."""
    rng = np.random.default_rng(42)
    total = rng.normal(size=(N_BASE + N_QUERIES, 384)).astype(np.float32)
    total /= np.linalg.norm(total, axis=1, keepdims=True)
    base = total[:N_BASE]
    queries = total[N_BASE:]
    _, gt_ids = top_k_exato(base, queries, k=K)
    return {"base": base, "queries": queries, "gt_ids": gt_ids}


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


def test_pgvector_buscador_ponta_a_ponta(
    pg_conn: psycopg.Connection, dados: dict[str, np.ndarray]
) -> None:
    nome = f"bench_a_{uuid.uuid4().hex[:8]}"
    try:
        seed_pgvector(vetores=dados["base"], metadata=None, conn=pg_conn, nome_tabela=nome)
        buscador = PgvectorBuscador(conn=pg_conn, nome_tabela=nome)
        resultados = medir_sistema(
            buscador,
            queries=dados["queries"],
            gt_ids=dados["gt_ids"],
            ef_search_values=EF_SWEEP,
            k=K,
            n_base=N_BASE,
            timestamp_utc="2026-05-10T00-00-00Z",
            warmup=2,
        )
        _assertivas_comuns(resultados, sistema="pgvector")
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


def test_qdrant_buscador_ponta_a_ponta(
    qdrant_client: QdrantClient, dados: dict[str, np.ndarray]
) -> None:
    nome = f"bench_a_{uuid.uuid4().hex[:8]}"
    try:
        seed_qdrant(
            vetores=dados["base"],
            metadata=None,
            client=qdrant_client,
            nome_colecao=nome,
        )
        buscador = QdrantBuscador(client=qdrant_client, nome_colecao=nome)
        resultados = medir_sistema(
            buscador,
            queries=dados["queries"],
            gt_ids=dados["gt_ids"],
            ef_search_values=EF_SWEEP,
            k=K,
            n_base=N_BASE,
            timestamp_utc="2026-05-10T00-00-00Z",
            warmup=2,
        )
        _assertivas_comuns(resultados, sistema="qdrant")
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


def test_weaviate_buscador_ponta_a_ponta(
    weaviate_client: weaviate.WeaviateClient, dados: dict[str, np.ndarray]
) -> None:
    nome = f"BenchA{uuid.uuid4().hex[:8]}"  # Weaviate exige classe iniciando em maiúscula
    try:
        seed_weaviate(
            vetores=dados["base"],
            metadata=None,
            client=weaviate_client,
            nome_classe=nome,
        )
        buscador = WeaviateBuscador(client=weaviate_client, nome_classe=nome)
        resultados = medir_sistema(
            buscador,
            queries=dados["queries"],
            gt_ids=dados["gt_ids"],
            ef_search_values=EF_SWEEP,
            k=K,
            n_base=N_BASE,
            timestamp_utc="2026-05-10T00-00-00Z",
            warmup=2,
        )
        _assertivas_comuns(resultados, sistema="weaviate")
    finally:
        weaviate_client.collections.delete(nome)


# ---------------------------------------------------------------------------
# Assertivas comuns
# ---------------------------------------------------------------------------


def _assertivas_comuns(resultados: list, *, sistema: str) -> None:
    assert len(resultados) == len(EF_SWEEP)
    for r, ef in zip(resultados, EF_SWEEP, strict=True):
        assert r.sistema == sistema
        assert r.cenario == "A"
        assert r.n == N_BASE
        assert r.parametros["ef_search"] == ef
        assert r.parametros["k"] == K
        assert r.metricas["qps"] > 0.0
        assert 0.0 <= r.metricas["recall_at_k"] <= 1.0
    # Numa base de 300, HNSW com ef=64 deve recuperar quase tudo.
    recall_alto = resultados[-1].metricas["recall_at_k"]
    assert recall_alto >= 0.8, f"{sistema}: recall@{K} com ef={EF_SWEEP[-1]} = {recall_alto}"
    # ef maior não pode piorar o recall de forma significativa.
    assert resultados[-1].metricas["recall_at_k"] >= resultados[0].metricas["recall_at_k"] - 0.05
