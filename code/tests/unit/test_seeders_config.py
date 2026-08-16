"""Testes unitários da configuração de busca filtrada nos seeders.

Contexto (auditoria de 2026-08-16): os resultados do Cenário B mostraram
`recall = 1,0000` constante em todos os `ef_search` para Qdrant e Weaviate nas
seletividades baixas. Isso não é qualidade de ANN filtrado — é o *fallback*
documentado para **busca exata** quando o subconjunto elegível é pequeno:

- Weaviate: `flatSearchCutoff` (default **40000** objetos). A doc oficial diz
  "To force a vector index search, set `flatSearchCutoff: 0`".
- Qdrant: `full_scan_threshold` (default **10000 KB**). Abaixo do limiar o
  *query planner* prefere varredura completa a percorrer o HNSW.

Para que o Cenário B compare de fato *busca aproximada com filtro* nos três
sistemas, os seeders precisam expor esses limiares. Estes testes usam dublês que
capturam os kwargs efetivamente passados aos clientes — sem Docker.

Vide `vault/decisões/2026-08-16-equalizacao-cenario-b.md`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from seeders.pgvector_seeder import seed_pgvector
from seeders.qdrant_seeder import FULL_SCAN_MINIMO, seed_qdrant
from seeders.weaviate_seeder import seed_weaviate


@pytest.fixture(autouse=True)
def _sem_register_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    """`register_vector` exige conexão psycopg real; irrelevante para estes testes."""
    monkeypatch.setattr(
        "seeders.pgvector_seeder.register_vector", lambda conn: None
    )


@pytest.fixture
def vetores() -> np.ndarray:
    rng = np.random.default_rng(42)
    arr = rng.normal(size=(8, 4)).astype(np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    return arr


@pytest.fixture
def metadata_seletor() -> list[dict[str, Any]]:
    return [{"seletor": i / 8.0} for i in range(8)]


# ---------------------------------------------------------------------------
# Dublês
# ---------------------------------------------------------------------------


class _InfoColecao:
    status = "green"


class FakeQdrant:
    """Captura os kwargs de `create_collection` e engole o resto.

    `get_collection` responde `green` de imediato: a espera pela indexação tem
    testes próprios em `test_qdrant_indexacao.py`.
    """

    def __init__(self) -> None:
        self.create_kwargs: dict[str, Any] = {}
        self.payload_index_kwargs: dict[str, Any] = {}

    def create_collection(self, **kwargs: Any) -> None:
        self.create_kwargs = kwargs

    def create_payload_index(self, **kwargs: Any) -> None:
        self.payload_index_kwargs = kwargs

    def upsert(self, **kwargs: Any) -> None:
        pass

    def get_collection(self, nome: str) -> _InfoColecao:
        return _InfoColecao()


class _FakeBatch:
    def __enter__(self) -> _FakeBatch:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def add_object(self, **kwargs: Any) -> None:
        pass


class _FakeBatchFactory:
    def fixed_size(self, **kwargs: Any) -> _FakeBatch:
        return _FakeBatch()


class _FakeCollection:
    def __init__(self) -> None:
        self.batch = _FakeBatchFactory()


class _FakeCollections:
    def __init__(self) -> None:
        self.create_kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> None:
        self.create_kwargs = kwargs

    def get(self, nome: str) -> _FakeCollection:
        return _FakeCollection()


class FakeWeaviate:
    def __init__(self) -> None:
        self.collections = _FakeCollections()


class _FakeCursor:
    def __init__(self, sql: list[str]) -> None:
        self._sql = sql

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, query: str, params: Any = None) -> None:
        self._sql.append(query)

    def executemany(self, query: str, params: Any = None) -> None:
        self._sql.append(query)

    def copy(self, query: str) -> _FakeCursor:
        self._sql.append(query)
        return self

    def write_row(self, row: Any) -> None:
        pass


class FakePg:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.sql)

    def commit(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Qdrant — full_scan_threshold
# ---------------------------------------------------------------------------


def test_qdrant_sem_full_scan_threshold_preserva_comportamento(vetores):
    """Default (None) não deve tocar em `full_scan_threshold` — regressão."""
    client = FakeQdrant()
    seed_qdrant(
        vetores=vetores, metadata=None, client=client, nome_colecao="c",
    )
    hnsw = client.create_kwargs["hnsw_config"]
    assert hnsw.full_scan_threshold is None


def test_qdrant_full_scan_threshold_minimo_forca_hnsw(vetores):
    """`FULL_SCAN_MINIMO` ⇒ nenhum subconjunto de interesse é 'pequeno'."""
    client = FakeQdrant()
    seed_qdrant(
        vetores=vetores, metadata=None, client=client, nome_colecao="c",
        full_scan_threshold=FULL_SCAN_MINIMO,
    )
    hnsw = client.create_kwargs["hnsw_config"]
    assert hnsw.full_scan_threshold == FULL_SCAN_MINIMO


def test_qdrant_minimo_respeita_limite_do_servidor():
    """O servidor rejeita 0 com HTTP 422: 'must be 10 or larger'.

    Regressão de campo: a primeira contraprova (2026-08-16) morreu exatamente
    aqui, ao copiar do Weaviate a receita `cutoff = 0`.
    """
    assert FULL_SCAN_MINIMO >= 10


def test_qdrant_preserva_m_e_ef_construction_com_threshold(vetores):
    """O limiar não pode atropelar os parâmetros de construção do grafo."""
    client = FakeQdrant()
    seed_qdrant(
        vetores=vetores, metadata=None, client=client, nome_colecao="c",
        m=16, ef_construction=200, full_scan_threshold=0,
    )
    hnsw = client.create_kwargs["hnsw_config"]
    assert (hnsw.m, hnsw.ef_construct) == (16, 200)


# ---------------------------------------------------------------------------
# Weaviate — flat_search_cutoff / filter_strategy
# ---------------------------------------------------------------------------


def test_weaviate_sem_cutoff_preserva_comportamento(vetores):
    """Default (None) mantém o `flatSearchCutoff` padrão do servidor (40000)."""
    client = FakeWeaviate()
    seed_weaviate(
        vetores=vetores, metadata=None, client=client, nome_classe="C",
    )
    cfg = client.collections.create_kwargs["vector_config"]
    assert cfg.vectorIndexConfig.flatSearchCutoff is None


def test_weaviate_cutoff_zero_forca_indice_vetorial(vetores):
    """`flat_search_cutoff=0` ⇒ nunca cai em busca exata (doc oficial)."""
    client = FakeWeaviate()
    seed_weaviate(
        vetores=vetores, metadata=None, client=client, nome_classe="C",
        flat_search_cutoff=0,
    )
    cfg = client.collections.create_kwargs["vector_config"]
    assert cfg.vectorIndexConfig.flatSearchCutoff == 0


def test_weaviate_filter_strategy_explicito(vetores):
    """A estratégia de filtro precisa ser registrável (ACORN é default em 1.34+)."""
    client = FakeWeaviate()
    seed_weaviate(
        vetores=vetores, metadata=None, client=client, nome_classe="C",
        filter_strategy="acorn",
    )
    cfg = client.collections.create_kwargs["vector_config"]
    assert cfg.vectorIndexConfig.filterStrategy is not None


# ---------------------------------------------------------------------------
# pgvector — índice no atributo de filtro
# ---------------------------------------------------------------------------


def test_pgvector_sem_indice_seletor_preserva_comportamento(
    vetores, metadata_seletor
):
    """Default: nenhum índice em `seletor` — reproduz o que rodou em julho."""
    conn = FakePg()
    seed_pgvector(
        vetores=vetores, metadata=metadata_seletor, conn=conn, nome_tabela="t",
    )
    assert not any("USING btree (seletor)" in s for s in conn.sql)


def test_pgvector_indexar_seletor_emite_btree(vetores, metadata_seletor):
    """`indexar_seletor=True` ⇒ B-tree no atributo de filtro (equalização)."""
    conn = FakePg()
    seed_pgvector(
        vetores=vetores, metadata=metadata_seletor, conn=conn, nome_tabela="t",
        indexar_seletor=True,
    )
    assert any("USING btree (seletor)" in s for s in conn.sql)


def test_pgvector_indice_seletor_ignorado_sem_metadata(vetores):
    """Cenário A (metadata=None) não deve criar índice de filtro."""
    conn = FakePg()
    seed_pgvector(
        vetores=vetores, metadata=None, conn=conn, nome_tabela="t",
        indexar_seletor=True,
    )
    assert not any("USING btree (seletor)" in s for s in conn.sql)
