"""Cenário B — busca semântica com filtro de seletividade variável.

Estende o Cenário A: além de varrer `efSearch`, varre a **seletividade** do
predicado `seletor < p` (fração da base elegível: 1%, 10%, 50%, 100%). Mede
latência (p50/p95/p99), QPS e recall@K sob filtro, comparando contra o
ground truth **filtrado por seletividade** (não o GT global do A).

Decisões metodológicas em
[[../../vault/decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]:

- Predicado = atributo numérico `seletor` uniforme; `seletor < p`.
- Ground truth = top-K exato *dentro do subconjunto filtrado*, um por `p`
  (`ground_truth.exact_search.top_k_exato_filtrado`).
- `p = 1.0` ⇒ sem filtro efetivo ⇒ deve reproduzir o Cenário A (âncora).

A medição opera sobre o Protocol `BuscadorFiltravel` (estende
`BuscadorVetorial` com `buscar_uma_filtrada`); cada SGBD entra como adaptador
concreto (`benchmarks.buscadores`), mantendo a orquestração testável sem
Docker. Queries held-out e warmup+descarte herdados do Cenário A
([[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]]).
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

import numpy as np

from benchmarks.cenario_a import WARMUP_PADRAO, BuscadorVetorial
from lib.metrics import latencia_percentis, qps, recall_at_k
from lib.reporting import ResultadoBenchmark


@runtime_checkable
class BuscadorFiltravel(BuscadorVetorial, Protocol):
    """`BuscadorVetorial` + busca com predicado de seletividade (Cenário B)."""

    def buscar_uma_filtrada(self, query: np.ndarray, k: int, *, p_max: float) -> list[int]:
        """Retorna os ids dos `k` vizinhos com `seletor < p_max`."""
        ...


def medir_sistema_filtrado(
    buscador: BuscadorFiltravel,
    *,
    queries: np.ndarray,
    gt_por_seletividade: Mapping[float, np.ndarray],
    ef_search_values: Sequence[int],
    seletividades: Sequence[float],
    k: int,
    n_base: int,
    timestamp_utc: str,
    warmup: int = WARMUP_PADRAO,
    parametros_extra: dict | None = None,
    ambiente: dict | None = None,
) -> list[ResultadoBenchmark]:
    """Varre `seletividades × ef_search_values`. Um `ResultadoBenchmark` por combo.

    Laço externo = seletividade, interno = `efSearch`. Para cada `(p, ef)`:
    configura o sistema, roda `warmup` buscas filtradas descartadas, mede
    `len(queries)` buscas filtradas (latência por query, ms) e calcula
    p50/p95/p99, QPS e recall@k contra `gt_por_seletividade[p]`.

    O recall usa `k=None` (profundidade = `min(obtido, gt)`): com seletividade
    pequena o GT filtrado pode ter menos que `k` colunas (subconjunto < k);
    o denominador passa a ser o tamanho do subconjunto, conforme a ADR.

    Levanta `ValueError` para: `queries` vazias; `ef_search_values` vazio;
    `seletividades` vazio; `warmup` negativo; falta de ground truth para
    alguma seletividade; ou `len(queries) != len(gt)` de alguma seletividade.
    """
    if queries.shape[0] == 0:
        raise ValueError("`queries` vazio — nada para medir.")
    if len(ef_search_values) == 0:
        raise ValueError("`ef_search_values` vazio — nada para varrer.")
    if len(seletividades) == 0:
        raise ValueError("`seletividades` vazio — nada para varrer.")
    if warmup < 0:
        raise ValueError(f"warmup inválido: {warmup} (esperado >= 0).")
    for p in seletividades:
        if p not in gt_por_seletividade:
            raise ValueError(
                f"ground truth ausente para a seletividade {p}; "
                f"forneça `gt_por_seletividade[{p}]`."
            )
        if queries.shape[0] != gt_por_seletividade[p].shape[0]:
            raise ValueError(
                f"nº de queries difere do ground truth (seletividade {p}): "
                f"queries={queries.shape[0]}, gt={gt_por_seletividade[p].shape[0]}."
            )

    n_queries = queries.shape[0]
    resultados: list[ResultadoBenchmark] = []

    for p in seletividades:
        gt_ids = gt_por_seletividade[p]
        for ef in ef_search_values:
            buscador.configurar_ef_search(ef)

            for i in range(warmup):
                buscador.buscar_uma_filtrada(queries[i % n_queries], k, p_max=p)

            latencias_ms = np.empty(n_queries, dtype=np.float64)
            # Sob filtro forte o subconjunto pode ter < k itens: a busca
            # devolve menos que `k` ids. Preenchemos com -1 (sentinela que
            # nunca casa com id válido >= 0) para manter a matriz retangular;
            # `recall_at_k` é set-based e ignora o padding.
            ids_obtidos = np.full((n_queries, k), -1, dtype=np.int64)
            for i in range(n_queries):
                t0 = time.perf_counter()
                ids = buscador.buscar_uma_filtrada(queries[i], k, p_max=p)
                latencias_ms[i] = (time.perf_counter() - t0) * 1000.0
                ids_obtidos[i, : len(ids)] = ids

            perc = latencia_percentis(latencias_ms)
            tempo_total_s = float(latencias_ms.sum()) / 1000.0
            qps_v = qps(num_queries=n_queries, tempo_total_s=tempo_total_s)
            recall_v = recall_at_k(ids_obtidos, gt_ids, k=None)

            parametros = {
                "ef_search": ef,
                "k": k,
                "warmup": warmup,
                "seletividade": p,
            }
            if parametros_extra:
                parametros.update(parametros_extra)

            resultados.append(
                ResultadoBenchmark(
                    cenario="B",
                    sistema=buscador.nome,
                    n=n_base,
                    timestamp_utc=timestamp_utc,
                    parametros=parametros,
                    metricas={
                        "p50": perc["p50"],
                        "p95": perc["p95"],
                        "p99": perc["p99"],
                        "qps": qps_v,
                        "recall_at_k": recall_v,
                    },
                    ambiente=dict(ambiente) if ambiente else {},
                )
            )

    return resultados
