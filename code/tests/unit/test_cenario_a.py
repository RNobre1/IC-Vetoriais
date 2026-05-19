"""Testes de `benchmarks.cenario_a` (TDD — escritos antes da implementação).

`cenario_a` orquestra a busca pura. Para ser testável sem Docker, a lógica
de medição opera sobre o Protocol `BuscadorVetorial` (um adaptador por SGBD,
testados em integração à parte). Aqui injetamos um `FakeBuscador`
determinístico e verificamos:

- um `ResultadoBenchmark` por valor de `efSearch`;
- `configurar_ef_search` chamado com cada valor, na ordem;
- warmup descartado (não entra nas métricas);
- recall@K calculado contra o ground truth;
- bloco de parâmetros/métricas/ambiente preenchido conforme a ADR
  [[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]].
"""

from __future__ import annotations

import numpy as np
import pytest

from benchmarks.cenario_a import medir_sistema
from lib.reporting import ResultadoBenchmark

# ---------------------------------------------------------------------------
# Fake
# ---------------------------------------------------------------------------


class FakeBuscador:
    """Buscador determinístico.

    `perfeito=True`: devolve exatamente os `k` ids do ground truth da query
    correspondente (recall = 1.0). `perfeito=False`: devolve ids deslocados
    (recall = 0.0). Conta chamadas para validar warmup.
    """

    def __init__(self, gt_ids: np.ndarray, *, nome: str = "fake", perfeito: bool = True) -> None:
        self.nome = nome
        self._gt = gt_ids
        self._perfeito = perfeito
        self.efs_configurados: list[int] = []
        self.chamadas_busca = 0
        self._idx = 0

    def configurar_ef_search(self, ef: int) -> None:
        self.efs_configurados.append(ef)
        self._idx = 0  # reinicia o ponteiro de query a cada ef

    def buscar_uma(self, query: np.ndarray, k: int) -> list[int]:
        del query
        self.chamadas_busca += 1
        linha = self._gt[self._idx % len(self._gt)]
        self._idx += 1
        if self._perfeito:
            return list(linha[:k])
        return list(linha[:k] + 100_000)  # nenhum id em comum → recall 0


@pytest.fixture
def queries() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.standard_normal((20, 8)).astype(np.float32)


@pytest.fixture
def gt_ids() -> np.ndarray:
    """Ground truth realista: 10 ids DISTINTOS por linha (sem reposição).

    `top_k_exato` nunca repete id numa linha; usar `rng.integers` geraria
    duplicatas e `recall_at_k` (baseado em conjuntos) nunca chegaria a 1.0.
    """
    rng = np.random.default_rng(7)
    linhas = [rng.choice(1000, size=10, replace=False) for _ in range(20)]
    return np.array(linhas, dtype=np.int64)


# ---------------------------------------------------------------------------
# Estrutura da saída
# ---------------------------------------------------------------------------


def test_um_resultado_por_ef_search(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    resultados = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[16, 32, 64],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
    )
    assert len(resultados) == 3
    assert all(isinstance(r, ResultadoBenchmark) for r in resultados)
    assert [r.parametros["ef_search"] for r in resultados] == [16, 32, 64]


def test_configura_ef_em_ordem(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[16, 64, 256],
        k=5,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
    )
    assert buscador.efs_configurados == [16, 64, 256]


def test_campos_fixos_do_resultado(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids, nome="pgvector")
    r = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[32],
        k=10,
        n_base=12345,
        timestamp_utc="2026-05-10T12-00-00Z",
    )[0]
    assert r.cenario == "A"
    assert r.sistema == "pgvector"
    assert r.n == 12345
    assert r.timestamp_utc == "2026-05-10T12-00-00Z"
    assert r.parametros["k"] == 10
    assert r.parametros["ef_search"] == 32
    assert "warmup" in r.parametros
    assert set(r.metricas) >= {"p50", "p95", "p99", "qps", "recall_at_k"}


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------


def test_warmup_e_descartado_das_metricas(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    warmup = 5
    medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[16],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=warmup,
    )
    # 1 ef × (warmup + len(queries)) buscas
    assert buscador.chamadas_busca == warmup + len(queries)


def test_warmup_zero_ok(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[16],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=0,
    )
    assert buscador.chamadas_busca == len(queries)


# ---------------------------------------------------------------------------
# Recall
# ---------------------------------------------------------------------------


def test_recall_1_quando_buscador_perfeito(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids, perfeito=True)
    r = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[64],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=0,
    )[0]
    assert r.metricas["recall_at_k"] == pytest.approx(1.0)


def test_recall_0_quando_buscador_erra_tudo(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids, perfeito=False)
    r = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[64],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=0,
    )[0]
    assert r.metricas["recall_at_k"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Métricas têm tipos serializáveis e valores plausíveis
# ---------------------------------------------------------------------------


def test_metricas_sao_float_plausiveis(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    r = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[32],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
    )[0]
    for chave in ("p50", "p95", "p99", "qps", "recall_at_k"):
        assert isinstance(r.metricas[chave], float)
    assert r.metricas["p99"] >= r.metricas["p50"] >= 0.0
    assert r.metricas["qps"] > 0.0


# ---------------------------------------------------------------------------
# Validações de borda
# ---------------------------------------------------------------------------


def test_levanta_se_queries_vazias(gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    with pytest.raises(ValueError, match="quer"):
        medir_sistema(
            buscador,
            queries=np.zeros((0, 8), dtype=np.float32),
            gt_ids=gt_ids,
            ef_search_values=[16],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-10T00-00-00Z",
        )


def test_levanta_se_ef_search_values_vazio(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    with pytest.raises(ValueError, match="ef_search"):
        medir_sistema(
            buscador,
            queries=queries,
            gt_ids=gt_ids,
            ef_search_values=[],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-10T00-00-00Z",
        )


def test_levanta_se_warmup_negativo(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    with pytest.raises(ValueError, match="warmup"):
        medir_sistema(
            buscador,
            queries=queries,
            gt_ids=gt_ids,
            ef_search_values=[16],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-10T00-00-00Z",
            warmup=-1,
        )


def test_levanta_se_num_queries_difere_do_gt(queries: np.ndarray) -> None:
    gt_curto = np.zeros((5, 10), dtype=np.int64)  # 5 != 20 queries
    buscador = FakeBuscador(gt_curto)
    with pytest.raises(ValueError, match="quer"):
        medir_sistema(
            buscador,
            queries=queries,
            gt_ids=gt_curto,
            ef_search_values=[16],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-10T00-00-00Z",
        )
