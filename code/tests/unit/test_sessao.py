"""Testes unitários de carregamento e classificação da sessão experimental."""

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
