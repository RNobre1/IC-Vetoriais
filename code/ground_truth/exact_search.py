"""Ground truth via busca exata por produto interno (FAISS IndexFlatIP).

Para cada vetor de query, devolve os top-K itens da base com maior produto
interno. Como nossos embeddings são L2-normalizados (vide
`pipeline.embeddings`), produto interno é equivalente a similaridade cosseno.

Este módulo é a referência de ouro para o cálculo de `recall@K` dos 3 SGBDs
vetoriais nas Etapas 3-4.

API pública:
- `top_k_exato(base, queries, k) -> (scores, ids)`.
- `top_k_exato_filtrado(base, queries, *, seletor, p, k) -> (scores, ids)` —
  ground truth do Cenário B: top-K exato *dentro do subconjunto* que satisfaz
  `seletor < p`, com ids remapeados para os ids originais da base.
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


def top_k_exato_filtrado(
    base: np.ndarray,
    queries: np.ndarray,
    *,
    seletor: np.ndarray,
    p: float,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Ground truth do Cenário B: top-K exato *dentro do subconjunto filtrado*.

    O predicado é `seletor < p` (vide
    [[../../vault/decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]).
    A busca exata roda **apenas** sobre os vetores que passam o filtro — é o
    ótimo atingível sob o predicado, contra o qual o recall@K dos SGBDs é
    medido. Os ids retornados são remapeados para os ids originais da base
    (`0..N-1`, consistentes com os seeders), não os índices do subconjunto.

    Args:
        base: shape `(N, D)`, `N >= 1`.
        queries: shape `(M, D)`, `M >= 1`.
        seletor: shape `(N,)`. Atributo numérico por vetor (uniforme em [0,1)
            no uso real; o predicado é `seletor < p`).
        p: limiar de seletividade em `(0, 1]`. `p = 1.0` mantém todos os
            vetores ⇒ resultado idêntico a `top_k_exato` (âncora de sanidade).
        k: `k >= 1`. Se o subconjunto filtrado tiver menos que `k` vetores,
            o resultado é *clampado* ao tamanho do subconjunto (o recall@K
            set-based continua bem definido).

    Returns:
        `(scores, ids)`: shape `(M, min(k, |subconjunto|))`, dtypes
        `float32` / `int64`. `ids` são os ids originais da base.

    Raises:
        ValueError: arrays não 2-D, vazios, dimensões inconsistentes;
            `seletor` não 1-D ou de tamanho `!= N`; `p` fora de `(0, 1]`;
            `k < 1`; ou subconjunto filtrado vazio.
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
    if seletor.ndim != 1 or seletor.shape[0] != base.shape[0]:
        raise ValueError(
            f"`seletor` precisa ter shape (N,) com N={base.shape[0]}; "
            f"recebido shape={seletor.shape}."
        )
    if not (0.0 < p <= 1.0):
        raise ValueError(f"p inválido: {p} (esperado 0 < p <= 1).")
    if k <= 0:
        raise ValueError(f"k inválido: {k} (esperado k >= 1).")

    mascara = seletor < p
    ids_originais = np.nonzero(mascara)[0].astype(np.int64, copy=False)
    if ids_originais.shape[0] == 0:
        raise ValueError(
            f"subconjunto filtrado vazio: nenhum seletor < p={p}. "
            "Reveja a grade de seletividades ou o atributo `seletor`."
        )

    k_efetivo = min(k, int(ids_originais.shape[0]))
    sub = np.ascontiguousarray(base[mascara], dtype=np.float32)
    queries32 = np.ascontiguousarray(queries, dtype=np.float32)

    index = faiss.IndexFlatIP(base.shape[1])
    index.add(sub)
    scores, ids_locais = index.search(queries32, k_efetivo)

    ids_remapeados = ids_originais[ids_locais.astype(np.int64, copy=False)]
    return scores.astype(np.float32, copy=False), ids_remapeados
