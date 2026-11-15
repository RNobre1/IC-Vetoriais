"""Inserção concorrente do Cenário C, um adaptador por SGBD.

O produtor do Cenário C roda em outro processo, então o adaptador precisa
nascer lá: `FabricaInseridor` é *picklable* e, chamada no processo filho,
abre a própria conexão e devolve `(inserir_lote, fechar)`.

Cada `inserir_lote(ids, vetores)` só retorna quando o servidor confirma a
escrita, porque é essa confirmação que o consumidor usa para saber quais
vetores já existem: commit da transação no pgvector, `upsert` com
`wait=True` no Qdrant, `insert_many` síncrono no Weaviate. A durabilidade
dessas confirmações não é equalizada entre os sistemas (o commit do
PostgreSQL inclui `fsync` do WAL; os outros dois não garantem o mesmo), e
isso precisa acompanhar qualquer comparação de taxa sustentada.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

Inserir = Callable[[list[int], np.ndarray], None]


@dataclass(frozen=True)
class FabricaInseridor:
    """Abre a conexão do produtor no processo onde for chamada."""

    sistema: str
    nome_recurso: str
    env: dict[str, str] = field(default_factory=dict)

    def __call__(self) -> tuple[Inserir, Callable[[], None]]:
        if self.sistema == "pgvector":
            return _pgvector(self.nome_recurso, self.env)
        if self.sistema == "qdrant":
            return _qdrant(self.nome_recurso, self.env)
        if self.sistema == "weaviate":
            return _weaviate(self.nome_recurso, self.env)
        raise ValueError(f"sistema desconhecido: {self.sistema}")


def _pgvector(tabela: str, env: dict[str, str]) -> tuple[Inserir, Callable[[], None]]:
    import psycopg
    from pgvector.psycopg import register_vector

    conn = psycopg.connect(
        f"host={env['PG_HOST']} port={env['PG_PORT']} dbname={env['PG_DATABASE']} "
        f"user={env['PG_USER']} password={env['PG_PASSWORD']}"
    )
    register_vector(conn)

    def inserir(ids: list[int], vetores: np.ndarray) -> None:
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO {tabela} (id, embedding) VALUES (%s, %s)",
                list(zip(ids, vetores, strict=True)),
            )
        conn.commit()

    return inserir, conn.close


def _qdrant(colecao: str, env: dict[str, str]) -> tuple[Inserir, Callable[[], None]]:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import PointStruct

    client = QdrantClient(host=env["QDRANT_HOST"], port=int(env["QDRANT_HTTP_PORT"]), timeout=120)

    def inserir(ids: list[int], vetores: np.ndarray) -> None:
        client.upsert(
            collection_name=colecao,
            points=[
                PointStruct(id=int(i), vector=v.tolist()) for i, v in zip(ids, vetores, strict=True)
            ],
            wait=True,
        )

    return inserir, client.close


def _weaviate(classe: str, env: dict[str, str]) -> tuple[Inserir, Callable[[], None]]:
    import weaviate
    from weaviate.classes.data import DataObject

    client = weaviate.connect_to_local(host=env["WEAVIATE_HOST"], port=int(env["WEAVIATE_PORT"]))
    col = client.collections.get(classe)

    def inserir(ids: list[int], vetores: np.ndarray) -> None:
        resultado = col.data.insert_many(
            [
                DataObject(properties={"external_id": int(i)}, vector=v.tolist())
                for i, v in zip(ids, vetores, strict=True)
            ]
        )
        if resultado.has_errors:
            primeiro = next(iter(resultado.errors.values()))
            raise RuntimeError(f"Weaviate recusou {len(resultado.errors)} objeto(s): {primeiro}")

    return inserir, client.close


def contar(sistema: str, recurso: Any, nome_recurso: str) -> int:
    """Total de vetores na coleção — confere que toda inserção confirmada existe."""
    if sistema == "pgvector":
        with recurso.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {nome_recurso}")
            (n,) = cur.fetchone()
        recurso.commit()
        return int(n)
    if sistema == "qdrant":
        return int(recurso.count(collection_name=nome_recurso, exact=True).count)
    if sistema == "weaviate":
        col = recurso.collections.get(nome_recurso)
        return int(col.aggregate.over_all(total_count=True).total_count)
    raise ValueError(f"sistema desconhecido: {sistema}")
