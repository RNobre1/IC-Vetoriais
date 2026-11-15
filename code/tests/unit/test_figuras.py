"""Testes de fumaça e validação visual de figuras vetoriais em PDF."""

from pathlib import Path

from analise.figuras import (
    fig_cenario_c,
    fig_memoria,
    fig_recall_qps,
    formato_escala_extenso,
)
from analise.sessao import carregar_sessao

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "analise"


def test_formato_escala_extenso():
    assert formato_escala_extenso(100_000) == "100 mil vetores"
    assert formato_escala_extenso(500_000) == "500 mil vetores"
    assert formato_escala_extenso(1_000_000) == "1 milhão de vetores"
    assert formato_escala_extenso(5_000) == "5 mil vetores"


def test_fig_recall_qps_smoke(tmp_path):
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    saida = tmp_path / "recall_qps.pdf"

    fig = fig_recall_qps(sessao, escalas=[5000], caminho_saida=saida)
    assert fig is not None
    assert saida.exists()
    assert saida.stat().st_size > 0

    # Verifica propriedades dos eixos
    ax = fig.axes[0]
    assert ax.get_title() == "5 mil vetores"
    assert ax.get_ylabel() == "QPS (escala log)"
    assert ax.get_xlabel() == "Recall@10"

    # Verifica legenda única ao nível da figura
    assert len(fig.legends) == 1
    leg = fig.legends[0]
    textos_legenda = [t.get_text() for t in leg.get_texts()]
    assert any("pgvector" in t for t in textos_legenda)


def test_fig_cenario_c_smoke(tmp_path):
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    saida = tmp_path / "cenario_c.pdf"

    fig = fig_cenario_c(sessao, n=5000, caminho_saida=saida)
    assert fig is not None
    assert saida.exists()
    assert saida.stat().st_size > 0

    ax1, ax2 = fig.axes[:2]
    assert ax1.get_xlabel() == "Janela (taxa alvo, ins/s)"
    assert ax2.get_xlabel() == "Janela (taxa alvo, ins/s)"
    assert ax1.get_ylabel() == "Latência p99 (ms)"
    assert ax2.get_ylabel() == "Recall@10 (limite inferior)"

    # Linha divisória vertical entre janela 4 e 5 (x=3.5)
    vlines1 = [line for line in ax1.lines if line.get_xdata()[0] == 3.5]
    vlines2 = [line for line in ax2.lines if line.get_xdata()[0] == 3.5]
    assert len(vlines1) >= 1
    assert len(vlines2) >= 1

    # Legenda única da figura
    assert len(fig.legends) == 1


def test_fig_memoria_smoke(tmp_path):
    csv_path = FIXTURES_DIR / "monitor_synthetic.csv"
    marcos_path = FIXTURES_DIR / "marcos.jsonl"
    saida = tmp_path / "memoria.pdf"

    fig = fig_memoria(csv_path, marcos_path, n=5000, caminho_saida=saida)
    assert fig is not None
    assert saida.exists()
    assert saida.stat().st_size > 0

    # Título do painel deve ser o nome do sistema
    titulos = [ax.get_title() for ax in fig.axes]
    assert any(t in ("pgvector", "Qdrant", "Weaviate") for t in titulos)

    # Eixo x com texto completo
    for ax in fig.axes:
        assert ax.get_xlabel() == "Tempo desde o início do bloco (min)"

    # Legenda única abaixo com Total e Anônima em cinza escuro
    assert len(fig.legends) == 1
    leg = fig.legends[0]
    textos = [t.get_text() for t in leg.get_texts()]
    assert "Total (memory.current)" in textos
    assert "Anônima (anon)" in textos
