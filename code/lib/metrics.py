"""Métricas dos experimentos: percentis de latência, QPS e recall@K.

Estas três funções produzem os números que entram em `vault/experimentos/`,
`code/results/*.json` e tabelas/figuras do relatório. Mantê-las puras,
determinísticas e bem testadas é um requisito de reprodutibilidade.

API pública:
- `latencia_percentis(latencias) -> {"p50", "p95", "p99"}`.
- `qps(num_queries, tempo_total_s) -> float`.
- `recall_at_k(ids_obtidos, ids_referencia, *, k=None) -> float`.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

# ---------------------------------------------------------------------------
# Latência: percentis p50/p95/p99
# ---------------------------------------------------------------------------


def latencia_percentis(latencias: Sequence[float] | np.ndarray) -> dict[str, float]:
    """Devolve `{"p50", "p95", "p99"}` para a distribuição de latências.

    A unidade da saída é a mesma da entrada (não converte ms↔s).
    Levanta `ValueError` se a sequência estiver vazia.
    """
    arr = np.asarray(latencias, dtype=np.float64)
    if arr.size == 0:
        raise ValueError("Distribuição de latências vazia — nada para sumarizar.")
    return {
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
    }


# ---------------------------------------------------------------------------
# QPS
# ---------------------------------------------------------------------------


def qps(*, num_queries: int, tempo_total_s: float) -> float:
    """Queries por segundo. Ambos parâmetros precisam ser estritamente positivos."""
    if num_queries <= 0:
        raise ValueError(f"num_queries inválido: {num_queries} (esperado >= 1).")
    if tempo_total_s <= 0:
        raise ValueError(f"tempo_total_s inválido: {tempo_total_s} (esperado > 0).")
    return num_queries / tempo_total_s


# ---------------------------------------------------------------------------
# Recall@K
# ---------------------------------------------------------------------------


def recall_at_k(
    ids_obtidos: np.ndarray,
    ids_referencia: np.ndarray,
    *,
    k: int | None = None,
) -> float:
    """Recall@K médio entre `ids_obtidos` e `ids_referencia`.

    Para cada query `i`:
        recall_i = |set(obtidos[i][:k]) ∩ set(referencia[i][:k])| / k

    Retorna a média sobre as queries (`float` em `[0, 1]`).

    `k=None` (default) usa `min(obtidos.shape[1], referencia.shape[1])`.

    Levanta `ValueError` para arrays não 2-D, número de queries divergente,
    arrays vazios, ou `k` fora de `[1, min(K_obtido, K_ref)]`.
    """
    if ids_obtidos.ndim != 2 or ids_referencia.ndim != 2:
        raise ValueError("`ids_obtidos` e `ids_referencia` precisam ser arrays 2-D.")
    if ids_obtidos.shape[0] == 0 and ids_referencia.shape[0] == 0:
        raise ValueError("Arrays vazios — nada para comparar.")
    if ids_obtidos.shape[0] != ids_referencia.shape[0]:
        raise ValueError(
            f"número de queries diferente: obtido={ids_obtidos.shape[0]}, "
            f"referencia={ids_referencia.shape[0]}."
        )

    k_max = min(ids_obtidos.shape[1], ids_referencia.shape[1])
    if k is None:
        k = k_max
    if k <= 0:
        raise ValueError(f"k inválido: {k} (esperado k >= 1).")
    if k > k_max:
        raise ValueError(
            f"k maior que profundidade disponível: k={k}, " f"min(obtido, referencia) = {k_max}."
        )

    recalls = np.empty(ids_obtidos.shape[0], dtype=np.float64)
    for i in range(ids_obtidos.shape[0]):
        intersec = np.intersect1d(ids_obtidos[i, :k], ids_referencia[i, :k], assume_unique=False)
        recalls[i] = len(intersec) / k
    return float(recalls.mean())
