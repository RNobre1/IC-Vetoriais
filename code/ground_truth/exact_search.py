"""Ground truth via busca exata por produto interno (FAISS IndexFlatIP).

Para cada vetor de query, devolve os top-K itens da base com maior produto
interno. Como nossos embeddings são L2-normalizados (vide
`pipeline.embeddings`), produto interno é equivalente a similaridade cosseno.

Este módulo é a referência de ouro para o cálculo de `recall@K` dos 3 SGBDs
vetoriais nas Etapas 3-4.

API pública:
- `top_k_exato(base, queries, k) -> (scores, ids)`.
"""

from __future__ import annotations

import faiss
import numpy as np


def top_k_exato(
    base: np.ndarray,
    queries: np.ndarray,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Top-K exato de `queries` contra `base` por produto interno.

    Args:
        base: shape `(N, D)`, `N >= 1`. Pode ser `float32` ou `float64`.
        queries: shape `(M, D)`, `M >= 1`.
        k: `1 <= k <= N`.

    Returns:
        Par `(scores, ids)`:
        - `scores`: shape `(M, k)`, dtype `float32`, ordenado decrescente por linha.
        - `ids`: shape `(M, k)`, dtype `int64`. Índices em `base` (0..N-1).

    Raises:
        ValueError: arrays não 2-D, base/queries vazias, dimensões inconsistentes,
            ou `k` fora de `[1, N]`.
    """
    if base.ndim != 2 or queries.ndim != 2:
        raise ValueError("`base` e `queries` precisam ser arrays 2-D.")
    if base.shape[0] == 0:
        raise ValueError("`base` está vazia.")
    if queries.shape[0] == 0:
        raise ValueError("`queries` está vazia.")
    if base.shape[1] != queries.shape[1]:
        raise ValueError(
            f"dimensão incompatível: base D={base.shape[1]}, queries D={queries.shape[1]}."
        )
    if k <= 0:
        raise ValueError(f"k inválido: {k} (esperado k >= 1).")
    if k > base.shape[0]:
        raise ValueError(f"k maior que tamanho da base: k={k}, |base|={base.shape[0]}.")

    base32 = np.ascontiguousarray(base, dtype=np.float32)
    queries32 = np.ascontiguousarray(queries, dtype=np.float32)

    index = faiss.IndexFlatIP(base.shape[1])
    index.add(base32)
    scores, ids = index.search(queries32, k)

    return scores.astype(np.float32, copy=False), ids.astype(np.int64, copy=False)
