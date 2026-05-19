"""Testes das partes puras do CLI `benchmarks.run_cenario_b` (TDD).

A orquestração I/O (embeddings/Docker) é coberta pelo smoke
`tests/integration/test_buscadores_filtrado.py` + run real. Aqui só a lógica
pura com rede de segurança própria:

- `parse_args`: defaults (inclui grade de seletividades da ADR
  [[../../vault/decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]),
  parsing custom, validação de positividade e de `seletividade ∈ (0, 1]`.
- `sintetizar_seletor`: atributo uniforme determinístico decorrelacionado;
  `seletor < p` ⇒ seletividade `p` (a menos de ±1/N).
"""

from __future__ import annotations

import numpy as np
import pytest

from benchmarks.run_cenario_b import Config, parse_args, sintetizar_seletor

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
    assert cfg.seletividades == [0.01, 0.1, 0.5, 1.0]
    assert cfg.warmup == 50
    assert cfg.sistemas == ["pgvector", "qdrant", "weaviate"]


def test_parse_args_custom() -> None:
    cfg = parse_args(
        [
            "--n",
            "500",
            "--queries",
            "50",
            "--ef-search",
            "16,64",
            "--seletividades",
            "0.05,0.5",
            "--sistemas",
            "qdrant",
        ]
    )
    assert cfg.n_base == 500
    assert cfg.n_queries == 50
    assert cfg.ef_search == [16, 64]
    assert cfg.seletividades == [0.05, 0.5]
    assert cfg.sistemas == ["qdrant"]


def test_parse_args_rejeita_n_nao_positivo() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--n", "0"])


def test_parse_args_rejeita_seletividade_fora_de_0_1() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--seletividades", "0.1,1.5"])
    with pytest.raises(SystemExit):
        parse_args(["--seletividades", "0,0.5"])


def test_parse_args_rejeita_seletividades_vazio() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--seletividades", ""])


# ---------------------------------------------------------------------------
# sintetizar_seletor
# ---------------------------------------------------------------------------


def test_sintetizar_seletor_shape_e_intervalo() -> None:
    sel = sintetizar_seletor(1000)
    assert sel.shape == (1000,)
    assert sel.dtype == np.float64
    assert sel.min() >= 0.0
    assert sel.max() < 1.0


def test_sintetizar_seletor_deterministico() -> None:
    np.testing.assert_array_equal(sintetizar_seletor(500), sintetizar_seletor(500))


def test_sintetizar_seletor_seletividade_exata() -> None:
    n = 10_000
    sel = sintetizar_seletor(n)
    # `seletor < p` ⇒ ~p·N itens (a menos de ±1).
    for p in (0.01, 0.1, 0.5):
        assert abs(int((sel < p).sum()) - round(p * n)) <= 1
    # p = 1.0 mantém todos (âncora = Cenário A sem filtro efetivo).
    assert int((sel < 1.0).sum()) == n


def test_sintetizar_seletor_uniforme_e_unico() -> None:
    n = 2000
    sel = sintetizar_seletor(n)
    # Permutação de {0, 1/N, ..., (N-1)/N}: todos distintos.
    assert len(np.unique(sel)) == n


def test_sintetizar_seletor_decorrelacionado_do_indice() -> None:
    # A permutação quebra a correlação id↔seletor (senão o filtro
    # selecionaria sempre os mesmos vetores em bloco).
    sel = sintetizar_seletor(5000)
    corr = np.corrcoef(np.arange(5000), sel)[0, 1]
    assert abs(corr) < 0.05, f"correlação id↔seletor alta demais: {corr}"
