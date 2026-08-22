"""Testes da garantia de indexação concluída no seeder do Weaviate.

Mesma família do defeito já corrigido em `test_qdrant_indexacao.py`. O
`batch.fixed_size(...)` retorna quando os objetos foram **aceitos**, não quando
o HNSW terminou de indexá-los: o Weaviate enfileira os vetores e constrói o
grafo em background. Ao sair do bloco `with`, o seeder pode devolver o controle
com a fila ainda cheia — e quem medir latência ou recall nesse instante mede um
índice pela metade, com números plausíveis e errados.

A correção pertence ao seeder, não a cada chamador: quem semeia é quem sabe que
a escrita foi assíncrona (Regra 2-A — fonte única). É também a condição para
medir tempo de indexação de forma justa contra o pgvector, cujo
`CREATE INDEX` é bloqueante.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from seeders.weaviate_seeder import seed_weaviate


@pytest.fixture
def vetores() -> np.ndarray:
    rng = np.random.default_rng(11)
    arr = rng.normal(size=(4, 4)).astype(np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    return arr


class _Batch:
    def __enter__(self) -> _Batch:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def add_object(self, **kwargs: Any) -> None:
        pass


class _BatchFactory:
    def fixed_size(self, **kwargs: Any) -> _Batch:
        return _Batch()


class _Collection:
    def __init__(self) -> None:
        self.batch = _BatchFactory()


class _Collections:
    def create(self, **kwargs: Any) -> None:
        pass

    def get(self, nome: str) -> _Collection:
        return _Collection()


class _Shard:
    def __init__(self, collection: str, fila: int, status: str) -> None:
        self.collection = collection
        self.vector_queue_length = fila
        self.vector_indexing_status = status


class _Node:
    def __init__(self, shards: list[_Shard]) -> None:
        self.shards = shards


class _Cluster:
    """Devolve fila cheia nas primeiras consultas e drenada a partir da N-ésima."""

    def __init__(self, viradas: int, classe: str = "C") -> None:
        self.viradas = viradas
        self.classe = classe
        self.chamadas = 0

    def nodes(self, collection: str | None = None, *, output: str | None = None) -> list[_Node]:
        self.chamadas += 1
        drenou = self.chamadas > self.viradas
        return [
            _Node(
                [
                    _Shard(
                        self.classe,
                        fila=0 if drenou else 4_000,
                        status="READY" if drenou else "INDEXING",
                    )
                ]
            )
        ]


class FakeWeaviateComFila:
    def __init__(self, viradas: int = 2, classe: str = "C") -> None:
        self.collections = _Collections()
        self.cluster = _Cluster(viradas, classe)


@pytest.fixture(autouse=True)
def _sem_dormir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lib.footprint.time.sleep", lambda _s: None)


def test_seed_aguarda_a_fila_de_indexacao_drenar(vetores) -> None:
    """O seeder só retorna depois que o shard da classe fica `READY`."""
    client = FakeWeaviateComFila(viradas=3)

    seed_weaviate(vetores=vetores, metadata=None, client=client, nome_classe="C")

    assert client.cluster.chamadas == 4, "deveria consultar até a fila drenar"


def test_seed_sem_espera_quando_desligado(vetores) -> None:
    """`aguardar_indexacao=False` preserva o comportamento assíncrono puro."""
    client = FakeWeaviateComFila(viradas=3)

    seed_weaviate(
        vetores=vetores,
        metadata=None,
        client=client,
        nome_classe="C",
        aguardar_indexacao=False,
    )

    assert client.cluster.chamadas == 0


def test_seed_desiste_apos_limite_de_tentativas(vetores) -> None:
    """Fila que nunca drena não pode travar a suíte para sempre."""
    client = FakeWeaviateComFila(viradas=10**9)

    with pytest.raises(TimeoutError, match="fila"):
        seed_weaviate(
            vetores=vetores,
            metadata=None,
            client=client,
            nome_classe="C",
            tentativas_indexacao=5,
        )

    assert client.cluster.chamadas == 5


def test_seed_retorna_contagem_apos_espera(vetores) -> None:
    """A espera não pode alterar o contrato de retorno (N inserido)."""
    client = FakeWeaviateComFila(viradas=1)

    assert seed_weaviate(vetores=vetores, metadata=None, client=client, nome_classe="C") == 4
