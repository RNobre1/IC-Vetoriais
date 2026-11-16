"""Teste de frescor das tabelas geradas para o relatório."""

from pathlib import Path

import pytest

from analise.config_oficial import (
    ANTERIOR_PATHS,
    RESULTS_DIR,
    SAIDA_TABELAS,
    SESSAO_DIR,
)
from analise.gerar import gerar_artefatos

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "analise"


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

    for arquivo_regerado in tmp_tabelas.glob("*.tex"):
        arquivo_tex = SAIDA_TABELAS / arquivo_regerado.name
        assert arquivo_tex.exists(), f"Tabela {arquivo_regerado.name} foi gerada mas não existe na pasta oficial {SAIDA_TABELAS}."


def test_frescor_sintetico_com_fixtures(tmp_path):
    """Valida a mecânica do teste de frescor (regeração idêntica e detecção de tabela faltante)."""
    pasta_oficial = tmp_path / "gerado_oficial"
    pasta_regerada = tmp_path / "regerada"

    gerar_artefatos(
        results_dir=FIXTURES_DIR / "jsons",
        sessao_dir=FIXTURES_DIR,
        marcos_path=FIXTURES_DIR / "marcos.jsonl",
        monitor_csv=FIXTURES_DIR / "monitor_synthetic.csv",
        anterior_paths=[FIXTURES_DIR / "anterior_A_100k.json"],
        saida_tabelas=pasta_oficial,
        saida_figuras=tmp_path / "figuras",
    )

    assert (pasta_oficial / "tab_c_hospedeiro_5000.tex").exists()
    assert (pasta_oficial / "tab_custo.tex").exists()
    assert (pasta_oficial / "tab_custo_5000.tex").exists()

    gerar_artefatos(
        results_dir=FIXTURES_DIR / "jsons",
        sessao_dir=FIXTURES_DIR,
        marcos_path=FIXTURES_DIR / "marcos.jsonl",
        monitor_csv=FIXTURES_DIR / "monitor_synthetic.csv",
        anterior_paths=[FIXTURES_DIR / "anterior_A_100k.json"],
        saida_tabelas=pasta_regerada,
        saida_figuras=tmp_path / "figuras",
    )

    for arq in pasta_oficial.glob("*.tex"):
        regerado = pasta_regerada / arq.name
        assert regerado.exists()
        assert regerado.read_bytes() == arq.read_bytes()
