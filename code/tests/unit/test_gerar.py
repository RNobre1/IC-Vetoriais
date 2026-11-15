"""Testes unitários do CLI gerador de artefatos da análise."""

from pathlib import Path

from analise.gerar import gerar_artefatos

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "analise"


def test_gerar_artefatos_completo(tmp_path):
    saida_tabelas = tmp_path / "tabelas"
    saida_figuras = tmp_path / "figuras"

    avisos = gerar_artefatos(
        results_dir=FIXTURES_DIR / "jsons",
        sessao_dir=FIXTURES_DIR,
        marcos_path=FIXTURES_DIR / "marcos.jsonl",
        monitor_csv=FIXTURES_DIR / "monitor_synthetic.csv",
        anterior_paths=[FIXTURES_DIR / "anterior_A_100k.json"],
        saida_tabelas=saida_tabelas,
        saida_figuras=saida_figuras,
    )

    # Verifica se as tabelas foram geradas
    assert (saida_tabelas / "tab_recursos.tex").exists()
    assert (saida_tabelas / "tab_a_5000.tex").exists()
    assert (saida_tabelas / "tab_b_5000.tex").exists()
    assert (saida_tabelas / "tab_c_5000.tex").exists()
    assert (saida_tabelas / "tab_ponte.tex").exists()
    assert (saida_tabelas / "tab_reprod.tex").exists()
    assert (saida_tabelas / "tab_custo.tex").exists()

    # Conteúdo não vazio
    assert (saida_tabelas / "tab_recursos.tex").stat().st_size > 0
    assert (saida_tabelas / "tab_c_5000.tex").stat().st_size > 0

    # Figuras geradas
    assert (saida_figuras / "fig_recall_qps.pdf").exists()
    assert (saida_figuras / "fig_cenario_c_5000.pdf").exists()
    assert (saida_figuras / "fig_memoria_5000.pdf").exists()

    # Avisos capturados
    assert isinstance(avisos, list)
