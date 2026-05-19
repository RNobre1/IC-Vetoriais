"""Testes do **esqueleto** de `benchmarks.cenario_c` (TDD).

Cenário C (carga mista RAG) só roda de fato na Etapa 4 (datasets de 1M; vide
[[../../vault/decisões/2026-04-28-tamanhos-100k-500k-1m]] e o risco de
hardware no plano da Etapa 2). Aqui validamos apenas o **contrato do
esqueleto**: a estrutura de configuração, a lógica pura do escalonamento de
inserções, e que `executar` recusa rodar carga real nesta etapa.
"""

from __future__ import annotations

import math

import pytest

from benchmarks.cenario_c import (
    TAXAS_INSERCAO_PADRAO,
    ConfigC,
    executar,
    intervalo_entre_insercoes,
)

# ---------------------------------------------------------------------------
# Lógica pura: escalonamento de inserções
# ---------------------------------------------------------------------------


def test_taxa_zero_significa_sem_insercoes() -> None:
    # Taxa 0 ins/s = leitura pura (baseline) → intervalo infinito.
    assert intervalo_entre_insercoes(0) == math.inf


def test_intervalo_e_inverso_da_taxa() -> None:
    assert intervalo_entre_insercoes(10) == pytest.approx(0.1)
    assert intervalo_entre_insercoes(1000) == pytest.approx(0.001)


def test_taxa_negativa_invalida() -> None:
    with pytest.raises(ValueError, match="taxa"):
        intervalo_entre_insercoes(-1)


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------


def test_config_defaults() -> None:
    cfg = ConfigC()
    assert cfg.taxas_insercao == list(TAXAS_INSERCAO_PADRAO)
    assert cfg.taxas_insercao == [0, 10, 100, 1000]
    assert cfg.k == 10
    assert cfg.n_base > 0


# ---------------------------------------------------------------------------
# Esqueleto não roda carga real na Etapa 2
# ---------------------------------------------------------------------------


def test_executar_recusa_carga_real_nesta_etapa() -> None:
    with pytest.raises(NotImplementedError, match="Etapa 4"):
        executar(ConfigC())
