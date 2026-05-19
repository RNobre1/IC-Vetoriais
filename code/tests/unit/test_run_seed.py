"""Testes da parte pura do CLI `benchmarks.run_seed` (TDD).

`run_seed` apenas semeia N embeddings nos SGBDs (sem benchmark) — usado por
`make seed` e pelo critério de pronto #2 da Etapa 2. A orquestração I/O é
coberta pelos smokes de seeder/cenário; aqui só `parse_args`.
"""

from __future__ import annotations

import pytest

from benchmarks.run_seed import ConfigSeed, parse_args


def test_defaults() -> None:
    cfg = parse_args([])
    assert isinstance(cfg, ConfigSeed)
    assert cfg.n_base == 10_000
    assert cfg.sistemas == ["pgvector", "qdrant", "weaviate"]


def test_custom() -> None:
    cfg = parse_args(["--n", "100000", "--sistemas", "pgvector"])
    assert cfg.n_base == 100_000
    assert cfg.sistemas == ["pgvector"]


def test_rejeita_n_nao_positivo() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--n", "0"])


def test_rejeita_sistema_desconhecido() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--sistemas", "pgvector,redis"])
