"""Geração de embeddings com cache local e dependency injection do encoder.

API pública:
- `MODELO_PADRAO`, `DIM_MINILM_L6_V2` — constantes do modelo escolhido pela ADR
  [[../../vault/decisões/2026-04-28-modelo-embedding-minilm]].
- `chave_cache(textos, *, modelo_nome)` — chave de cache determinística.
- `gerar_embeddings(textos, *, modelo_nome, cache_dir, encoder_factory)` — gera
  ou recupera embeddings normalizados L2.

O parâmetro `encoder_factory` torna o módulo testável sem `sentence-transformers`
instalado: testes injetam um fake; o factory padrão (carregado lazy) constrói
um `SentenceTransformer` real.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import numpy as np

MODELO_PADRAO = "sentence-transformers/all-MiniLM-L6-v2"
DIM_MINILM_L6_V2 = 384


class _Encoder(Protocol):
    """Subset da interface do `sentence_transformers.SentenceTransformer.encode` que usamos."""

    def encode(
        self,
        textos: list[str],
        *,
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ) -> np.ndarray: ...


def _factory_padrao() -> _Encoder:
    """Carrega `SentenceTransformer` lazy — só importa quando chamado de verdade."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODELO_PADRAO)


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------


def chave_cache(textos: list[str], *, modelo_nome: str) -> str:
    """Hash SHA-256 hex de (modelo_nome, textos em ordem). Determinística."""
    h = hashlib.sha256()
    h.update(modelo_nome.encode("utf-8"))
    h.update(b"\x00")
    for t in textos:
        h.update(t.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Geração
# ---------------------------------------------------------------------------


def gerar_embeddings(
    textos: list[str],
    *,
    modelo_nome: str = MODELO_PADRAO,
    cache_dir: Path,
    batch_size: int = 64,
    encoder_factory: Callable[[], _Encoder] = _factory_padrao,
) -> np.ndarray:
    """Gera embeddings normalizados L2 para `textos`.

    - Calcula `chave_cache` a partir de (`modelo_nome`, `textos`).
    - Se `cache_dir/<chave>.npy` existe, retorna do disco e **não** chama o encoder.
    - Caso contrário, instancia um encoder via `encoder_factory()` e calcula.
    - O resultado é salvo em `cache_dir/<chave>.npy` e devolvido.
    - Lista vazia retorna `np.zeros((0, DIM_MINILM_L6_V2), dtype=float32)` sem
      chamar o encoder.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not textos:
        return np.zeros((0, DIM_MINILM_L6_V2), dtype=np.float32)

    chave = chave_cache(textos, modelo_nome=modelo_nome)
    arquivo = cache_dir / f"{chave}.npy"

    if arquivo.exists():
        return np.load(arquivo)

    encoder = encoder_factory()
    arr = encoder.encode(
        textos,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype(np.float32, copy=False)

    np.save(arquivo, arr)
    return arr
