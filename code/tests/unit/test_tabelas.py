"""Testes unitários dos geradores de linhas LaTeX para tabelas."""

from pathlib import Path

from analise.sessao import carregar_arquivos, carregar_sessao
from analise.tabelas import (
    linhas_cenario_a,
    linhas_cenario_b,
    linhas_cenario_c,
    linhas_controle_weaviate,
    linhas_ponte,
    linhas_recursos,
    linhas_reprodutibilidade,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "analise"


def test_linhas_recursos():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    linhas = linhas_recursos(sessao, escalas=[5000])

    # Deve conter multirow da escala
    assert r"\multirow{3}{*}{5k}" in linhas
    # pgvector com dados reais da fixture (total_bytes = 18604032 => 17.7 MiB; 18604032/5000 = 3721 B/vetor)
    assert "pgvector" in linhas
    assert "17,7" in linhas
    assert "3.721" in linhas
    assert "10,0" in linhas  # 10485760 B = 10.0 MiB RSS delta
    assert "12,5" in linhas  # tempo indice
    # Outros sistemas sem fixture nessa escala devem aparecer com traço
    assert "Qdrant" in linhas
    assert "Weaviate" in linhas
    assert r"\hline" in linhas


def test_linhas_cenario_a():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    linhas = linhas_cenario_a(sessao, n=5000)

    # pgvector tem 2 pontos (ef 16 e 64)
    assert r"\multirow{2}{*}{pgvector}" in linhas
    assert "16" in linhas
    assert "0,9500" in linhas
    assert "0,50" in linhas  # p50
    assert "1.200,0" in linhas  # qps
    # Amplitude: (0.52 - 0.48) / 0.50 * 100 = 8%
    assert "8" in linhas
    assert r"\hline" in linhas


def test_linhas_cenario_b():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    linhas = linhas_cenario_b(sessao, n=5000, ef=64)

    assert r"\multirow{4}{*}{pgvector}" in linhas
    assert r"1\%" in linhas
    assert "0,0600" in linhas  # padrao
    assert "0,0595" in linhas  # equalizado
    assert "1,24" in linhas  # p50 eq
    assert "810,0" in linhas  # qps eq


def test_linhas_cenario_c():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    linhas = linhas_cenario_c(sessao, n=5000)

    assert r"\multirow{2}{*}{pgvector}" in linhas
    # Janela 1: taxa 0, recall 0,9925, sem escrita (---)
    assert "0,9925" in linhas
    # Janela 2: taxa 10, recall novos com denominador (1,6k), visibilidade 100
    assert "0,9492 (1,6k)" in linhas
    assert "100" in linhas


def test_linhas_ponte():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    linhas = linhas_ponte(sessao, ef=64)

    # Qdrant possui registro na ponte de 100k
    assert "Qdrant" in linhas
    assert "0,9980" in linhas
    assert "2,29" in linhas
    assert "432,8" in linhas


def test_linhas_reprodutibilidade():
    sessao_nova = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    sessao_ant = carregar_arquivos([FIXTURES_DIR / "anterior_A_100k.json"])

    linhas = linhas_reprodutibilidade(sessao_nova, sessao_ant, ef=64)

    assert r"\multirow{3}{*}{100k}" in linhas
    assert "pgvector" in linhas
    assert "0,9872" in linhas  # anterior recall
    assert "822,0" in linhas  # anterior qps


def test_linhas_controle_weaviate():
    # Cria uma fixture sintética de sessao com Weaviate B padrão e equalizado
    dados_padrao = {
        "cenario": "B",
        "sistema": "weaviate",
        "n": 500000,
        "pontos": [
            {
                "parametros": {"ef_search": 16, "seletividade": 0.10},
                "metricas": {"recall_at_k": 0.9076},
                "ambiente": {"equalizado": False},
            },
            {
                "parametros": {"ef_search": 32, "seletividade": 0.10},
                "metricas": {"recall_at_k": 0.9189},
                "ambiente": {"equalizado": False},
            },
        ],
    }
    dados_eq = {
        "cenario": "B",
        "sistema": "weaviate",
        "n": 500000,
        "pontos": [
            {
                "parametros": {"ef_search": 16, "seletividade": 0.10},
                "metricas": {"recall_at_k": 0.9067},
                "ambiente": {"equalizado": True},
            },
            {
                "parametros": {"ef_search": 32, "seletividade": 0.10},
                "metricas": {"recall_at_k": 0.9100},
                "ambiente": {"equalizado": True},
            },
        ],
    }
    from analise.sessao import ArquivoSessao, Sessao

    sessao = Sessao(
        arquivos={
            ("B_padrao", "weaviate", 500000): ArquivoSessao(
                caminho=Path("dummy_b.json"),
                cenario="B",
                sistema="weaviate",
                n=500000,
                condicao="B_padrao",
                timestamp_utc="2026-11-15T15-00-00Z",
                dados=dados_padrao,
            ),
            ("B_eq", "weaviate", 500000): ArquivoSessao(
                caminho=Path("dummy_beq.json"),
                cenario="B",
                sistema="weaviate",
                n=500000,
                condicao="B_eq",
                timestamp_utc="2026-11-15T15-00-00Z",
                dados=dados_eq,
            ),
        }
    )

    linhas = linhas_controle_weaviate(sessao, n=500000)
    # ef 16: padrao 0,9076, eq 0,9067, delta 0,0009 -> Sim
    assert "16 & 0,9076 & 0,9067 & 0,0009 & Sim" in linhas
    # ef 32: padrao 0,9189, eq 0,9100, delta 0,0089 (> 0,005) -> Não
    assert "32 & 0,9189 & 0,9100 & 0,0089 & Não" in linhas
