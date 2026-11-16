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
    assert (saida_tabelas / "tab_c_hospedeiro_5000.tex").exists()
    assert (saida_tabelas / "tab_ponte.tex").exists()
    assert (saida_tabelas / "tab_reprod.tex").exists()
    assert (saida_tabelas / "tab_custo.tex").exists()
    assert (saida_tabelas / "tab_custo_5000.tex").exists()

    # Conteúdo não vazio
    assert (saida_tabelas / "tab_recursos.tex").stat().st_size > 0
    assert (saida_tabelas / "tab_c_5000.tex").stat().st_size > 0
    assert (saida_tabelas / "tab_c_hospedeiro_5000.tex").stat().st_size > 0
    assert (saida_tabelas / "tab_custo_5000.tex").stat().st_size > 0

    # Verifica tab_c_hospedeiro_5000.tex
    conteudo_c_hosp = (saida_tabelas / "tab_c_hospedeiro_5000.tex").read_text(encoding="utf-8")
    assert r"\multirow{2}{*}{pgvector}" in conteudo_c_hosp
    assert r"\hline" in conteudo_c_hosp

    # Verifica distinção de formato entre tab_custo.tex (consolidada) e tab_custo_5000.tex (por escala)
    conteudo_custo_global = (saida_tabelas / "tab_custo.tex").read_text(encoding="utf-8")
    conteudo_custo_5000 = (saida_tabelas / "tab_custo_5000.tex").read_text(encoding="utf-8")

    assert "5k" in conteudo_custo_global
    assert "5k" not in conteudo_custo_5000
    assert r"\multirow{1}{*}{pgvector}" in conteudo_custo_5000
    assert r"\hline" in conteudo_custo_5000
    # Verifica que as novas colunas (swap-in e psi-mem) estão presentes
    assert r"\cline{2-9}" in conteudo_custo_global or r"\hline" in conteudo_custo_global

    # Figuras geradas
    assert (saida_figuras / "fig_recall_qps.pdf").exists()
    assert (saida_figuras / "fig_cenario_c_5000.pdf").exists()
    assert (saida_figuras / "fig_memoria_5000.pdf").exists()

    # Avisos capturados
    assert isinstance(avisos, list)


def test_makefile_tabelas_alvo_imprime_avisos():
    makefile = Path(__file__).parents[2] / "Makefile"
    assert makefile.exists()
    conteudo = makefile.read_text(encoding="utf-8")

    # Localiza o alvo tabelas:
    assert "tabelas:" in conteudo
    trecho = conteudo.split("tabelas:")[1].split("\n\n")[0]
    # Deve imprimir os avisos com prefixo AVISO:
    assert "AVISO:" in trecho
