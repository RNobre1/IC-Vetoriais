"""Testes de fumaça da geração de figuras vetoriais em PDF."""

from pathlib import Path

from analise.figuras import fig_cenario_c, fig_memoria, fig_recall_qps
from analise.sessao import carregar_sessao

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "analise"


def test_fig_recall_qps_smoke(tmp_path):
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    saida = tmp_path / "recall_qps.pdf"

    fig = fig_recall_qps(sessao, escalas=[5000], caminho_saida=saida)
    assert fig is not None
    assert saida.exists()
    assert saida.stat().st_size > 0


def test_fig_cenario_c_smoke(tmp_path):
    sessao = carregar_sessao(FIXTURES_DIR / "jsons", FIXTURES_DIR / "marcos.jsonl")
    saida = tmp_path / "cenario_c.pdf"

    fig = fig_cenario_c(sessao, n=5000, caminho_saida=saida)
    assert fig is not None
    assert saida.exists()
    assert saida.stat().st_size > 0


def test_fig_memoria_smoke(tmp_path):
    csv_path = FIXTURES_DIR / "monitor_synthetic.csv"
    marcos_path = FIXTURES_DIR / "marcos.jsonl"
    saida = tmp_path / "memoria.pdf"

    fig = fig_memoria(csv_path, marcos_path, n=5000, caminho_saida=saida)
    assert fig is not None
    assert saida.exists()
    assert saida.stat().st_size > 0
