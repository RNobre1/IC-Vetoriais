"""Testes unitários de processamento de custo de recursos (monitor + marcos)."""

from pathlib import Path

from analise.custo import FASES_RELEVANTES, calcular_custo, linhas_custo

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "analise"


def test_calcular_custo_e_linhas():
    csv_path = FIXTURES_DIR / "monitor_synthetic.csv"
    marcos_path = FIXTURES_DIR / "marcos.jsonl"

    metricas = calcular_custo(csv_path, marcos_path)
    assert len(metricas) == 1

    m = metricas[0]
    assert m.n == 5000
    assert m.sistema == "pgvector"
    assert m.passo == "seed_a"
    assert abs(m.pico_mem_mib - 120.0) < 0.1
    assert abs(m.pico_anon_mib - 60.0) < 0.1
    assert abs(m.cpu_nucleos - 1.0) < 0.05
    assert m.swap_out_paginas == 1156
    assert abs(m.swap_out_mib - 4.515625) < 0.01
    assert abs(m.pico_psi_mem_full - 0.05) < 1e-4

    linhas = linhas_custo(metricas)
    assert r"\multirow{1}{*}{5k}" in linhas
    assert "pgvector" in linhas
    assert r"seed\_a" in linhas
    assert "120,0" in linhas
    assert "60,0" in linhas
    assert "1,0" in linhas
    assert "4,5" in linhas
    assert r"\hline" in linhas


def test_calcular_custo_celulas_vazias_e_reinicio():
    csv_path = FIXTURES_DIR / "monitor_vazias.csv"
    marcos_path = FIXTURES_DIR / "marcos_vazias.jsonl"

    # Sem filtrar relevantes para testar 'reiniciar' e 'vazio'
    metricas = calcular_custo(csv_path, marcos_path, somente_relevantes=False)
    # 2 fases: reiniciar e vazio
    assert len(metricas) == 2

    m_reiniciar = next(m for m in metricas if m.passo == "reiniciar")
    assert m_reiniciar.pico_mem_mib is not None
    assert abs(m_reiniciar.pico_mem_mib - 111.96) < 0.1

    # CPU: somando trechos monotônicos válidos
    assert m_reiniciar.cpu_nucleos is not None
    assert m_reiniciar.cpu_nucleos > 0
    assert abs(m_reiniciar.cpu_nucleos - 0.263) < 0.05

    # Fase "vazio": sem nenhuma amostra de contêiner válida
    m_vazio = next(m for m in metricas if m.passo == "vazio")
    assert m_vazio.pico_mem_mib is None
    assert m_vazio.pico_anon_mib is None
    assert m_vazio.cpu_nucleos is None

    # Linhas LaTeX devem renderizar --- para None
    linhas = linhas_custo([m_vazio])
    assert "---" in linhas


def test_calcular_custo_filtra_fases_irrelevantes():
    # Passos como 'bloco', 'reiniciar', 'limpar' não devem entrar se somente_relevantes=True
    csv_path = FIXTURES_DIR / "monitor_vazias.csv"
    marcos_path = FIXTURES_DIR / "marcos_vazias.jsonl"

    metricas = calcular_custo(csv_path, marcos_path, somente_relevantes=True)
    assert len(metricas) == 0  # reiniciar e vazio não estão em FASES_RELEVANTES
    for f in ("bloco", "reiniciar", "limpar", "C_total", "C_recall", "dados", "btree"):
        assert f not in FASES_RELEVANTES
