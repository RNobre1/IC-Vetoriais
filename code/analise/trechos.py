"""Trechos de código citados no relatório, extraídos do próprio código-fonte.

O relatório mostra pedaços do código em listagens. Para que a listagem não
envelheça separada do código, o trecho é delimitado no fonte por duas linhas
de comentário, `# relatorio: inicio <nome>` e `# relatorio: fim <nome>`, e
copiado daqui para `docx/relatorio_parcial/gerado/` por `make tabelas`; o
teste de frescor compara o arquivo gerado com o código atual.

`TRECHOS` é o manifesto: cada listagem do relatório, declarada uma vez, com as
partes que a compõem (sistema, arquivo relativo a `code/`, nome da marca).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

RAIZ_CODIGO = Path(__file__).resolve().parents[1]

MARCA_INICIO = "# relatorio: inicio "
MARCA_FIM = "# relatorio: fim "

# Listagem -> partes (sistema, arquivo relativo a code/, nome da marca).
TRECHOS: dict[str, list[tuple[str, str, str]]] = {
    # Seção 5.1: os três sistemas recebem os mesmos parâmetros de HNSW.
    "codigo_indice": [
        ("pgvector", "seeders/pgvector_seeder.py", "indice-hnsw"),
        ("Qdrant", "seeders/qdrant_seeder.py", "indice-hnsw"),
        ("Weaviate", "seeders/weaviate_seeder.py", "indice-hnsw"),
    ],
    # Seção 5.4: o mesmo predicado de filtro escrito na API de cada sistema.
    "codigo_filtro": [
        ("pgvector", "benchmarks/buscadores.py", "busca-filtrada-pgvector"),
        ("Qdrant", "benchmarks/buscadores.py", "busca-filtrada-qdrant"),
        ("Weaviate", "benchmarks/buscadores.py", "busca-filtrada-weaviate"),
    ],
}


def extrair_trecho(fonte: str, nome: str) -> str:
    """Linhas entre as marcas `nome`, sem as marcas e sem a indentação comum."""
    linhas = fonte.splitlines(keepends=True)
    inicios = [i for i, linha in enumerate(linhas) if linha.strip() == MARCA_INICIO + nome]
    fins = [i for i, linha in enumerate(linhas) if linha.strip() == MARCA_FIM + nome]
    if not inicios:
        raise ValueError(f"marca de inicio de {nome!r} não encontrada")
    if not fins:
        raise ValueError(f"marca de fim de {nome!r} não encontrada")
    if len(inicios) > 1 or len(fins) > 1:
        raise ValueError(f"mais de uma marca para {nome!r}")
    inicio, fim = inicios[0], fins[0]
    if fim < inicio:
        raise ValueError(f"marca de fim de {nome!r} aparece antes da de inicio")
    corpo = linhas[inicio + 1 : fim]
    if not "".join(corpo).strip():
        raise ValueError(f"trecho {nome!r} vazio")
    return textwrap.dedent("".join(corpo))


def compor_listagem(partes: list[tuple[str, str, str]]) -> str:
    """Junta as partes de uma listagem, cada uma rotulada com sistema e arquivo."""
    blocos = [f"# {sistema} (code/{arquivo})\n{trecho}" for sistema, arquivo, trecho in partes]
    return "\n".join(blocos)


def gerar_trechos(saida: str | Path, raiz: Path = RAIZ_CODIGO) -> list[Path]:
    """Escreve `<listagem>.txt` em `saida` para cada entrada de `TRECHOS`."""
    p_saida = Path(saida)
    p_saida.mkdir(parents=True, exist_ok=True)
    escritos = []
    for nome, partes in TRECHOS.items():
        conteudo = compor_listagem(
            [
                (sistema, arquivo, extrair_trecho((raiz / arquivo).read_text("utf-8"), marca))
                for sistema, arquivo, marca in partes
            ]
        )
        destino = p_saida / f"{nome}.txt"
        destino.write_text(conteudo, encoding="utf-8")
        escritos.append(destino)
    return escritos
