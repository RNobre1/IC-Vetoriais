"""Testes unitários de processamento de custo de recursos (monitor + marcos)."""

from pathlib import Path

from analise.custo import (
    FASES_RELEVANTES,
    MetricaCustoFase,
    calcular_custo,
    linhas_custo,
)

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
    assert r"\multirow{1}{*}{pgvector}" in linhas
    assert "seed A" in linhas
    assert "120,0" in linhas
    assert "60,0" in linhas
    assert "1,0" in linhas
    assert "4,5" in linhas
    assert r"\hline" in linhas


def test_linhas_custo_ordenacao_e_multirows():
    # Cria métricas mock para testar:
    # 1. multirow por escala E por sistema
    # 2. nomes de exibição (pgvector, Qdrant, Weaviate)
    # 3. nomes e ordem das fases (seeds primeiro: seed A, seed B, seed B eq., depois A, B, B eq., C)
    # 4. \cline{2-7} entre sistemas na mesma escala
    m1 = MetricaCustoFase(100000, "pgvector", "B", 800.0, 10.0, 1.0, 0, 0.0, 0.0, 1000.0)
    m2 = MetricaCustoFase(100000, "pgvector", "seed_b", 850.0, 60.0, 2.0, 0, 0.5, 0.0, 900.0)
    m3 = MetricaCustoFase(100000, "pgvector", "A", 820.0, 12.0, 1.0, 0, 0.0, 0.0, 950.0)
    m4 = MetricaCustoFase(100000, "qdrant", "seed_a", 900.0, 400.0, 2.0, 0, 0.0, 0.0, 800.0)
    m5 = MetricaCustoFase(100000, "qdrant", "A", 750.0, 300.0, 1.0, 0, 0.0, 0.0, 850.0)

    linhas = linhas_custo([m1, m2, m3, m4, m5])

    # Escala tem total de 5 linhas
    assert r"\multirow{5}{*}{100k}" in linhas
    # pgvector tem 3 linhas
    assert r"\multirow{3}{*}{pgvector}" in linhas
    # qdrant tem 2 linhas e nome de exibição Qdrant
    assert r"\multirow{2}{*}{Qdrant}" in linhas

    # Ordem das fases do pgvector: seed B antes de A e B
    pos_seed_b = linhas.find("seed B")
    pos_a = linhas.find(" & & A &")
    pos_b = linhas.find(" & & B &")
    assert pos_seed_b != -1 and pos_a != -1 and pos_b != -1
    assert pos_seed_b < pos_a < pos_b

    # Divisão entre sistemas com \cline{2-7}
    assert r"\cline{2-7}" in linhas
    # Fim da escala com \hline
    assert r"\hline" in linhas


def test_linhas_custo_sem_escala():
    m1 = MetricaCustoFase(100000, "pgvector", "B", 800.0, 10.0, 1.0, 0, 0.0, 0.0, 1000.0)
    m2 = MetricaCustoFase(100000, "pgvector", "seed_b", 850.0, 60.0, 2.0, 0, 0.5, 0.0, 900.0)
    m3 = MetricaCustoFase(100000, "qdrant", "A", 750.0, 300.0, 1.0, 0, 0.0, 0.0, 850.0)

    linhas = linhas_custo([m1, m2, m3], incluir_escala=False)
    # Não deve ter multirow de escala nem menção a 100k
    assert r"\multirow{3}{*}{100k}" not in linhas
    assert "100k" not in linhas

    # Começa direto no multirow do sistema
    assert linhas.startswith(r"\multirow{2}{*}{pgvector} & seed B")
    assert " & B &" in linhas
    assert r"\hline" in linhas
    assert r"\multirow{1}{*}{Qdrant} & A &" in linhas


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
