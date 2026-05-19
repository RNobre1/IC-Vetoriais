"""Testes de `benchmarks.cenario_b` (TDD — escritos antes da implementação).

`cenario_b` orquestra a busca **com filtro de seletividade variável**. Mesma
estrutura do Cenário A (Protocol + medição testável sem Docker), mas:

- varre `seletividades × efSearch` (1 `ResultadoBenchmark` por combinação);
- usa `buscar_uma_filtrada(query, k, *, p_max)` (Protocol `BuscadorFiltravel`);
- recall@K contra o ground truth **filtrado por seletividade**
  (`gt_por_seletividade[p]`), não o GT global do Cenário A;
- `cenario == "B"`, `parametros["seletividade"]` registrado.

Decisões: [[../../vault/decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]].
"""

from __future__ import annotations

import numpy as np
import pytest

from benchmarks.cenario_b import medir_sistema_filtrado
from lib.reporting import ResultadoBenchmark

# ---------------------------------------------------------------------------
# Fake
# ---------------------------------------------------------------------------


class FakeBuscadorFiltravel:
    """Buscador filtrável determinístico.

    `perfeito=True`: devolve os ids do `gt_por_p[p_max]` da query corrente
    (recall = 1.0). `perfeito=False`: ids deslocados (recall = 0.0). Conta
    chamadas para validar warmup e registra os `ef` configurados na ordem.
    """

    def __init__(
        self,
        gt_por_p: dict[float, np.ndarray],
        *,
        nome: str = "fake",
        perfeito: bool = True,
    ) -> None:
        self.nome = nome
        self._gt = gt_por_p
        self._perfeito = perfeito
        self.efs_configurados: list[int] = []
        self.chamadas_busca = 0
        self._idx = 0

    def configurar_ef_search(self, ef: int) -> None:
        self.efs_configurados.append(ef)
        self._idx = 0

    def buscar_uma(self, query: np.ndarray, k: int) -> list[int]:  # contrato A
        del query
        raise AssertionError("Cenário B deve usar buscar_uma_filtrada.")

    def buscar_uma_filtrada(self, query: np.ndarray, k: int, *, p_max: float) -> list[int]:
        del query
        self.chamadas_busca += 1
        linha = self._gt[p_max][self._idx % len(self._gt[p_max])]
        self._idx += 1
        if self._perfeito:
            return list(linha[:k])
        return list(linha[:k] + 100_000)


@pytest.fixture
def queries() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.standard_normal((20, 8)).astype(np.float32)


@pytest.fixture
def seletividades() -> list[float]:
    return [0.01, 0.1, 1.0]


@pytest.fixture
def gt_por_p(seletividades: list[float]) -> dict[float, np.ndarray]:
    """1 ground truth (20 queries × 10 ids distintos) por seletividade."""
    rng = np.random.default_rng(7)
    return {
        p: np.array(
            [rng.choice(1000, size=10, replace=False) for _ in range(20)],
            dtype=np.int64,
        )
        for p in seletividades
    }


# ---------------------------------------------------------------------------
# Estrutura da saída
# ---------------------------------------------------------------------------


def test_um_resultado_por_combinacao_seletividade_ef(
    queries: np.ndarray, gt_por_p: dict[float, np.ndarray], seletividades: list[float]
) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p)
    resultados = medir_sistema_filtrado(
        buscador,
        queries=queries,
        gt_por_seletividade=gt_por_p,
        ef_search_values=[16, 64],
        seletividades=seletividades,
        k=10,
        n_base=100,
        timestamp_utc="2026-05-19T00-00-00Z",
    )
    assert len(resultados) == len(seletividades) * 2
    assert all(isinstance(r, ResultadoBenchmark) for r in resultados)
    assert all(r.cenario == "B" for r in resultados)


def test_varre_seletividade_externo_ef_interno(
    queries: np.ndarray, gt_por_p: dict[float, np.ndarray], seletividades: list[float]
) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p)
    resultados = medir_sistema_filtrado(
        buscador,
        queries=queries,
        gt_por_seletividade=gt_por_p,
        ef_search_values=[16, 64],
        seletividades=seletividades,
        k=10,
        n_base=100,
        timestamp_utc="2026-05-19T00-00-00Z",
    )
    combos = [(r.parametros["seletividade"], r.parametros["ef_search"]) for r in resultados]
    esperado = [(p, ef) for p in seletividades for ef in (16, 64)]
    assert combos == esperado
    assert buscador.efs_configurados == [16, 64] * len(seletividades)


def test_campos_fixos_do_resultado(queries: np.ndarray, gt_por_p: dict[float, np.ndarray]) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p, nome="qdrant")
    r = medir_sistema_filtrado(
        buscador,
        queries=queries,
        gt_por_seletividade=gt_por_p,
        ef_search_values=[32],
        seletividades=[0.1],
        k=10,
        n_base=54321,
        timestamp_utc="2026-05-19T12-00-00Z",
    )[0]
    assert r.cenario == "B"
    assert r.sistema == "qdrant"
    assert r.n == 54321
    assert r.timestamp_utc == "2026-05-19T12-00-00Z"
    assert r.parametros["k"] == 10
    assert r.parametros["ef_search"] == 32
    assert r.parametros["seletividade"] == 0.1
    assert "warmup" in r.parametros
    assert set(r.metricas) >= {"p50", "p95", "p99", "qps", "recall_at_k"}


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------


def test_warmup_descartado(
    queries: np.ndarray, gt_por_p: dict[float, np.ndarray], seletividades: list[float]
) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p)
    warmup = 5
    medir_sistema_filtrado(
        buscador,
        queries=queries,
        gt_por_seletividade=gt_por_p,
        ef_search_values=[16, 64],
        seletividades=seletividades,
        k=10,
        n_base=100,
        timestamp_utc="2026-05-19T00-00-00Z",
        warmup=warmup,
    )
    n_combos = len(seletividades) * 2
    assert buscador.chamadas_busca == n_combos * (warmup + len(queries))


# ---------------------------------------------------------------------------
# Recall
# ---------------------------------------------------------------------------


def test_recall_1_quando_perfeito(queries: np.ndarray, gt_por_p: dict[float, np.ndarray]) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p, perfeito=True)
    r = medir_sistema_filtrado(
        buscador,
        queries=queries,
        gt_por_seletividade=gt_por_p,
        ef_search_values=[64],
        seletividades=[0.1],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-19T00-00-00Z",
        warmup=0,
    )[0]
    assert r.metricas["recall_at_k"] == pytest.approx(1.0)


def test_recall_0_quando_erra_tudo(queries: np.ndarray, gt_por_p: dict[float, np.ndarray]) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p, perfeito=False)
    r = medir_sistema_filtrado(
        buscador,
        queries=queries,
        gt_por_seletividade=gt_por_p,
        ef_search_values=[64],
        seletividades=[0.1],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-19T00-00-00Z",
        warmup=0,
    )[0]
    assert r.metricas["recall_at_k"] == pytest.approx(0.0)


def test_recall_usa_gt_da_seletividade_corrente(
    queries: np.ndarray, gt_por_p: dict[float, np.ndarray], seletividades: list[float]
) -> None:
    # O fake só acerta se receber o gt da p corrente — prova que cada combo
    # mede contra `gt_por_seletividade[p]`, não um GT global.
    buscador = FakeBuscadorFiltravel(gt_por_p, perfeito=True)
    resultados = medir_sistema_filtrado(
        buscador,
        queries=queries,
        gt_por_seletividade=gt_por_p,
        ef_search_values=[32],
        seletividades=seletividades,
        k=10,
        n_base=100,
        timestamp_utc="2026-05-19T00-00-00Z",
        warmup=0,
    )
    assert all(r.metricas["recall_at_k"] == pytest.approx(1.0) for r in resultados)


def test_gt_clampado_menor_que_k_nao_quebra_recall(
    queries: np.ndarray,
) -> None:
    # Seletividade minúscula ⇒ subconjunto < k ⇒ gt com menos de k colunas.
    gt_clamp = {0.01: np.tile(np.arange(4, dtype=np.int64), (20, 1))}  # 4 < k=10
    buscador = FakeBuscadorFiltravel(gt_clamp, perfeito=True)
    r = medir_sistema_filtrado(
        buscador,
        queries=queries,
        gt_por_seletividade=gt_clamp,
        ef_search_values=[16],
        seletividades=[0.01],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-19T00-00-00Z",
        warmup=0,
    )[0]
    assert r.metricas["recall_at_k"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------


def test_metricas_float_plausiveis(queries: np.ndarray, gt_por_p: dict[float, np.ndarray]) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p)
    r = medir_sistema_filtrado(
        buscador,
        queries=queries,
        gt_por_seletividade=gt_por_p,
        ef_search_values=[32],
        seletividades=[0.1],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-19T00-00-00Z",
    )[0]
    for chave in ("p50", "p95", "p99", "qps", "recall_at_k"):
        assert isinstance(r.metricas[chave], float)
    assert r.metricas["p99"] >= r.metricas["p50"] >= 0.0
    assert r.metricas["qps"] > 0.0


# ---------------------------------------------------------------------------
# Validações de borda
# ---------------------------------------------------------------------------


def test_levanta_se_queries_vazias(gt_por_p: dict[float, np.ndarray]) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p)
    with pytest.raises(ValueError, match="quer"):
        medir_sistema_filtrado(
            buscador,
            queries=np.zeros((0, 8), dtype=np.float32),
            gt_por_seletividade=gt_por_p,
            ef_search_values=[16],
            seletividades=[0.1],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-19T00-00-00Z",
        )


def test_levanta_se_ef_vazio(queries: np.ndarray, gt_por_p: dict[float, np.ndarray]) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p)
    with pytest.raises(ValueError, match="ef_search"):
        medir_sistema_filtrado(
            buscador,
            queries=queries,
            gt_por_seletividade=gt_por_p,
            ef_search_values=[],
            seletividades=[0.1],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-19T00-00-00Z",
        )


def test_levanta_se_seletividades_vazio(
    queries: np.ndarray, gt_por_p: dict[float, np.ndarray]
) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p)
    with pytest.raises(ValueError, match="seletividade"):
        medir_sistema_filtrado(
            buscador,
            queries=queries,
            gt_por_seletividade=gt_por_p,
            ef_search_values=[16],
            seletividades=[],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-19T00-00-00Z",
        )


def test_levanta_se_warmup_negativo(queries: np.ndarray, gt_por_p: dict[float, np.ndarray]) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p)
    with pytest.raises(ValueError, match="warmup"):
        medir_sistema_filtrado(
            buscador,
            queries=queries,
            gt_por_seletividade=gt_por_p,
            ef_search_values=[16],
            seletividades=[0.1],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-19T00-00-00Z",
            warmup=-1,
        )


def test_levanta_se_falta_gt_para_uma_seletividade(
    queries: np.ndarray, gt_por_p: dict[float, np.ndarray]
) -> None:
    buscador = FakeBuscadorFiltravel(gt_por_p)
    with pytest.raises(ValueError, match="ground truth|seletividade"):
        medir_sistema_filtrado(
            buscador,
            queries=queries,
            gt_por_seletividade=gt_por_p,  # não tem a chave 0.5
            ef_search_values=[16],
            seletividades=[0.5],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-19T00-00-00Z",
        )


def test_levanta_se_num_queries_difere_do_gt(queries: np.ndarray) -> None:
    gt_curto = {0.1: np.zeros((5, 10), dtype=np.int64)}  # 5 != 20 queries
    buscador = FakeBuscadorFiltravel(gt_curto)
    with pytest.raises(ValueError, match="quer"):
        medir_sistema_filtrado(
            buscador,
            queries=queries,
            gt_por_seletividade=gt_curto,
            ef_search_values=[16],
            seletividades=[0.1],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-19T00-00-00Z",
        )
