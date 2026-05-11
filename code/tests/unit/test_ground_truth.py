"""Testes de `ground_truth.exact_search` (TDD — escritos antes da implementação).

A função `top_k_exato(base, queries, k)` retorna `(scores, ids)` com o top-K exato
por produto interno (FAISS `IndexFlatIP`). Como nossos embeddings serão sempre
normalizados L2 (vide `pipeline.embeddings`), produto interno é equivalente a
cosseno. Isto vira a referência de ouro para o cálculo de `recall@K` dos 3 SGBDs.

Princípios:
- API funcional pura: sem estado global, sem I/O.
- Determinismo absoluto: mesmas entradas → bit-a-bit a mesma saída.
- Validação na borda: o módulo é a fronteira entre numpy do usuário e FAISS;
  rejeita formatos inválidos antes de chamar a biblioteca C++.
"""

from __future__ import annotations

import numpy as np
import pytest

from ground_truth.exact_search import top_k_exato

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rng() -> np.random.Generator:
    """RNG fixo para reprodutibilidade dos próprios testes."""
    return np.random.default_rng(42)


@pytest.fixture
def base_normalizada(rng: np.random.Generator) -> np.ndarray:
    """100 vetores 384-D normalizados L2 (`float32`)."""
    arr = rng.standard_normal((100, 384)).astype(np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    return arr


# ---------------------------------------------------------------------------
# Saída: shape e dtypes
# ---------------------------------------------------------------------------


def test_top_k_retorna_shape_e_dtypes_corretos(base_normalizada: np.ndarray) -> None:
    queries = base_normalizada[:5]  # 5 queries quaisquer
    scores, ids = top_k_exato(base_normalizada, queries, k=10)

    assert scores.shape == (5, 10)
    assert ids.shape == (5, 10)
    assert scores.dtype == np.float32
    assert ids.dtype == np.int64


# ---------------------------------------------------------------------------
# Correção semântica: query == base[i] → top-1 é o próprio i
# ---------------------------------------------------------------------------


def test_top_1_de_query_igual_a_base_retorna_proprio_item(base_normalizada: np.ndarray) -> None:
    queries = base_normalizada  # query[i] == base[i] para todo i
    scores, ids = top_k_exato(base_normalizada, queries, k=1)

    np.testing.assert_array_equal(ids[:, 0], np.arange(len(base_normalizada)))
    # produto interno de vetor normalizado consigo mesmo ≈ 1.0
    np.testing.assert_allclose(scores[:, 0], np.ones(len(base_normalizada)), atol=1e-5)


# ---------------------------------------------------------------------------
# Ordenação: top-K vem em ordem decrescente de score
# ---------------------------------------------------------------------------


def test_resultado_ordenado_por_score_decrescente(base_normalizada: np.ndarray) -> None:
    queries = base_normalizada[:3]
    scores, _ = top_k_exato(base_normalizada, queries, k=20)

    # Cada linha deve estar em ordem decrescente
    for linha in scores:
        diffs = np.diff(linha)
        assert np.all(diffs <= 1e-6), f"Esperado decrescente, recebi {linha}"


# ---------------------------------------------------------------------------
# Recall vs si mesmo: ground truth contra ground truth = 100%
# ---------------------------------------------------------------------------


def test_recall_contra_si_mesmo_e_100_porcento(base_normalizada: np.ndarray) -> None:
    queries = base_normalizada[:10]
    _, ids_a = top_k_exato(base_normalizada, queries, k=10)
    _, ids_b = top_k_exato(base_normalizada, queries, k=10)

    np.testing.assert_array_equal(ids_a, ids_b)


# ---------------------------------------------------------------------------
# Determinismo bit-a-bit
# ---------------------------------------------------------------------------


def test_determinismo_bit_a_bit(base_normalizada: np.ndarray) -> None:
    queries = base_normalizada[:5]
    s1, i1 = top_k_exato(base_normalizada, queries, k=10)
    s2, i2 = top_k_exato(base_normalizada, queries, k=10)

    assert np.array_equal(s1, s2)
    assert np.array_equal(i1, i2)


# ---------------------------------------------------------------------------
# Aceita float64 e converte internamente para float32 (requisito do FAISS)
# ---------------------------------------------------------------------------


def test_aceita_float64_e_converte_para_float32(rng: np.random.Generator) -> None:
    base = rng.standard_normal((50, 16)).astype(np.float64)
    base /= np.linalg.norm(base, axis=1, keepdims=True)
    queries = base[:3]

    scores, ids = top_k_exato(base, queries, k=5)

    assert scores.dtype == np.float32
    assert ids.dtype == np.int64
    np.testing.assert_array_equal(ids[:, 0], np.arange(3))


# ---------------------------------------------------------------------------
# Validações de borda
# ---------------------------------------------------------------------------


def test_levanta_se_dimensoes_inconsistentes(base_normalizada: np.ndarray) -> None:
    queries_dim_errada = np.zeros((3, 128), dtype=np.float32)
    with pytest.raises(ValueError, match="dimensão"):
        top_k_exato(base_normalizada, queries_dim_errada, k=5)


def test_levanta_se_k_invalido(base_normalizada: np.ndarray) -> None:
    queries = base_normalizada[:1]
    with pytest.raises(ValueError, match="k"):
        top_k_exato(base_normalizada, queries, k=0)
    with pytest.raises(ValueError, match="k"):
        top_k_exato(base_normalizada, queries, k=-1)


def test_levanta_se_k_maior_que_base(base_normalizada: np.ndarray) -> None:
    queries = base_normalizada[:1]
    with pytest.raises(ValueError, match="k"):
        top_k_exato(base_normalizada, queries, k=len(base_normalizada) + 1)


def test_levanta_se_arrays_nao_2d(base_normalizada: np.ndarray) -> None:
    queries_1d = base_normalizada[0]  # shape (384,) — não 2-D
    with pytest.raises(ValueError, match="2"):
        top_k_exato(base_normalizada, queries_1d, k=5)

    base_1d = base_normalizada.ravel()  # shape (100*384,) — não 2-D
    queries_2d = base_normalizada[:1]
    with pytest.raises(ValueError, match="2"):
        top_k_exato(base_1d, queries_2d, k=5)


def test_levanta_se_base_vazia() -> None:
    base_vazia = np.zeros((0, 384), dtype=np.float32)
    queries = np.zeros((1, 384), dtype=np.float32)
    with pytest.raises(ValueError, match="vazia"):
        top_k_exato(base_vazia, queries, k=1)


def test_levanta_se_queries_vazia(base_normalizada: np.ndarray) -> None:
    queries_vazia = np.zeros((0, 384), dtype=np.float32)
    with pytest.raises(ValueError, match="vazia"):
        top_k_exato(base_normalizada, queries_vazia, k=5)
