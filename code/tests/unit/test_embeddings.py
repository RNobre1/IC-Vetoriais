"""Testes do `pipeline.embeddings` (TDD — escritos antes da implementação).

Estratégia de mock:
- O módulo expõe `gerar_embeddings(textos, *, modelo_nome, cache_dir, encoder_factory)`.
- `encoder_factory` é um callable que devolve um objeto com método `.encode(...)`.
- Em produção, o factory padrão constrói um `SentenceTransformer`.
- Em testes, passamos um factory que devolve um `FakeEncoder` previsível.

Isso permite TDD sem depender do download do modelo real (~80 MB) nem da
instalação de torch (~700 MB) — essas dependências entram em commit separado.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from pipeline.embeddings import (
    DIM_MINILM_L6_V2,
    MODELO_PADRAO,
    chave_cache,
    gerar_embeddings,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeEncoder:
    """Encoder previsível: emula a API do sentence-transformers em RAM.

    Para texto T, gera o vetor `[hash(T) % 7919 / 7919, 0, 0, ...]` (não normalizado),
    normalizado L2 se `normalize_embeddings=True`. Determinístico e sem rede.
    """

    def __init__(self, dim: int = DIM_MINILM_L6_V2) -> None:
        self.dim = dim
        self.chamadas = 0

    def encode(
        self,
        textos: list[str],
        *,
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        del batch_size, show_progress_bar  # mantém a assinatura compatível, ignorada no fake
        self.chamadas += 1
        out = np.zeros((len(textos), self.dim), dtype=np.float32)
        for i, t in enumerate(textos):
            valor = (hash(t) % 7919) / 7919.0 + 0.001  # evita vetor zero
            out[i, 0] = valor
            out[i, 1] = valor / 2
            out[i, 2] = valor / 3
        if normalize_embeddings:
            normas = np.linalg.norm(out, axis=1, keepdims=True)
            normas[normas == 0] = 1.0
            out = out / normas
        return out


@pytest.fixture
def encoder_factory() -> Callable[[], FakeEncoder]:
    """Factory que constrói um FakeEncoder novo a cada chamada."""

    def _f() -> FakeEncoder:
        return FakeEncoder()

    return _f


@pytest.fixture
def encoder_singleton(encoder_factory: Callable[[], FakeEncoder]) -> FakeEncoder:
    """FakeEncoder único compartilhado pra contar chamadas."""
    return encoder_factory()


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------


def test_modelo_padrao_e_minilm() -> None:
    assert MODELO_PADRAO == "sentence-transformers/all-MiniLM-L6-v2"


def test_dim_minilm_l6_v2_e_384() -> None:
    assert DIM_MINILM_L6_V2 == 384


# ---------------------------------------------------------------------------
# chave_cache
# ---------------------------------------------------------------------------


def test_chave_cache_determinismo() -> None:
    a = chave_cache(["alpha", "beta"], modelo_nome=MODELO_PADRAO)
    b = chave_cache(["alpha", "beta"], modelo_nome=MODELO_PADRAO)
    assert a == b


def test_chave_cache_textos_diferentes_geram_chaves_diferentes() -> None:
    a = chave_cache(["alpha", "beta"], modelo_nome=MODELO_PADRAO)
    b = chave_cache(["alpha", "gamma"], modelo_nome=MODELO_PADRAO)
    assert a != b


def test_chave_cache_modelos_diferentes_geram_chaves_diferentes() -> None:
    a = chave_cache(["alpha"], modelo_nome="modelo-x")
    b = chave_cache(["alpha"], modelo_nome="modelo-y")
    assert a != b


def test_chave_cache_ordem_dos_textos_importa() -> None:
    a = chave_cache(["alpha", "beta"], modelo_nome=MODELO_PADRAO)
    b = chave_cache(["beta", "alpha"], modelo_nome=MODELO_PADRAO)
    assert a != b


def test_chave_cache_eh_string_hex_estavel() -> None:
    chave = chave_cache(["alpha"], modelo_nome=MODELO_PADRAO)
    assert isinstance(chave, str)
    assert len(chave) >= 16
    int(chave, 16)  # parseable como hex


# ---------------------------------------------------------------------------
# gerar_embeddings — shape e normalização
# ---------------------------------------------------------------------------


def test_gerar_embeddings_shape_correto(
    tmp_path: Path, encoder_factory: Callable[[], FakeEncoder]
) -> None:
    textos = [f"texto_{i}" for i in range(7)]
    arr = gerar_embeddings(textos, cache_dir=tmp_path, encoder_factory=encoder_factory)
    assert arr.shape == (7, DIM_MINILM_L6_V2)
    assert arr.dtype == np.float32


def test_gerar_embeddings_normalizados_l2(
    tmp_path: Path, encoder_factory: Callable[[], FakeEncoder]
) -> None:
    textos = [f"texto_{i}" for i in range(5)]
    arr = gerar_embeddings(textos, cache_dir=tmp_path, encoder_factory=encoder_factory)
    normas = np.linalg.norm(arr, axis=1)
    np.testing.assert_allclose(normas, np.ones(5), atol=1e-6)


def test_gerar_embeddings_lista_vazia_retorna_array_vazio(
    tmp_path: Path, encoder_factory: Callable[[], FakeEncoder]
) -> None:
    arr = gerar_embeddings([], cache_dir=tmp_path, encoder_factory=encoder_factory)
    assert arr.shape == (0, DIM_MINILM_L6_V2)


# ---------------------------------------------------------------------------
# Cache: hit / miss / reprodutibilidade
# ---------------------------------------------------------------------------


def test_gerar_embeddings_cache_miss_chama_encoder_e_salva(
    tmp_path: Path,
) -> None:
    enc = FakeEncoder()
    arr = gerar_embeddings(
        ["a", "b"],
        cache_dir=tmp_path,
        encoder_factory=lambda: enc,
    )
    assert enc.chamadas == 1
    # arquivo de cache foi criado
    arquivos_cache = list(tmp_path.glob("*.npy"))
    assert len(arquivos_cache) == 1
    assert arr.shape == (2, DIM_MINILM_L6_V2)


def test_gerar_embeddings_cache_hit_pula_encoder(tmp_path: Path) -> None:
    enc1 = FakeEncoder()
    enc2 = FakeEncoder()

    arr_primeira = gerar_embeddings(
        ["a", "b"],
        cache_dir=tmp_path,
        encoder_factory=lambda: enc1,
    )
    arr_segunda = gerar_embeddings(
        ["a", "b"],
        cache_dir=tmp_path,
        encoder_factory=lambda: enc2,
    )

    # Primeira chamada paga; segunda é cache hit.
    assert enc1.chamadas == 1
    assert enc2.chamadas == 0
    np.testing.assert_array_equal(arr_primeira, arr_segunda)


def test_gerar_embeddings_input_diferente_recalcula(tmp_path: Path) -> None:
    enc = FakeEncoder()
    factory = lambda: enc  # noqa: E731

    arr1 = gerar_embeddings(["a", "b"], cache_dir=tmp_path, encoder_factory=factory)
    arr2 = gerar_embeddings(["a", "c"], cache_dir=tmp_path, encoder_factory=factory)

    assert enc.chamadas == 2
    assert arr1.shape == arr2.shape
    # Pelo menos uma posição deve diferir (textos diferentes).
    assert not np.array_equal(arr1, arr2)


def test_gerar_embeddings_reprodutivel_entre_processos_simulados(
    tmp_path: Path,
) -> None:
    """Dois encoders independentes constroem o mesmo array para os mesmos textos."""
    arr1 = gerar_embeddings(["x", "y", "z"], cache_dir=tmp_path, encoder_factory=FakeEncoder)
    # Apaga cache pra forçar regeneração
    for f in tmp_path.glob("*.npy"):
        f.unlink()
    arr2 = gerar_embeddings(["x", "y", "z"], cache_dir=tmp_path, encoder_factory=FakeEncoder)
    np.testing.assert_array_equal(arr1, arr2)


def test_gerar_embeddings_modelos_diferentes_caches_diferentes(tmp_path: Path) -> None:
    """Mesma input com `modelo_nome` diferente gera caches separados."""
    enc = FakeEncoder()
    factory = lambda: enc  # noqa: E731

    gerar_embeddings(["a"], cache_dir=tmp_path, encoder_factory=factory, modelo_nome="modelo-1")
    gerar_embeddings(["a"], cache_dir=tmp_path, encoder_factory=factory, modelo_nome="modelo-2")

    assert enc.chamadas == 2
    assert len(list(tmp_path.glob("*.npy"))) == 2
