"""Testes do modo equalizado do CLI do Cenário B.

A execução de julho/2026 comparou os três sistemas em condições desiguais:
o Qdrant recebeu índice de payload em `seletor`, o pgvector ficou sem índice
nenhum no atributo de filtro, e Qdrant e Weaviate responderam as seletividades
baixas por **busca exata** (fallback de `full_scan_threshold` / `flatSearchCutoff`)
em vez de ANN. O `--equalizado` existe para tornar a comparação válida.

É um flag único, e não três independentes, de propósito: a equalização é uma
decisão metodológica só coerente por inteiro — meia equalização produz um
terceiro regime, diferente tanto do default quanto do equalizado, e ninguém
saberia dizer qual está lendo no JSON de saída.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from benchmarks.run_cenario_b import _seed_b, nome_classe_weaviate, parse_args


@pytest.fixture
def vetores() -> np.ndarray:
    rng = np.random.default_rng(3)
    arr = rng.normal(size=(4, 4)).astype(np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    return arr


@pytest.fixture
def metadata() -> list[dict[str, Any]]:
    return [{"seletor": i / 4.0} for i in range(4)]


@pytest.fixture
def capturas(monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    """Substitui os três seeders por espiões que registram os kwargs."""
    registro: dict[str, dict[str, Any]] = {}

    def espiao(nome: str):
        def _fn(**kwargs: Any) -> int:
            registro[nome] = kwargs
            return 0

        return _fn

    monkeypatch.setattr("seeders.pgvector_seeder.seed_pgvector", espiao("pgvector"))
    monkeypatch.setattr("seeders.qdrant_seeder.seed_qdrant", espiao("qdrant"))
    monkeypatch.setattr("seeders.weaviate_seeder.seed_weaviate", espiao("weaviate"))
    return registro


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


def test_default_nao_e_equalizado():
    """Sem o flag, reproduz exatamente o que rodou em julho/2026."""
    assert parse_args([]).equalizado is False


def test_flag_liga_equalizacao():
    assert parse_args(["--equalizado"]).equalizado is True


def test_equalizado_usa_prefixo_proprio():
    """Recursos separados: um re-run não pode sobrescrever a base do default."""
    assert parse_args(["--equalizado"]).colecao_prefixo != parse_args([]).colecao_prefixo


def test_nome_weaviate_preserva_o_historico():
    """O prefixo default precisa continuar produzindo exatamente `BenchB`."""
    assert nome_classe_weaviate("bench_b") == "BenchB"


def test_nome_weaviate_separa_o_equalizado():
    """Sem isso, a classe Weaviate colidiria com a base do modo default."""
    assert nome_classe_weaviate("bench_b_eq") == "BenchBEq"


# ---------------------------------------------------------------------------
# _seed_b
# ---------------------------------------------------------------------------


def test_seed_qdrant_equalizado_minimiza_full_scan_threshold(vetores, metadata, capturas):
    """O Qdrant rejeita 0 (HTTP 422); o mínimo aceito é 10 KB (~7 vetores 384-D)."""
    from seeders.qdrant_seeder import FULL_SCAN_MINIMO

    _seed_b(
        "qdrant",
        vetores=vetores,
        metadata=metadata,
        recurso=object(),
        nome_recurso="c",
        equalizado=True,
    )
    assert capturas["qdrant"]["full_scan_threshold"] == FULL_SCAN_MINIMO


def test_seed_weaviate_equalizado_zera_flat_search_cutoff(vetores, metadata, capturas):
    _seed_b(
        "weaviate",
        vetores=vetores,
        metadata=metadata,
        recurso=object(),
        nome_recurso="C",
        equalizado=True,
    )
    assert capturas["weaviate"]["flat_search_cutoff"] == 0


def test_seed_pgvector_equalizado_indexa_seletor(vetores, metadata, capturas):
    _seed_b(
        "pgvector",
        vetores=vetores,
        metadata=metadata,
        recurso=object(),
        nome_recurso="t",
        equalizado=True,
    )
    assert capturas["pgvector"]["indexar_seletor"] is True


def test_seed_default_preserva_configuracao_de_julho(vetores, metadata, capturas):
    """Sem equalização, nenhum limiar é tocado — reprodutibilidade do histórico."""
    for sistema, nome in [("qdrant", "c"), ("weaviate", "C"), ("pgvector", "t")]:
        _seed_b(
            sistema,
            vetores=vetores,
            metadata=metadata,
            recurso=object(),
            nome_recurso=nome,
            equalizado=False,
        )
    assert capturas["qdrant"].get("full_scan_threshold") is None
    assert capturas["weaviate"].get("flat_search_cutoff") is None
    assert capturas["pgvector"].get("indexar_seletor", False) is False
