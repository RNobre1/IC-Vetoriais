"""Cenário A — busca semântica pura.

Mede latência (p50/p95/p99), QPS e recall@K de um SGBD vetorial sob busca
pura, varrendo `efSearch`. Decisões metodológicas em
[[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]]:

- Queries = passages held-out (split estilo ANN-Benchmarks).
- Warmup descartado antes de medir (default 50), registrado no resultado.
- Ground truth = top-K exato (FAISS, `ground_truth.exact_search`).

A lógica de medição (`medir_sistema`) opera sobre o Protocol
`BuscadorVetorial`. Cada SGBD entra como um adaptador concreto (testado em
integração à parte), mantendo esta orquestração testável sem Docker.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

import numpy as np

from lib.metrics import latencia_percentis, qps, recall_at_k
from lib.reporting import ResultadoBenchmark

WARMUP_PADRAO = 50


@runtime_checkable
class BuscadorVetorial(Protocol):
    """Interface mínima que cada SGBD precisa expor para o Cenário A."""

    nome: str

    def configurar_ef_search(self, ef: int) -> None:
        """Ajusta o parâmetro de busca HNSW (`efSearch`/`hnsw_ef`/`ef`)."""
        ...

    def buscar_uma(self, query: np.ndarray, k: int) -> list[int]:
        """Retorna os ids dos `k` vizinhos mais próximos de `query`."""
        ...


def medir_sistema(
    buscador: BuscadorVetorial,
    *,
    queries: np.ndarray,
    gt_ids: np.ndarray,
    ef_search_values: Sequence[int],
    k: int,
    n_base: int,
    timestamp_utc: str,
    warmup: int = WARMUP_PADRAO,
    parametros_extra: dict | None = None,
    ambiente: dict | None = None,
) -> list[ResultadoBenchmark]:
    """Varre `ef_search_values` medindo o `buscador`. Um `ResultadoBenchmark` por ef.

    Para cada `ef`: configura o sistema, roda `warmup` buscas descartadas, mede
    `len(queries)` buscas individuais (latência por query, em ms), e calcula
    p50/p95/p99, QPS e recall@k contra `gt_ids`.

    Levanta `ValueError` para `queries` vazias, `ef_search_values` vazio,
    `warmup` negativo, ou `len(queries) != len(gt_ids)`.
    """
    if queries.shape[0] == 0:
        raise ValueError("`queries` vazio — nada para medir.")
    if len(ef_search_values) == 0:
        raise ValueError("`ef_search_values` vazio — nada para varrer.")
    if warmup < 0:
        raise ValueError(f"warmup inválido: {warmup} (esperado >= 0).")
    if queries.shape[0] != gt_ids.shape[0]:
        raise ValueError(
            f"nº de queries difere do ground truth: queries={queries.shape[0]}, "
            f"gt_ids={gt_ids.shape[0]}."
        )

    n_queries = queries.shape[0]
    resultados: list[ResultadoBenchmark] = []

    for ef in ef_search_values:
        buscador.configurar_ef_search(ef)

        for i in range(warmup):
            buscador.buscar_uma(queries[i % n_queries], k)

        latencias_ms = np.empty(n_queries, dtype=np.float64)
        ids_obtidos = np.empty((n_queries, k), dtype=np.int64)
        for i in range(n_queries):
            t0 = time.perf_counter()
            ids = buscador.buscar_uma(queries[i], k)
            latencias_ms[i] = (time.perf_counter() - t0) * 1000.0
            ids_obtidos[i] = ids

        p = latencia_percentis(latencias_ms)
        tempo_total_s = float(latencias_ms.sum()) / 1000.0
        qps_v = qps(num_queries=n_queries, tempo_total_s=tempo_total_s)
        recall_v = recall_at_k(ids_obtidos, gt_ids, k=k)

        parametros = {"ef_search": ef, "k": k, "warmup": warmup}
        if parametros_extra:
            parametros.update(parametros_extra)

        resultados.append(
            ResultadoBenchmark(
                cenario="A",
                sistema=buscador.nome,
                n=n_base,
                timestamp_utc=timestamp_utc,
                parametros=parametros,
                metricas={
                    "p50": p["p50"],
                    "p95": p["p95"],
                    "p99": p["p99"],
                    "qps": qps_v,
                    "recall_at_k": recall_v,
                },
                ambiente=dict(ambiente) if ambiente else {},
            )
        )

    return resultados
