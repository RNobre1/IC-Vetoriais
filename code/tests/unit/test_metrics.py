"""Testes de `lib.metrics` (TDD — escritos antes da implementação).

Três peças, todas funções puras sobre numpy:
- `latencia_percentis(latencias)` → dict com p50, p95, p99 (mesma unidade da entrada).
- `qps(num_queries, tempo_total_s)` → float (queries por segundo).
- `recall_at_k(ids_obtidos, ids_referencia, *, k=None)` → float em [0,1].

Estes três blocos viram os números que vão para `vault/experimentos/`,
`code/results/` e, mais tarde, para o relatório parcial. Logo precisam ser
exatos em casos canônicos e levantar erro útil em casos de borda.
"""

from __future__ import annotations

import numpy as np
import pytest

from lib.metrics import latencia_percentis, qps, recall_at_k

# ---------------------------------------------------------------------------
# latencia_percentis
# ---------------------------------------------------------------------------


def test_percentis_em_distribuicao_uniforme_0_a_100() -> None:
    """Sequência [0, 1, ..., 100] tem percentis idênticos aos índices."""
    latencias = np.arange(101, dtype=np.float64)
    p = latencia_percentis(latencias)
    assert p["p50"] == pytest.approx(50.0)
    assert p["p95"] == pytest.approx(95.0)
    assert p["p99"] == pytest.approx(99.0)


def test_percentis_aceita_lista_python() -> None:
    p = latencia_percentis([1.0, 2.0, 3.0, 4.0, 5.0])
    assert p["p50"] == pytest.approx(3.0)


def test_percentis_um_elemento_so() -> None:
    p = latencia_percentis([42.0])
    assert p["p50"] == pytest.approx(42.0)
    assert p["p95"] == pytest.approx(42.0)
    assert p["p99"] == pytest.approx(42.0)


def test_percentis_chaves_exatas() -> None:
    p = latencia_percentis([1.0, 2.0, 3.0])
    assert set(p.keys()) == {"p50", "p95", "p99"}


def test_percentis_lista_vazia_levanta() -> None:
    with pytest.raises(ValueError, match="vazia"):
        latencia_percentis([])
    with pytest.raises(ValueError, match="vazia"):
        latencia_percentis(np.array([], dtype=np.float64))


# ---------------------------------------------------------------------------
# qps
# ---------------------------------------------------------------------------


def test_qps_caso_basico() -> None:
    assert qps(num_queries=100, tempo_total_s=2.0) == pytest.approx(50.0)


def test_qps_uma_query_em_um_segundo() -> None:
    assert qps(num_queries=1, tempo_total_s=1.0) == pytest.approx(1.0)


def test_qps_levanta_se_tempo_invalido() -> None:
    with pytest.raises(ValueError, match="tempo"):
        qps(num_queries=10, tempo_total_s=0.0)
    with pytest.raises(ValueError, match="tempo"):
        qps(num_queries=10, tempo_total_s=-1.0)


def test_qps_levanta_se_num_queries_invalido() -> None:
    with pytest.raises(ValueError, match="queries"):
        qps(num_queries=0, tempo_total_s=1.0)
    with pytest.raises(ValueError, match="queries"):
        qps(num_queries=-5, tempo_total_s=1.0)


# ---------------------------------------------------------------------------
# recall_at_k
# ---------------------------------------------------------------------------


def test_recall_obtido_igual_referencia_e_1_0() -> None:
    ref = np.array([[10, 20, 30], [40, 50, 60]], dtype=np.int64)
    obt = ref.copy()
    assert recall_at_k(obt, ref) == pytest.approx(1.0)


def test_recall_sem_intersecao_e_0() -> None:
    ref = np.array([[1, 2, 3]], dtype=np.int64)
    obt = np.array([[4, 5, 6]], dtype=np.int64)
    assert recall_at_k(obt, ref) == pytest.approx(0.0)


def test_recall_meia_intersecao() -> None:
    """obtido[0] tem {1,2,3,4,5} ∩ referencia[0] {1,2,3,6,7} = {1,2,3} → 3/5."""
    ref = np.array([[1, 2, 3, 6, 7]], dtype=np.int64)
    obt = np.array([[1, 2, 3, 4, 5]], dtype=np.int64)
    assert recall_at_k(obt, ref) == pytest.approx(0.6)


def test_recall_e_media_entre_queries() -> None:
    """Query 0: recall 1.0. Query 1: recall 0.0. Média = 0.5."""
    ref = np.array([[1, 2], [3, 4]], dtype=np.int64)
    obt = np.array([[1, 2], [9, 8]], dtype=np.int64)
    assert recall_at_k(obt, ref) == pytest.approx(0.5)


def test_recall_independe_de_ordem_dentro_do_topk() -> None:
    """Recall é baseado em conjuntos — ordem do top-K não importa."""
    ref = np.array([[1, 2, 3]], dtype=np.int64)
    obt = np.array([[3, 1, 2]], dtype=np.int64)
    assert recall_at_k(obt, ref) == pytest.approx(1.0)


def test_recall_k_explicito_trunca_ambos() -> None:
    """Com k=3, só comparamos os 3 primeiros de cada linha."""
    ref = np.array([[1, 2, 3, 4, 5]], dtype=np.int64)
    obt = np.array([[1, 2, 3, 99, 100]], dtype=np.int64)
    assert recall_at_k(obt, ref, k=3) == pytest.approx(1.0)
    # com k=5, recall = 3/5 = 0.6
    assert recall_at_k(obt, ref, k=5) == pytest.approx(0.6)


def test_recall_k_default_usa_min_dos_dois() -> None:
    """Sem `k`, usa min(obtido.shape[1], referencia.shape[1])."""
    ref = np.array([[1, 2, 3, 4, 5]], dtype=np.int64)
    obt = np.array([[1, 2, 3]], dtype=np.int64)  # shape (1, 3)
    # k efetivo = 3; intersecção = {1,2,3} = 3 → 3/3 = 1.0
    assert recall_at_k(obt, ref) == pytest.approx(1.0)


def test_recall_levanta_se_num_queries_diferente() -> None:
    ref = np.array([[1, 2], [3, 4]], dtype=np.int64)
    obt = np.array([[1, 2]], dtype=np.int64)
    with pytest.raises(ValueError, match="queries"):
        recall_at_k(obt, ref)


def test_recall_levanta_se_arrays_nao_2d() -> None:
    ref_1d = np.array([1, 2, 3], dtype=np.int64)
    obt_2d = np.array([[1, 2, 3]], dtype=np.int64)
    with pytest.raises(ValueError, match="2"):
        recall_at_k(obt_2d, ref_1d)
    with pytest.raises(ValueError, match="2"):
        recall_at_k(ref_1d, obt_2d)


def test_recall_levanta_se_k_invalido() -> None:
    ref = np.array([[1, 2, 3]], dtype=np.int64)
    obt = np.array([[1, 2, 3]], dtype=np.int64)
    with pytest.raises(ValueError, match="k"):
        recall_at_k(obt, ref, k=0)
    with pytest.raises(ValueError, match="k"):
        recall_at_k(obt, ref, k=-1)


def test_recall_levanta_se_k_excede_shape() -> None:
    ref = np.array([[1, 2, 3]], dtype=np.int64)
    obt = np.array([[1, 2, 3]], dtype=np.int64)
    with pytest.raises(ValueError, match="k"):
        recall_at_k(obt, ref, k=10)


def test_recall_levanta_se_arrays_vazios() -> None:
    vazio = np.zeros((0, 5), dtype=np.int64)
    com_dado = np.array([[1, 2, 3, 4, 5]], dtype=np.int64)
    with pytest.raises(ValueError, match="vazi"):
        recall_at_k(vazio, vazio)
    with pytest.raises(ValueError, match="queries"):
        recall_at_k(vazio, com_dado)
