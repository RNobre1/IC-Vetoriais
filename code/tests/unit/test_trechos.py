"""Trechos de código citados no relatório: extração por marcas e guardas de frescor."""

import re
from pathlib import Path

import pytest

from analise.config_oficial import REPO_ROOT, SAIDA_TABELAS
from analise.trechos import (
    MARCA_FIM,
    MARCA_INICIO,
    RAIZ_CODIGO,
    TRECHOS,
    compor_listagem,
    extrair_trecho,
    gerar_trechos,
)

SECOES_RELATORIO = REPO_ROOT / "docx" / "relatorio_parcial" / "secoes"

FONTE = """\
def f(conn):
    with conn.cursor() as cur:
        # relatorio: inicio consulta
        cur.execute(
            "SELECT 1"
        )
        # relatorio: fim consulta
        return cur.fetchone()
"""


def test_extrai_linhas_entre_as_marcas_sem_indentacao_comum():
    assert extrair_trecho(FONTE, "consulta") == 'cur.execute(\n    "SELECT 1"\n)\n'


def test_marcas_nao_aparecem_no_trecho():
    trecho = extrair_trecho(FONTE, "consulta")
    assert "relatorio:" not in trecho


@pytest.mark.parametrize(
    ("fonte", "mensagem"),
    [
        ("x = 1\n", "inicio"),
        ("# relatorio: inicio consulta\nx = 1\n", "fim"),
        ("# relatorio: fim consulta\nx = 1\n# relatorio: inicio consulta\n", "antes"),
        ("# relatorio: inicio consulta\n# relatorio: fim consulta\n", "vazio"),
        (
            "# relatorio: inicio consulta\nx = 1\n# relatorio: fim consulta\n"
            "# relatorio: inicio consulta\ny = 2\n# relatorio: fim consulta\n",
            "mais de uma",
        ),
    ],
)
def test_marcas_invalidas_levantam_erro(fonte, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        extrair_trecho(fonte, "consulta")


def test_nome_parecido_nao_casa_com_outra_marca():
    fonte = "# relatorio: inicio consulta-b\nx = 1\n# relatorio: fim consulta-b\n"
    with pytest.raises(ValueError, match="inicio"):
        extrair_trecho(fonte, "consulta")


def test_compor_listagem_rotula_cada_parte_com_sistema_e_arquivo():
    listagem = compor_listagem(
        [
            ("pgvector", "benchmarks/a.py", "cur.execute(q)\n"),
            ("Qdrant", "benchmarks/b.py", "client.query(q)\n"),
        ]
    )
    assert listagem == (
        "# pgvector (code/benchmarks/a.py)\n"
        "cur.execute(q)\n"
        "\n"
        "# Qdrant (code/benchmarks/b.py)\n"
        "client.query(q)\n"
    )


def test_gerar_trechos_escreve_um_arquivo_por_listagem(tmp_path):
    escritos = gerar_trechos(tmp_path)
    assert sorted(p.name for p in escritos) == sorted(f"{nome}.txt" for nome in TRECHOS)
    for p in escritos:
        assert p.read_text(encoding="utf-8").strip()


def test_frescor_trechos_gerados(tmp_path):
    """O que está em gerado/ é idêntico ao que o código atual produz."""
    gerar_trechos(tmp_path)
    for nome in TRECHOS:
        oficial = SAIDA_TABELAS / f"{nome}.txt"
        assert oficial.exists(), f"{oficial.name} não existe; rode `make tabelas`."
        assert (
            oficial.read_bytes() == (tmp_path / f"{nome}.txt").read_bytes()
        ), f"{oficial.name} difere do código atual (falha de frescor); rode `make tabelas`."


def _marcas_no_codigo() -> set[tuple[str, str]]:
    """(arquivo relativo a code/, nome) de toda marca de início fora dos testes."""
    achadas = set()
    padrao = re.compile(rf"^\s*{re.escape(MARCA_INICIO)}(\S+)\s*$")
    for arquivo in RAIZ_CODIGO.rglob("*.py"):
        relativo = arquivo.relative_to(RAIZ_CODIGO)
        if relativo.parts[0] in {"tests", ".venv"}:
            continue
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            m = padrao.match(linha)
            if m:
                achadas.add((relativo.as_posix(), m.group(1)))
    return achadas


def test_toda_marca_no_codigo_esta_no_manifesto():
    declaradas = {(arq, nome) for partes in TRECHOS.values() for _, arq, nome in partes}
    orfas = _marcas_no_codigo() - declaradas
    assert not orfas, f"Marcas sem entrada em TRECHOS: {sorted(orfas)}"


def test_marcas_de_fim_sao_simetricas_ao_inicio():
    assert MARCA_INICIO.replace("inicio", "fim") == MARCA_FIM


def test_toda_listagem_do_relatorio_vem_do_manifesto_e_vice_versa():
    usadas = set()
    for tex in SECOES_RELATORIO.glob("*.tex"):
        usadas |= set(
            re.findall(r"\\lstinputlisting(?:\[[^\]]*\])?\{gerado/([^}]+)\.txt\}", tex.read_text())
        )
    assert usadas == set(TRECHOS), (
        f"Só no relatório: {sorted(usadas - set(TRECHOS))}; "
        f"só no manifesto: {sorted(set(TRECHOS) - usadas)}"
    )


def test_caminhos_do_manifesto_existem():
    for partes in TRECHOS.values():
        for _, arquivo, _ in partes:
            assert (RAIZ_CODIGO / arquivo).is_file(), arquivo


def test_raiz_do_codigo_e_a_pasta_code_do_repositorio():
    """O cabeçalho de cada parte usa `code/<arquivo>`, o caminho visto no repositório."""
    assert RAIZ_CODIGO == REPO_ROOT / "code"


def test_make_tabelas_tambem_gera_os_trechos(tmp_path):
    """`gerar_artefatos` é a entrada única de `make tabelas`; os trechos saem junto."""
    from analise.gerar import gerar_artefatos

    fixtures = Path(__file__).parent / "fixtures" / "analise"
    gerar_artefatos(
        results_dir=fixtures / "jsons",
        sessao_dir=fixtures,
        marcos_path=fixtures / "marcos.jsonl",
        monitor_csv=fixtures / "monitor_synthetic.csv",
        anterior_paths=[fixtures / "anterior_A_100k.json"],
        saida_tabelas=tmp_path,
        saida_figuras=None,
    )
    for nome in TRECHOS:
        assert (tmp_path / f"{nome}.txt").exists()
