"""Testes unitários de carregamento e classificação da sessão experimental."""

import json
from pathlib import Path

from analise.sessao import carregar_arquivos, carregar_sessao

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "analise"


def test_carregar_sessao_janela_e_classificacao():
    results_dir = FIXTURES_DIR / "jsons"
    marcos_path = FIXTURES_DIR / "marcos.jsonl"

    sessao = carregar_sessao(results_dir, marcos_path)

    # 1. Arquivo fora da janela (13:00:00Z) deve ser excluído
    assert sessao.obter("A", "weaviate", 5000) is None

    # 2. Arquivo A com protocolo sessao-2026-11
    a_pg = sessao.obter("A", "pgvector", 5000)
    assert a_pg is not None
    assert a_pg.condicao == "A"
    assert a_pg.timestamp_utc == "2026-11-15T14:51:40Z"

    # 3. Chave repetida deve manter o mais recente e avisar
    assert any("repetida" in aviso.lower() for aviso in sessao.avisos)
    assert a_pg.dados["timestamp_utc"] == "2026-11-15T14:51:40Z"

    # 4. Arquivo A sem protocolo dentro da janela vira A_ponte
    ponte = sessao.obter("A_ponte", "qdrant", 100000)
    assert ponte is not None
    assert ponte.condicao == "A_ponte"

    # 5. Cenário B padrão (equalizado == False)
    b_padrao = sessao.obter("B_padrao", "pgvector", 5000)
    assert b_padrao is not None
    assert b_padrao.condicao == "B_padrao"

    # 6. Cenário B equalizado (equalizado == True)
    b_eq = sessao.obter("B_eq", "pgvector", 5000)
    assert b_eq is not None
    assert b_eq.condicao == "B_eq"

    # 7. Cenário C
    c_pg = sessao.obter("C", "pgvector", 5000)
    assert c_pg is not None
    assert c_pg.condicao == "C"

    # Escalas presentes
    assert sessao.escalas == [5000, 100000]


def test_carregar_arquivos_sem_marcos():
    path_anterior = FIXTURES_DIR / "anterior_A_100k.json"
    sessao_ant = carregar_arquivos([path_anterior])

    a_ant = sessao_ant.obter("A", "pgvector", 100000)
    assert a_ant is not None
    assert a_ant.condicao == "A"
    assert a_ant.n == 100000
    assert a_ant.timestamp_utc == "2026-08-23T15:08:57Z"


def test_carregar_sessao_regressao_ponte_marcos_todos(tmp_path):
    # Regressão: marcos com passo: "ponte", sistema: "todos" antes do primeiro bloco
    # fazem carregar_sessao encontrar A_ponte para os 3 sistemas (JSONs da ponte SEM a chave protocolo no ambiente)
    marcos_p = tmp_path / "marcos.jsonl"
    marcos_p.write_text(
        '{"ts_utc": "2026-11-15T10:00:00Z", "evento": "inicio", "passo": "ponte", "sistema": "todos", "n": 100000}\n'
        '{"ts_utc": "2026-11-15T10:15:00Z", "evento": "fim", "passo": "ponte", "sistema": "todos", "n": 100000}\n'
        '{"ts_utc": "2026-11-15T10:20:00Z", "evento": "inicio", "passo": "bloco", "sistema": "pgvector", "n": 100000}\n'
        '{"ts_utc": "2026-11-15T10:30:00Z", "evento": "fim", "passo": "bloco", "sistema": "pgvector", "n": 100000}\n',
        encoding="utf-8",
    )
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    for i, sis in enumerate(("pgvector", "qdrant", "weaviate"), start=1):
        d = {
            "cenario": "A",
            "sistema": sis,
            "n": 100000,
            "timestamp_utc": f"2026-11-15T10:0{i}:00Z",
            "ambiente": {},  # SEM protocolo
            "pontos": [{"metricas": {"recall_at_k": 0.98, "qps": 500.0}}],
        }
        (results_dir / f"cenario_A_{sis}_100000_ponte.json").write_text(
            json.dumps(d), encoding="utf-8"
        )

    # JSON do protocolo novo durante o bloco para pgvector
    d_novo = {
        "cenario": "A",
        "sistema": "pgvector",
        "n": 100000,
        "timestamp_utc": "2026-11-15T10:25:00Z",
        "ambiente": {"protocolo": "sessao-2026-11"},
        "pontos": [{"metricas": {"recall_at_k": 0.99, "qps": 600.0}}],
    }
    (results_dir / "cenario_A_pgvector_100000_novo.json").write_text(
        json.dumps(d_novo), encoding="utf-8"
    )

    sessao = carregar_sessao(results_dir, marcos_p)

    for sis in ("pgvector", "qdrant", "weaviate"):
        arq_ponte = sessao.obter("A_ponte", sis, 100000)
        assert arq_ponte is not None
        assert arq_ponte.condicao == "A_ponte"
        assert arq_ponte.sistema == sis

    arq_a = sessao.obter("A", "pgvector", 100000)
    assert arq_a is not None
    assert arq_a.condicao == "A"


def test_carregar_sessao_marcos_linha_corrompida(tmp_path):
    marcos_p = tmp_path / "marcos.jsonl"
    marcos_p.write_text(
        '{"ts_utc": "2026-11-15T10:00:00Z", "evento": "inicio", "passo": "bloco", "sistema": "pgvector", "n": 5000}\n'
        "LINHA_CORROMPIDA_NAO_JSON\n"
        '{"ts_utc": "2026-11-15T10:10:00Z", "evento": "fim", "passo": "bloco", "sistema": "pgvector", "n": 5000}\n',
        encoding="utf-8",
    )
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    sessao = carregar_sessao(results_dir, marcos_p)
    assert any("corrompida" in a.lower() for a in sessao.avisos)
