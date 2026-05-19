"""Normalização e persistência da saída dos benchmarks.

Três peças:
- `ResultadoBenchmark`: registro imutável de uma execução (metadados +
  parâmetros + métricas + ambiente).
- `salvar_resultado(...)`: serializa para JSON UTF-8 determinístico em
  `code/results/`, com nome de arquivo previsível.
- `salvar_ground_truth` / `carregar_ground_truth`: round-trip do top-K exato
  (de `ground_truth.exact_search.top_k_exato`) em `data/ground_truth/` como `.npz`.

Reprodutibilidade: `sort_keys=True` (diff estável), `ensure_ascii=False`
(PT-BR sem escapes `\\uXXXX`), nome de arquivo função pura dos metadados.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class ResultadoBenchmark:
    """Registro imutável de uma execução de benchmark.

    `parametros` (ef_search, m, ef_construction, k, ...), `metricas`
    (p50, p95, p99, qps, recall_at_k, ...) e `ambiente` (imagem do SGBD,
    host, ...) são dicts livres — o schema é fixado por convenção dos
    cenários, não por este módulo, para não acoplar reporting a um cenário.
    """

    cenario: str
    sistema: str
    n: int
    timestamp_utc: str
    parametros: dict[str, Any] = field(default_factory=dict)
    metricas: dict[str, Any] = field(default_factory=dict)
    ambiente: dict[str, Any] = field(default_factory=dict)


def _slug_timestamp(timestamp_utc: str) -> str:
    """Torna o timestamp seguro para nome de arquivo (`:` é inválido em alguns FS)."""
    return timestamp_utc.replace(":", "-")


def salvar_resultado(resultado: ResultadoBenchmark, *, results_dir: Path) -> Path:
    """Grava `resultado` como JSON em `results_dir`. Retorna o caminho escrito.

    Nome: `cenario_<cenario>_<sistema>_<n>_<timestamp-slug>.json`.
    JSON com `indent=2`, `sort_keys=True`, `ensure_ascii=False`, newline final.
    Cria `results_dir` (e pais) se não existir.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    nome = (
        f"cenario_{resultado.cenario}_{resultado.sistema}_"
        f"{resultado.n}_{_slug_timestamp(resultado.timestamp_utc)}.json"
    )
    caminho = results_dir / nome
    payload = dataclasses.asdict(resultado)
    caminho.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return caminho


def salvar_ground_truth(
    scores: np.ndarray,
    ids: np.ndarray,
    *,
    dest_dir: Path,
    nome: str,
) -> Path:
    """Persiste o top-K exato `(scores, ids)` em `dest_dir/<nome>.npz`.

    `scores` e `ids` precisam ser 2-D e ter o mesmo shape `(M, K)`.
    Cria `dest_dir` se não existir. Retorna o caminho `.npz`.
    """
    if scores.ndim != 2 or ids.ndim != 2:
        raise ValueError("`scores` e `ids` precisam ser arrays 2-D.")
    if scores.shape != ids.shape:
        raise ValueError(f"shape divergente: scores={scores.shape}, ids={ids.shape}.")
    dest_dir.mkdir(parents=True, exist_ok=True)
    caminho = dest_dir / f"{nome}.npz"
    np.savez(caminho, scores=scores, ids=ids)
    return caminho


def carregar_ground_truth(caminho: Path) -> tuple[np.ndarray, np.ndarray]:
    """Lê um `.npz` salvo por `salvar_ground_truth`. Retorna `(scores, ids)`."""
    with np.load(caminho) as dados:
        return dados["scores"], dados["ids"]
