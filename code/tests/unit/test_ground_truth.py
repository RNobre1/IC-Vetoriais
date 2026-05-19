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

from ground_truth.exact_search import top_k_exato, top_k_exato_filtrado

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


# ===========================================================================
# top_k_exato_filtrado — ground truth do Cenário B (recall sob filtro)
#
# Decisão: [[vault/decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]].
# `seletor` é um atributo numérico por vetor; o predicado é `seletor < p`.
# O recall@K do Cenário B é medido contra o top-K exato *dentro do
# subconjunto que passa o filtro*, com ids remapeados para os ids originais
# da base (0..N-1, consistentes com os seeders).
# ===========================================================================


@pytest.fixture
def seletor_arange() -> np.ndarray:
    """`seletor[i] = i/100` — `seletor < p` mantém exatamente os ids `0..ceil(p·100)-1`.

    Correlação id↔seletor é intencional *no teste* (torna o subconjunto e o
    remapeamento previsíveis). A decorrelação real é responsabilidade do seed.
    """
    return np.arange(100, dtype=np.float64) / 100.0


def test_filtrado_shape_e_dtypes(base_normalizada: np.ndarray, seletor_arange: np.ndarray) -> None:
    queries = base_normalizada[:5]
    scores, ids = top_k_exato_filtrado(
        base_normalizada, queries, seletor=seletor_arange, p=0.5, k=10
    )
    assert scores.shape == (5, 10)
    assert ids.shape == (5, 10)
    assert scores.dtype == np.float32
    assert ids.dtype == np.int64


def test_filtrado_so_retorna_ids_que_passam_o_predicado(
    base_normalizada: np.ndarray, seletor_arange: np.ndarray
) -> None:
    # p=0.5 com seletor=arange/100 mantém ids 0..49; 50..99 são excluídos.
    queries = base_normalizada  # inclui queries cujo vizinho global está fora
    _, ids = top_k_exato_filtrado(base_normalizada, queries, seletor=seletor_arange, p=0.5, k=10)
    assert ids.min() >= 0
    assert ids.max() < 50, "nenhum id excluído pelo filtro pode aparecer"


def test_filtrado_top1_de_item_que_passa_e_o_proprio_id_original(
    base_normalizada: np.ndarray, seletor_arange: np.ndarray
) -> None:
    # query == base[7]; 7 passa o filtro (7/100 < 0.5) → top-1 deve ser o id 7.
    queries = base_normalizada[7:8]
    scores, ids = top_k_exato_filtrado(
        base_normalizada, queries, seletor=seletor_arange, p=0.5, k=5
    )
    assert ids[0, 0] == 7
    np.testing.assert_allclose(scores[0, 0], 1.0, atol=1e-5)


def test_filtrado_p_1_equivale_a_busca_global_do_cenario_a(
    base_normalizada: np.ndarray, seletor_arange: np.ndarray
) -> None:
    # Âncora de sanidade: p=1.0 mantém todos → idêntico ao Cenário A.
    queries = base_normalizada[:10]
    s_glob, i_glob = top_k_exato(base_normalizada, queries, k=10)
    s_filt, i_filt = top_k_exato_filtrado(
        base_normalizada, queries, seletor=seletor_arange, p=1.0, k=10
    )
    np.testing.assert_array_equal(i_glob, i_filt)
    np.testing.assert_array_equal(s_glob, s_filt)


def test_filtrado_k_clampado_quando_subconjunto_menor_que_k(
    base_normalizada: np.ndarray, seletor_arange: np.ndarray
) -> None:
    # p=0.05 → seletor<0.05 mantém ids 0..4 (5 itens). k=10 → 5 colunas.
    queries = base_normalizada[:3]
    scores, ids = top_k_exato_filtrado(
        base_normalizada, queries, seletor=seletor_arange, p=0.05, k=10
    )
    assert scores.shape == (3, 5)
    assert ids.shape == (3, 5)
    assert set(ids.ravel().tolist()).issubset(set(range(5)))


def test_filtrado_determinismo_bit_a_bit(
    base_normalizada: np.ndarray, seletor_arange: np.ndarray
) -> None:
    queries = base_normalizada[:5]
    s1, i1 = top_k_exato_filtrado(base_normalizada, queries, seletor=seletor_arange, p=0.3, k=7)
    s2, i2 = top_k_exato_filtrado(base_normalizada, queries, seletor=seletor_arange, p=0.3, k=7)
    assert np.array_equal(s1, s2)
    assert np.array_equal(i1, i2)


def test_filtrado_levanta_se_seletor_shape_invalido(
    base_normalizada: np.ndarray,
) -> None:
    queries = base_normalizada[:1]
    seletor_2d = np.zeros((100, 1), dtype=np.float64)
    with pytest.raises(ValueError, match="seletor"):
        top_k_exato_filtrado(base_normalizada, queries, seletor=seletor_2d, p=0.5, k=5)
    seletor_curto = np.zeros(99, dtype=np.float64)
    with pytest.raises(ValueError, match="seletor"):
        top_k_exato_filtrado(base_normalizada, queries, seletor=seletor_curto, p=0.5, k=5)


def test_filtrado_levanta_se_p_fora_de_0_1(
    base_normalizada: np.ndarray, seletor_arange: np.ndarray
) -> None:
    queries = base_normalizada[:1]
    for p_invalido in (0.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="p"):
            top_k_exato_filtrado(
                base_normalizada, queries, seletor=seletor_arange, p=p_invalido, k=5
            )


def test_filtrado_levanta_se_subconjunto_vazio(
    base_normalizada: np.ndarray, seletor_arange: np.ndarray
) -> None:
    # Nenhum seletor < p muito pequeno (min(seletor)=0.0; p=0.0 já barrado,
    # mas um seletor todo >= p deixa o subconjunto vazio).
    seletor_alto = np.ones(100, dtype=np.float64)
    queries = base_normalizada[:1]
    with pytest.raises(ValueError, match="subconjunto"):
        top_k_exato_filtrado(base_normalizada, queries, seletor=seletor_alto, p=0.5, k=5)


def test_filtrado_levanta_se_k_invalido(
    base_normalizada: np.ndarray, seletor_arange: np.ndarray
) -> None:
    queries = base_normalizada[:1]
    with pytest.raises(ValueError, match="k"):
        top_k_exato_filtrado(base_normalizada, queries, seletor=seletor_arange, p=0.5, k=0)
