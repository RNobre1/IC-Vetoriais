"""Testes da garantia de indexação concluída no seeder do Qdrant.

Contexto (auditoria de 2026-08-16). Em julho/2026 o `qdrant_seeder` trocou
`upsert(wait=True)` por `wait=False` para destravar o *timeout* na carga de
500k. A troca resolveu a lentidão mas removeu uma garantia: ao retornar, o
seeder não assegura mais que o HNSW terminou de ser construído.

A espera pelo status `green` foi implementada apenas nos scripts avulsos da
Etapa 3 (`run_etapa3.py`), **não** no caminho canônico usado por `make bench-A`
e `make bench-B`. Consequência: uma execução pelo CLI pode medir latência e
recall sobre um índice ainda em construção — e falha em silêncio, produzindo
números plausíveis porém errados.

A correção pertence ao seeder, não a cada chamador: quem semeia é quem sabe que
o upsert foi assíncrono (Regra 2-A — fonte única).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from seeders.qdrant_seeder import seed_qdrant


@pytest.fixture
def vetores() -> np.ndarray:
    rng = np.random.default_rng(7)
    arr = rng.normal(size=(4, 4)).astype(np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    return arr


class _Info:
    def __init__(self, status: str) -> None:
        self.status = status


class FakeQdrantComStatus:
    """Devolve `yellow` nas primeiras chamadas e `green` a partir da N-ésima."""

    def __init__(self, viradas: int = 2) -> None:
        self.viradas = viradas
        self.chamadas_get = 0
        self.esperas: list[float] = []

    def create_collection(self, **kwargs: Any) -> None:
        pass

    def create_payload_index(self, **kwargs: Any) -> None:
        pass

    def upsert(self, **kwargs: Any) -> None:
        pass

    def get_collection(self, nome: str) -> _Info:
        self.chamadas_get += 1
        return _Info("green" if self.chamadas_get > self.viradas else "yellow")


def test_seed_aguarda_status_green(vetores, monkeypatch):
    """O seeder só retorna depois que a coleção sai de `yellow`."""
    monkeypatch.setattr("seeders.qdrant_seeder.time.sleep", lambda s: None)
    client = FakeQdrantComStatus(viradas=3)

    seed_qdrant(vetores=vetores, metadata=None, client=client, nome_colecao="c")

    assert client.chamadas_get == 4, "deveria consultar até obter green"


def test_seed_sem_espera_quando_desligado(vetores, monkeypatch):
    """`aguardar_indexacao=False` preserva o comportamento assíncrono puro."""
    monkeypatch.setattr("seeders.qdrant_seeder.time.sleep", lambda s: None)
    client = FakeQdrantComStatus(viradas=3)

    seed_qdrant(
        vetores=vetores, metadata=None, client=client, nome_colecao="c",
        aguardar_indexacao=False,
    )

    assert client.chamadas_get == 0


def test_seed_desiste_apos_limite_de_tentativas(vetores, monkeypatch):
    """Índice que nunca fica verde não pode travar a suíte para sempre."""
    monkeypatch.setattr("seeders.qdrant_seeder.time.sleep", lambda s: None)
    client = FakeQdrantComStatus(viradas=10**9)

    with pytest.raises(TimeoutError, match="green"):
        seed_qdrant(
            vetores=vetores, metadata=None, client=client, nome_colecao="c",
            tentativas_indexacao=5,
        )

    assert client.chamadas_get == 5


def test_seed_retorna_contagem_apos_espera(vetores, monkeypatch):
    """A espera não pode alterar o contrato de retorno (N inserido)."""
    monkeypatch.setattr("seeders.qdrant_seeder.time.sleep", lambda s: None)
    client = FakeQdrantComStatus(viradas=1)

    assert (
        seed_qdrant(vetores=vetores, metadata=None, client=client, nome_colecao="c")
        == 4
    )
