"""Teste de frescor das tabelas geradas para o relatório."""

import pytest

from analise.config_oficial import (
    ANTERIOR_PATHS,
    RESULTS_DIR,
    SAIDA_TABELAS,
    SESSAO_DIR,
)
from analise.gerar import gerar_artefatos


def test_frescor_tabelas_geradas(tmp_path):
    if not SAIDA_TABELAS.exists() or not list(SAIDA_TABELAS.glob("*.tex")):
        pytest.skip(
            f"Diretório {SAIDA_TABELAS} ainda não existe ou não contém tabelas — pulando teste de frescor."
        )

    # Se gerado/ existe mas a sessão oficial apontada não existe, deve FALHAR (não pular)
    if not SESSAO_DIR.exists():
        pytest.fail(
            f"Diretório de tabelas oficiais {SAIDA_TABELAS} existe, mas a sessão oficial "
            f"referida em config_oficial.py ({SESSAO_DIR}) não foi encontrada."
        )

    tmp_tabelas = tmp_path / "tabelas"
    tmp_figuras = tmp_path / "figuras"

    gerar_artefatos(
        results_dir=RESULTS_DIR,
        sessao_dir=SESSAO_DIR,
        anterior_paths=ANTERIOR_PATHS,
        saida_tabelas=tmp_tabelas,
        saida_figuras=tmp_figuras,
    )

    for arquivo_tex in SAIDA_TABELAS.glob("*.tex"):
        arquivo_regerado = tmp_tabelas / arquivo_tex.name
        assert (
            arquivo_regerado.exists()
        ), f"Tabela {arquivo_tex.name} não foi regerada no teste de frescor."
        assert (
            arquivo_regerado.read_bytes() == arquivo_tex.read_bytes()
        ), f"Tabela {arquivo_tex.name} difere da versão em disco (falha de frescor)."
