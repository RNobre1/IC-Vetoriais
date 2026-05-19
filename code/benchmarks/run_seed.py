"""CLI `run_seed` — semeia N embeddings nos SGBDs, sem benchmark.

Usado por `make seed N=...` e pelo critério de pronto #2 da Etapa 2 (medir
tempo de carga isoladamente). Reusa o pipeline e os helpers do CLI do
Cenário A (`_construir_buscador`/`_limpar_recurso`/`_seed`) — seed idempotente
(limpa o recurso antes de recriar).

Uso:
    python -m benchmarks.run_seed --n 100000 --sistemas pgvector,qdrant,weaviate

Parte pura (`parse_args`) tem teste unitário; a orquestração (`executar`) é
coberta pelos smokes de seeder/cenário.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from benchmarks.run_cenario_a import (
    SISTEMAS_VALIDOS,
    _construir_buscador,
    _limpar_recurso,
    _seed,
)


@dataclass(frozen=True, slots=True)
class ConfigSeed:
    n_base: int = 10_000
    sistemas: list[str] = field(default_factory=lambda: list(SISTEMAS_VALIDOS))
    ms_marco_dir: Path = Path("../data/ms_marco")
    embeddings_dir: Path = Path("../data/embeddings")
    colecao_prefixo: str = "seed"


def parse_args(argv: Sequence[str]) -> ConfigSeed:
    """Converte argv em `ConfigSeed`. SystemExit em entrada inválida."""
    p = argparse.ArgumentParser(prog="run_seed", description="Semeia N embeddings.")
    p.add_argument("--n", type=int, default=10_000, help="nº de vetores a semear.")
    p.add_argument(
        "--sistemas",
        type=lambda s: [x.strip() for x in s.split(",") if x.strip()],
        default=list(SISTEMAS_VALIDOS),
    )
    p.add_argument("--ms-marco-dir", type=Path, default=Path("../data/ms_marco"))
    p.add_argument("--embeddings-dir", type=Path, default=Path("../data/embeddings"))
    a = p.parse_args(argv)

    if a.n <= 0:
        p.error(f"--n deve ser > 0 (recebido {a.n}).")
    desconhecidos = set(a.sistemas) - set(SISTEMAS_VALIDOS)
    if desconhecidos:
        p.error(f"sistemas desconhecidos: {sorted(desconhecidos)}. Válidos: {SISTEMAS_VALIDOS}.")

    return ConfigSeed(
        n_base=a.n,
        sistemas=a.sistemas,
        ms_marco_dir=a.ms_marco_dir,
        embeddings_dir=a.embeddings_dir,
    )


def executar(cfg: ConfigSeed) -> dict[str, int]:
    """Semeia `cfg.n_base` vetores em cada sistema. Retorna {sistema: n}."""
    from dotenv import load_dotenv

    from pipeline.embeddings import gerar_embeddings
    from pipeline.ms_marco_loader import sample_passages

    load_dotenv()
    env = dict(os.environ)

    tsv = cfg.ms_marco_dir / "collection.tsv"
    passages = sample_passages(tsv, n=cfg.n_base)
    embs = gerar_embeddings([p.text for p in passages], cache_dir=cfg.embeddings_dir)

    contagens: dict[str, int] = {}
    for sistema in cfg.sistemas:
        nome_recurso = (
            f"{cfg.colecao_prefixo}_{cfg.n_base}" if sistema != "weaviate" else f"Seed{cfg.n_base}"
        )
        _, recurso = _construir_buscador(sistema, nome_recurso=nome_recurso, env=env)
        try:
            _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome_recurso)
            _seed(sistema, vetores=embs, recurso=recurso, nome_recurso=nome_recurso)
            contagens[sistema] = embs.shape[0]
        finally:
            if hasattr(recurso, "close"):
                recurso.close()
    return contagens


def main(argv: Sequence[str] | None = None) -> int:
    import sys

    cfg = parse_args(sys.argv[1:] if argv is None else argv)
    contagens = executar(cfg)
    for sistema, n in contagens.items():
        print(f"{sistema}: {n} vetores semeados (recurso '{cfg.colecao_prefixo}_{cfg.n_base}')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
