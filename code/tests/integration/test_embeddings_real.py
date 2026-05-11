"""Integração com o encoder REAL (sentence-transformers).

Diferente dos testes unitários em `tests/unit/test_embeddings.py`, aqui exercemos o
caminho de produção: o factory padrão constrói um `SentenceTransformer` real,
faz o download do modelo (cache em `~/.cache/huggingface/`) e gera embeddings.

Requer:
- `sentence-transformers` instalado (Pré-Dia 3 da Etapa 2).
- Conexão à internet **apenas na primeira execução** (download do modelo, ~80 MB).
- O teste de subset MS MARCO pede `data/ms_marco/collection.tsv` descompactado;
  se ausente, é pulado com mensagem clara.

Marcadores:
- `slow`: primeira execução leva tempo (download do modelo + warmup do torch).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pipeline.embeddings import (
    DIM_MINILM_L6_V2,
    MODELO_PADRAO,
    chave_cache,
    gerar_embeddings,
)
from pipeline.ms_marco_loader import sample_passages

pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Sanity do encoder real
# ---------------------------------------------------------------------------


def test_encoder_real_produz_shape_dtype_e_norma_l2(tmp_path: Path) -> None:
    """Caminho de produção: factory padrão importa sentence-transformers."""
    textos = ["hello world", "outra frase de teste"]

    embs = gerar_embeddings(textos, cache_dir=tmp_path)

    assert embs.shape == (2, DIM_MINILM_L6_V2)
    assert embs.dtype == np.float32

    normas = np.linalg.norm(embs, axis=1)
    np.testing.assert_allclose(normas, np.ones(2), atol=1e-5)


def test_encoder_real_grava_arquivo_de_cache(tmp_path: Path) -> None:
    """A primeira chamada deve persistir `<chave>.npy` em `cache_dir`."""
    textos = ["frase única para isolar a chave"]

    gerar_embeddings(textos, cache_dir=tmp_path)

    chave = chave_cache(textos, modelo_nome=MODELO_PADRAO)
    arquivo = tmp_path / f"{chave}.npy"
    assert arquivo.exists()
    persistido = np.load(arquivo)
    assert persistido.shape == (1, DIM_MINILM_L6_V2)


def test_segunda_chamada_usa_cache_e_nao_invoca_encoder(tmp_path: Path) -> None:
    """Após a primeira chamada gravar o cache, a segunda não pode instanciar encoder."""
    textos = ["frase para verificar reuso de cache"]
    gerar_embeddings(textos, cache_dir=tmp_path)

    def factory_que_falha() -> object:
        raise AssertionError("encoder_factory não deveria ser chamado em cache hit")

    embs = gerar_embeddings(textos, cache_dir=tmp_path, encoder_factory=factory_que_falha)
    assert embs.shape == (1, DIM_MINILM_L6_V2)


# ---------------------------------------------------------------------------
# Subset MS MARCO (alimenta a primeira nota em vault/experimentos/)
# ---------------------------------------------------------------------------


COLLECTION_TSV = Path(__file__).resolve().parents[2].parent / "data" / "ms_marco" / "collection.tsv"


@pytest.mark.skipif(
    not COLLECTION_TSV.exists(),
    reason=f"collection.tsv não encontrado em {COLLECTION_TSV} (descompactar primeiro).",
)
def test_encoder_real_em_subset_ms_marco_100_passages(tmp_path: Path) -> None:
    """Geração ponta-a-ponta: loader → embeddings, com N=100, em um subset reproduzível."""
    passages = sample_passages(COLLECTION_TSV, n=100)
    assert len(passages) == 100
    textos = [p.text for p in passages]

    embs = gerar_embeddings(textos, cache_dir=tmp_path)

    assert embs.shape == (100, DIM_MINILM_L6_V2)
    assert embs.dtype == np.float32
    normas = np.linalg.norm(embs, axis=1)
    np.testing.assert_allclose(normas, np.ones(100), atol=1e-5)
