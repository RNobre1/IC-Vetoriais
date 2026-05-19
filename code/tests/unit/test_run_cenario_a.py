"""Testes das partes puras do CLI `benchmarks.run_cenario_a` (TDD).

O CLI é majoritariamente cola I/O (download/embeddings/Docker), coberta
ponta-a-ponta pelo smoke `tests/integration/test_buscadores.py`. Aqui
testamos só o que é lógica pura e merece rede de segurança própria:

- `parse_args`: defaults da ADR [[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]]
  (sweep efSearch, warmup), parsing custom e validação de positividade.
- `split_embeddings`: split determinístico base / queries held-out.
- `timestamp_utc`: string ISO FS-safe (sem `:`), sufixo `Z`.
"""

from __future__ import annotations

import re

import numpy as np
import pytest

from benchmarks.run_cenario_a import (
    Config,
    parse_args,
    split_embeddings,
    timestamp_utc,
)

# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


def test_parse_args_defaults() -> None:
    cfg = parse_args([])
    assert isinstance(cfg, Config)
    assert cfg.n_base == 10_000
    assert cfg.n_queries == 1_000
    assert cfg.k == 10
    assert cfg.ef_search == [16, 32, 64, 128, 256]
    assert cfg.warmup == 50
    assert cfg.sistemas == ["pgvector", "qdrant", "weaviate"]


def test_parse_args_custom() -> None:
    cfg = parse_args(
        [
            "--n",
            "500",
            "--queries",
            "50",
            "--k",
            "5",
            "--ef-search",
            "16,64",
            "--warmup",
            "10",
            "--sistemas",
            "pgvector,qdrant",
        ]
    )
    assert cfg.n_base == 500
    assert cfg.n_queries == 50
    assert cfg.k == 5
    assert cfg.ef_search == [16, 64]
    assert cfg.warmup == 10
    assert cfg.sistemas == ["pgvector", "qdrant"]


def test_parse_args_rejeita_n_nao_positivo() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--n", "0"])


def test_parse_args_rejeita_warmup_negativo() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--warmup", "-1"])


def test_parse_args_rejeita_sistema_desconhecido() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--sistemas", "pgvector,mongodb"])


def test_parse_args_rejeita_ef_search_nao_inteiro() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--ef-search", "16,abc"])


# ---------------------------------------------------------------------------
# split_embeddings
# ---------------------------------------------------------------------------


def test_split_embeddings_shapes_e_ordem() -> None:
    embs = np.arange(30 * 4, dtype=np.float32).reshape(30, 4)
    base, queries = split_embeddings(embs, n_base=20, n_queries=8)
    assert base.shape == (20, 4)
    assert queries.shape == (8, 4)
    # base = primeiros 20; queries = held-out (20..28), não sobrepõem o seed
    np.testing.assert_array_equal(base, embs[:20])
    np.testing.assert_array_equal(queries, embs[20:28])


def test_split_embeddings_deterministico() -> None:
    embs = np.random.default_rng(1).standard_normal((50, 8)).astype(np.float32)
    b1, q1 = split_embeddings(embs, n_base=30, n_queries=10)
    b2, q2 = split_embeddings(embs, n_base=30, n_queries=10)
    np.testing.assert_array_equal(b1, b2)
    np.testing.assert_array_equal(q1, q2)


def test_split_embeddings_levanta_se_insuficiente() -> None:
    embs = np.zeros((25, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="insuficiente"):
        split_embeddings(embs, n_base=20, n_queries=10)  # precisa de 30, tem 25


# ---------------------------------------------------------------------------
# timestamp_utc
# ---------------------------------------------------------------------------


def test_timestamp_utc_formato_fs_safe() -> None:
    ts = timestamp_utc()
    # 2026-05-10T18-30-00Z — sem ':' (FS-safe), termina em Z
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z", ts), ts
    assert ":" not in ts
