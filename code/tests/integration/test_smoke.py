"""Smoke test integrado — valida que os 3 SGBDs estão respondendo e aceitam operação básica.

Requer:
    make up

Cobre, para cada um dos 3 sistemas:
- conexão de rede;
- operação mínima de criação (extension/collection/class);
- inserção de 1 vetor;
- busca por similaridade do mesmo vetor (sanity).

Importante: este é o smoke do Dia 1 da Etapa 2, anterior aos seeders proprios.
Implementa diretamente os clientes para isolar problemas de infraestrutura.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def env() -> dict[str, str]:
    """Carrega variáveis de .env (se existir) e retorna os.environ como dict."""
    from dotenv import load_dotenv

    load_dotenv()
    return dict(os.environ)


@pytest.fixture(scope="module")
def vetor_teste() -> list[float]:
    """Vetor sintético de dimensão 384 (compatível com all-MiniLM-L6-v2)."""
    # 384 floats determinísticos, normalizados aproximadamente.
    import math

    raw = [math.sin(i * 0.1) for i in range(384)]
    norma = math.sqrt(sum(x * x for x in raw))
    return [x / norma for x in raw]


# ---------------------------------------------------------------------------
# pgvector
# ---------------------------------------------------------------------------


def test_pgvector_conexao_e_extensao(env: dict[str, str]) -> None:
    """pgvector responde TCP, aceita SELECT 1 e a extensão `vector` está disponível."""
    import psycopg

    conn_str = (
        f"host={env['PG_HOST']} port={env['PG_PORT']} "
        f"dbname={env['PG_DATABASE']} user={env['PG_USER']} password={env['PG_PASSWORD']}"
    )
    with psycopg.connect(conn_str) as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1

        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        assert cur.fetchone() is not None


def test_pgvector_insert_e_busca(env: dict[str, str], vetor_teste: list[float]) -> None:
    """pgvector aceita criar tabela com coluna vector(384), inserir e buscar por similaridade."""
    import psycopg

    conn_str = (
        f"host={env['PG_HOST']} port={env['PG_PORT']} "
        f"dbname={env['PG_DATABASE']} user={env['PG_USER']} password={env['PG_PASSWORD']}"
    )
    nome_tabela = f"smoke_{uuid.uuid4().hex[:8]}"
    vetor_literal = "[" + ",".join(f"{x:.8f}" for x in vetor_teste) + "]"

    with psycopg.connect(conn_str) as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute(f"CREATE TABLE {nome_tabela} (id int primary key, embedding vector(384))")
        cur.execute(f"INSERT INTO {nome_tabela} (id, embedding) VALUES (1, %s)", (vetor_literal,))
        cur.execute(
            f"SELECT id FROM {nome_tabela} ORDER BY embedding <=> %s LIMIT 1",
            (vetor_literal,),
        )
        assert cur.fetchone()[0] == 1
        cur.execute(f"DROP TABLE {nome_tabela}")
        conn.commit()


# ---------------------------------------------------------------------------
# Qdrant
# ---------------------------------------------------------------------------


def test_qdrant_responde_http(env: dict[str, str]) -> None:
    """Qdrant aceita conexão HTTP no endpoint raiz (versão)."""
    url = f"http://{env['QDRANT_HOST']}:{env['QDRANT_HTTP_PORT']}/"
    r = httpx.get(url, timeout=5.0)
    assert r.status_code == 200
    body = r.json()
    assert "version" in body or "title" in body  # contrato pode variar entre versões


def test_qdrant_collection_insert_e_busca(env: dict[str, str], vetor_teste: list[float]) -> None:
    """Qdrant cria coleção HNSW, aceita upsert e busca o vetor inserido como mais próximo de si mesmo."""
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        Distance,
        PointStruct,
        VectorParams,
    )

    client = QdrantClient(
        host=env["QDRANT_HOST"],
        port=int(env["QDRANT_HTTP_PORT"]),
    )
    nome_colecao = f"smoke_{uuid.uuid4().hex[:8]}"

    try:
        client.create_collection(
            collection_name=nome_colecao,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        client.upsert(
            collection_name=nome_colecao,
            points=[PointStruct(id=1, vector=vetor_teste)],
        )
        resultados = client.search(
            collection_name=nome_colecao,
            query_vector=vetor_teste,
            limit=1,
        )
        assert len(resultados) == 1
        assert resultados[0].id == 1
    finally:
        client.delete_collection(collection_name=nome_colecao)


# ---------------------------------------------------------------------------
# Weaviate
# ---------------------------------------------------------------------------


def test_weaviate_ready(env: dict[str, str]) -> None:
    """Weaviate sinaliza readiness no endpoint padrão."""
    url = f"http://{env['WEAVIATE_HOST']}:{env['WEAVIATE_PORT']}/v1/.well-known/ready"
    r = httpx.get(url, timeout=5.0)
    assert r.status_code == 200


def test_weaviate_collection_insert_e_busca(env: dict[str, str], vetor_teste: list[float]) -> None:
    """Weaviate cria classe sem vectorizer, aceita objeto com vetor manual e busca near_vector."""
    import weaviate
    from weaviate.classes.config import Configure, Property, DataType

    client = weaviate.connect_to_local(
        host=env["WEAVIATE_HOST"],
        port=int(env["WEAVIATE_PORT"]),
    )
    nome_classe = f"Smoke{uuid.uuid4().hex[:8]}"

    try:
        client.collections.create(
            name=nome_classe,
            vectorizer_config=Configure.Vectorizer.none(),
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=weaviate.classes.config.VectorDistances.COSINE,
            ),
            properties=[
                Property(name="external_id", data_type=DataType.INT),
            ],
        )
        colecao = client.collections.get(nome_classe)
        colecao.data.insert(
            properties={"external_id": 1},
            vector=vetor_teste,
        )
        resultado = colecao.query.near_vector(near_vector=vetor_teste, limit=1)
        assert len(resultado.objects) == 1
        assert resultado.objects[0].properties["external_id"] == 1
    finally:
        client.collections.delete(nome_classe)
        client.close()
