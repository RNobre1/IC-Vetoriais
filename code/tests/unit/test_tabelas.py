"""Testes unitários dos geradores de linhas LaTeX para tabelas."""

from pathlib import Path

from analise.sessao import ArquivoSessao, Sessao, carregar_arquivos, carregar_sessao
from analise.tabelas import (
    linhas_cenario_a,
    linhas_cenario_b,
    linhas_cenario_c,
    linhas_cenario_c_hospedeiro,
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
    # A primeira coluna é a escala, em multirow, para empilhar 500k e 1M numa
    # tabela só sem que o ef caia sob a coluna da escala.
    assert linhas.splitlines()[0] == "\\multirow{2}{*}{500k}"
    assert " & 16 & 0,9076 & 0,9067 & 0,0009 & Sim \\\\" in linhas
    assert " & 32 & 0,9189 & 0,9100 & 0,0089 & Não \\\\" in linhas


def test_linhas_cenario_c_hospedeiro():
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")

    # 1. Sem amostras de monitor: deve preencher com ---
    linhas_vazio = linhas_cenario_c_hospedeiro(sessao, n=5000, amostras_monitor=[])
    assert r"\multirow{2}{*}{pgvector}" in linhas_vazio
    assert " & 1 & 0 & --- & --- & --- \\\\" in linhas_vazio
    assert " & 2 & 10 & --- & --- & --- \\\\" in linhas_vazio
    assert r"\hline" in linhas_vazio

    # 2. Com amostras sintéticas na janela
    amostras = [
        {
            "ts_utc": "2026-11-15T14:51:46.000Z",
            "cpu_mhz_medio": "2500.0",
            "cpu_host_ocupado": "100",
            "cpu_host_total": "1000",
            "psi_cpu_some_avg10": "0.10",
        },
        {
            "ts_utc": "2026-11-15T14:51:50.000Z",
            "cpu_mhz_medio": "2700.0",
            "cpu_host_ocupado": "250",
            "cpu_host_total": "1600",
            "psi_cpu_some_avg10": "0.35",
        },
    ]
    linhas_com_dados = linhas_cenario_c_hospedeiro(sessao, n=5000, amostras_monitor=amostras)
    # Janela 1: MHz médio = (2500+2700)/2 = 2600; CPU ocup = (250-100)/(1600-1000)*100 = 25%; PSI pico = 0.35
    assert " & 1 & 0 & 2.600 & 25 & 0,35 \\\\" in linhas_com_dados
    # Janela 2 (sem amostras): ---
    assert " & 2 & 10 & --- & --- & --- \\\\" in linhas_com_dados


def test_linhas_cenario_c_hospedeiro_assentamento():
    dados_c = {
        "cenario": "C",
        "sistema": "weaviate",
        "n": 5000,
        "pontos": [
            {
                "parametros": {"ordem_janela": 5, "taxa_alvo": 0},
                "ambiente": {
                    "assentar_s": 5.0,
                    "inicio_utc": "2026-11-15T15:00:00Z",
                    "fim_utc": "2026-11-15T15:01:00Z",
                },
            }
        ],
    }
    sessao = Sessao(
        arquivos={
            ("C", "weaviate", 5000): ArquivoSessao(
                caminho=Path("dummy_c.json"),
                cenario="C",
                sistema="weaviate",
                n=5000,
                condicao="C",
                timestamp_utc="2026-11-15T15-00-00Z",
                dados=dados_c,
            )
        }
    )
    linhas = linhas_cenario_c_hospedeiro(sessao, n=5000, amostras_monitor=[])
    assert " & 6* & 0 & --- & --- & --- \\\\" in linhas


def test_referencia_preliminar_hospedeiro_1m():
    """Valida valores de referência de frequência da CPU no Cenário C da sessão preliminar."""
    p_results = Path(
        "/Users/rnobre/.traycer/epics/04d7ef96-f88f-4c9b-9007-745670c439de/scratch/preliminar/results"
    )
    sessao_dir = p_results / "sessoes" / "2026-11-16-final"
    csv_path = sessao_dir / "monitor_023936.csv"
    marcos_path = sessao_dir / "marcos.jsonl"

    if not csv_path.exists() or not marcos_path.exists():
        return

    sessao = carregar_sessao(p_results, marcos_path)
    linhas = linhas_cenario_c_hospedeiro(sessao, 1000000, amostras_monitor=csv_path)

    # pgvector janela 1 (alvo 0): ~1728 MHz
    assert r"\multirow{6}{*}{pgvector}" in linhas
    assert " & 1 & 0 & 1.728 & 8 & 0,00 \\\\" in linhas

    # Qdrant janela de 1000 (janela 4): ~2933 MHz
    assert r"\multirow{6}{*}{Qdrant}" in linhas
    assert " & 4 & 1.000 & 2.933 & 26 & 0,48 \\\\" in linhas

    # Weaviate janela de 1000 (janela 4): ~3540 MHz
    assert r"\multirow{6}{*}{Weaviate}" in linhas
    assert " & 4 & 1.000 & 3.540 & 23 & 1,34 \\\\" in linhas


def _sessao_b_sintetica(recalls_padrao_1pct: list[float]) -> Sessao:
    """Weaviate com B padrão em p=1% nos ef dados e B equalizado só em ef=64."""
    efs = [16, 32, 64, 128, 256][: len(recalls_padrao_1pct)]
    pontos_p = [
        {
            "parametros": {"seletividade": 0.01, "ef_search": ef},
            "metricas": {"recall_at_k": r, "p50": 1.0, "qps": 100.0},
        }
        for ef, r in zip(efs, recalls_padrao_1pct, strict=True)
    ]
    pontos_e = [
        {
            "parametros": {"seletividade": 0.01, "ef_search": 64},
            "metricas": {"recall_at_k": 0.5, "p50": 3.0, "qps": 300.0},
        }
    ]
    s = Sessao()
    for cond, pts in (("B_padrao", pontos_p), ("B_eq", pontos_e)):
        s.arquivos[(cond, "weaviate", 1000)] = ArquivoSessao(
            caminho=Path(f"{cond}.json"),
            cenario="B",
            sistema="weaviate",
            n=1000,
            condicao=cond,
            timestamp_utc="2026-11-16T00-00-00Z",
            dados={"pontos": pts},
        )
    return s


def test_cenario_b_negrito_quando_recall_padrao_nao_responde_a_ef():
    # Recall idêntico em todos os ef medidos não pode vir do percurso do grafo:
    # é o atalho de varredura exata. Vale também para 0,9999 constante.
    linhas = linhas_cenario_b(_sessao_b_sintetica([0.9999] * 5), n=1000, ef=64)
    assert " & 1\\% & \\textbf{0,9999} & 0,5000 & 3,00 & 300,0 \\\\" in linhas


def test_cenario_b_sem_negrito_quando_recall_varia_com_ef():
    linhas = linhas_cenario_b(_sessao_b_sintetica([0.9, 0.95, 0.97, 0.99, 1.0]), n=1000, ef=64)
    assert " & 1\\% & 0,9700 & 0,5000 & 3,00 & 300,0 \\\\" in linhas


def test_cenario_b_sem_negrito_com_um_unico_ef_medido():
    # Com um ponto só, não há como saber se o recall responde a ef.
    linhas = linhas_cenario_b(_sessao_b_sintetica([1.0, 1.0, 1.0][:1] * 1), n=1000, ef=64)
    assert "textbf" not in linhas
