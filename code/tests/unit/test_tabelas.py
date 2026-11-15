"""Testes unitários dos geradores de linhas LaTeX para tabelas."""

from pathlib import Path

from analise.sessao import ArquivoSessao, Sessao, carregar_arquivos, carregar_sessao
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

    assert r"\multirow{3}{*}{5k}" in linhas
    assert " & pgvector & 17,7 & 3.721 & 10,0 & 12,5 \\\\" in linhas
    assert " & Qdrant & --- & --- & --- & --- \\\\" in linhas
    assert " & Weaviate & --- & --- & --- & --- \\\\" in linhas
    assert r"\hline" in linhas


def test_linhas_cenario_a():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    linhas = linhas_cenario_a(sessao, n=5000)

    assert r"\multirow{2}{*}{pgvector}" in linhas
    assert " & 16 & 0,9500 & 0,50 & 1,20 & 2,10 & 1.200,0 & 8 \\\\" in linhas
    assert " & 64 & 0,9800 & 0,80 & 1,50 & 2,40 & 900,0 & 3 \\\\" in linhas
    assert r"\hline" in linhas


def test_linhas_cenario_b():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    linhas = linhas_cenario_b(sessao, n=5000, ef=64)

    assert r"\multirow{4}{*}{pgvector}" in linhas
    assert " & 1\\% & 0,0600 & 0,0595 & 1,24 & 810,0 \\\\" in linhas
    assert " & 10\\% & 0,6300 & 0,6310 & 1,18 & 840,0 \\\\" in linhas
    assert " & 50\\% & --- & --- & --- & --- \\\\" in linhas
    assert " & 100\\% & --- & --- & --- & --- \\\\" in linhas


def test_linhas_cenario_c():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    linhas = linhas_cenario_c(sessao, n=5000)

    assert r"\multirow{2}{*}{pgvector}" in linhas
    assert " & 1 & 0 & 0 & 0,85 & 2,45 & 880,0 & 0,9925 & --- & --- \\\\" in linhas
    assert " & 2 & 10 & 10 & 0,90 & 2,50 & 850,0 & 0,9915 & 0,9492 (1,6k) & 100 \\\\" in linhas


def test_linhas_cenario_c_rotulo_assentar_e_inf_sup_incompleto():
    dados_c = {
        "cenario": "C",
        "sistema": "qdrant",
        "n": 5000,
        "pontos": [
            {
                "parametros": {"ordem_janela": 5, "taxa_alvo": 0},
                "ambiente": {"assentar_s": 10.5},
                "metricas": {
                    "p50": 1.0,
                    "p99": 2.0,
                    "qps": 500.0,
                    "recall_inferior": 0.99,
                    "recall_superior": None,  # Um lado ausente -> deve virar '---'
                },
            }
        ],
    }
    sessao = Sessao(
        arquivos={
            ("C", "qdrant", 5000): ArquivoSessao(
                caminho=Path("dummy_c.json"),
                cenario="C",
                sistema="qdrant",
                n=5000,
                condicao="C",
                timestamp_utc="2026-11-15T15-00-00Z",
                dados=dados_c,
            )
        }
    )
    linhas = linhas_cenario_c(sessao, n=5000)
    # A janela com assentar_s vira 6* (ou ordem_janela + 1 com *)
    assert " & 6* & 0 & --- & 1,00 & 2,00 & 500,0 & --- & --- & --- \\\\" in linhas


def test_linhas_ponte():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    linhas = linhas_ponte(sessao, ef=64)

    assert "Qdrant & 0,9980 & 2,29 & 432,8 & --- & --- & --- \\\\" in linhas


def test_linhas_reprodutibilidade():
    sessao_nova = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    sessao_ant = carregar_arquivos([FIXTURES_DIR / "anterior_A_100k.json"])

    linhas = linhas_reprodutibilidade(sessao_nova, sessao_ant, ef=64)

    assert r"\multirow{3}{*}{100k}" in linhas
    assert " & pgvector & 0,9872 & 822,0 & --- & --- & --- \\\\" in linhas


def test_linhas_controle_weaviate():
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
    assert "16 & 0,9076 & 0,9067 & 0,0009 & Sim \\\\" in linhas
    assert "32 & 0,9189 & 0,9100 & 0,0089 & Não \\\\" in linhas
