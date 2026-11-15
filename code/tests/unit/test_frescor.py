"""Teste de frescor das tabelas geradas para o relatório."""

from pathlib import Path

import pytest

from analise.gerar import gerar_artefatos


def test_frescor_tabelas_geradas(tmp_path):
    # O diretório do relatório parcial
    repo_root = Path(__file__).resolve().parents[3]
    gerado_dir = repo_root / "docx" / "relatorio_parcial" / "gerado"

    if not gerado_dir.exists() or not list(gerado_dir.glob("*.tex")):
        pytest.skip(
            f"Diretório {gerado_dir} ainda não existe ou não contém tabelas — pulando teste de frescor."
        )

    # Quando existir, regera em tmp_path e compara byte a byte
    tmp_tabelas = tmp_path / "tabelas"
    tmp_figuras = tmp_path / "figuras"

    results_dir = repo_root / "code" / "results"
    sessoes_dir = results_dir / "sessoes"
    sessoes = sorted(sessoes_dir.glob("*")) if sessoes_dir.exists() else []
    if not sessoes:
        pytest.skip("Nenhuma sessão encontrada para executar teste de frescor.")

    sessao_ativa = sessoes[-1]
    gerar_artefatos(
        results_dir=results_dir,
        sessao_dir=sessao_ativa,
        saida_tabelas=tmp_tabelas,
        saida_figuras=tmp_figuras,
    )

    for arquivo_tex in gerado_dir.glob("*.tex"):
        arquivo_regerado = tmp_tabelas / arquivo_tex.name
        assert (
            arquivo_regerado.exists()
        ), f"Tabela {arquivo_tex.name} não foi regerada no teste de frescor."
        assert (
            arquivo_regerado.read_bytes() == arquivo_tex.read_bytes()
        ), f"Tabela {arquivo_tex.name} difere da versão em disco (falha de frescor)."
