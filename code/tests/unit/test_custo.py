"""Testes unitários de processamento de custo de recursos (monitor + marcos)."""

from pathlib import Path

from analise.custo import calcular_custo, linhas_custo

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
