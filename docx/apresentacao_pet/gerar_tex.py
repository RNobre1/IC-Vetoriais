#!/usr/bin/env python3
"""Escreve `corpo-gerado.tex` a partir de `conteudo.py`.

O `slides.tex` guarda só o preâmbulo e as macros de diagramação, e dá `\\input`
neste corpo. Assim o texto existe em um lugar só, e o `.pptx`, o roteiro e o
PDF não podem divergir por edição esquecida.
"""

from __future__ import annotations

import re
from pathlib import Path

import conteudo

AQUI = Path(__file__).parent
SAIDA = AQUI / "corpo-gerado.tex"

ESCAPES = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_"}


def tex(s: str) -> str:
    """Escapa o texto e converte a marcação inline em comandos LaTeX."""
    for a, b in ESCAPES.items():
        s = s.replace(a, b)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"\*([^*]+)\*", r"\\dest{\1}", s)
    s = re.sub(r"_([^_]+)_", r"\\emph{\1}", s)
    return s


def bloco(tipo, valor) -> str:
    if tipo == "texto":
        return tex(valor) + "\\\\[24pt]\n\n"
    if tipo == "nota":
        return ("{\\color{cinza}\\fontsize{23}{32}\\selectfont\n"
                + tex(valor) + "}\\\\[20pt]\n\n")
    if tipo == "nota_centro":
        return ("\\begin{center}{\\color{cinza}\\fontsize{23}{30}\\selectfont "
                + tex(valor) + "}\\end{center}\n\n")
    if tipo == "frase":
        linhas = "\\\\[10pt]\n".join(tex(l) for l in valor.split("\n"))
        return ("\\begin{center}{\\fontsize{34}{46}\\selectfont\\bfseries\\color{azul}\n"
                + linhas + "}\\end{center}\\vspace{26pt}\n\n")
    if tipo == "cartoes":
        larg = {2: 560, 3: 392}[len(valor)]
        vao = {2: 40, 3: 30}[len(valor)]
        partes = [f"\\cartao{{{larg}pt}}{{{tex(t)}}}{{{tex(x)}}}" for t, x in valor]
        return ("\\begin{center}\n"
                + f"\\hspace{{{vao}pt}}%\n".join(partes)
                + "\n\\end{center}\\vspace{22pt}\n\n")
    if tipo == "destaques":
        partes = [f"\\numerao{{azul}}{{{tex(p)}}}{{{tex(l)}}}" for p, l in valor]
        return "\\hspace{56pt}%\n".join(partes) + "\n\\\\[50pt]\n\n"
    if tipo == "colunas":
        cols = []
        for col in valor:
            cols.append("\\begin{minipage}[t]{620pt}\n"
                        + "\\\\[16pt]\n".join(tex(l) for l in col)
                        + "\n\\end{minipage}")
        return "%\n".join(cols) + "\\\\[26pt]\n\n"
    if tipo == "colunas_titulo":
        cols = []
        for titulo, itens in valor:
            cols.append("\\begin{minipage}[t]{640pt}\n"
                        f"{{\\fontsize{{29}}{{40}}\\selectfont\\bfseries {tex(titulo)}}}\\\\[14pt]\n"
                        "{\\fontsize{25}{36}\\selectfont\n"
                        + "\\\\\n".join(tex(l) for l in itens)
                        + "}\n\\end{minipage}")
        return "%\n".join(cols) + "\\\\[42pt]\n\n"
    if tipo == "barras":
        largura_max = 760
        linhas = [f"\\barra{{{tex(r)}}}{{{max(int(largura_max * p), 60)}}}{{azul}}{{{tex(t)}}}"
                  for r, p, t in valor]
        return "\n".join(linhas) + "\n\\vspace{16pt}\n\n"
    if tipo == "central":
        return ("\\vspace{150pt}\n\\begin{center}\n"
                "{\\fontsize{86}{100}\\selectfont\\bfseries " + tex(valor) + "}\n"
                "\\end{center}\n\n")
    if tipo == "diagrama":
        return diagrama(valor)
    if tipo == "tabela":
        return tabela(valor)
    if tipo == "caixa":
        return ("\\begin{center}\n\\colorbox{cinzaclaro}{\\begin{minipage}{1252pt}\n"
                "\\vspace{22pt}\n\\hspace{24pt}\\begin{minipage}{1204pt}\n\\raggedright\n"
                "{\\fontsize{29}{40}\\selectfont\n" + tex(valor) + "}\n"
                "\\end{minipage}\n\\vspace{24pt}\n\\end{minipage}}\n\\end{center}"
                "\\vspace{22pt}\n\n")
    if tipo == "caixa_navy":
        return ("\\vspace{16pt}\n\\begin{center}\n"
                "\\colorbox{navy}{\\begin{minipage}{1220pt}\n\\vspace{30pt}\n"
                "\\hspace{30pt}\\begin{minipage}{1160pt}\n\\raggedright\n"
                "{\\color{white}\\fontsize{40}{54}\\selectfont\n" + tex(valor[0]) + "\\\\[20pt]\n"
                "\\fontsize{32}{46}\\selectfont\n" + tex(valor[1]) + "}\n"
                "\\end{minipage}\n\\vspace{32pt}\n\\end{minipage}}\n\\end{center}"
                "\\vspace{40pt}\n\n")
    raise SystemExit(f"tipo de bloco sem emissor para LaTeX: {tipo}")


def diagrama(dados: dict) -> str:
    """Desenha pontos, ligações e rótulos com o ambiente `picture` do LaTeX.

    Coordenadas do conteúdo são normalizadas em 0..100 nos dois eixos, com y
    para cima. `picture` basta aqui: nem `tikz` nem `pgf` estão instalados, e
    `\\qbezier` traça segmento reto entre dois pontos arbitrários quando o
    ponto de controle é o ponto médio.
    """
    larg, alt = 1296, dados["altura"]
    px = lambda x: x * larg / 100
    py = lambda y: y * alt / 100
    # Sem `center`: centralizar desloca a caixa do `picture` e as coordenadas
    # deixam de bater com a margem do slide. Ancorando à esquerda, x=0 é a
    # margem e o mapeamento é exato — foi medido no PDF, não suposto.
    saida = ["\\noindent\\setlength{\\unitlength}{1pt}%\n"
             f"\\begin{{picture}}({larg},{alt})\n"]
    for x1, y1, x2, y2, cor, esp in dados["arestas"]:
        a, b, c, d = px(x1), py(y1), px(x2), py(y2)
        # O `\\qbezier` precisa ir dentro de um `\\put`: solto no `picture` ele
        # entra na lista horizontal e desloca o ponto de referência de tudo o
        # que vem depois. Medido no PDF: sem o `\\put`, os círculos saíam
        # 169 pt à direita das linhas que deveriam tocá-los.
        saida.append(f"  \\put(0,0){{{{\\color{{{cor}}}\\linethickness{{{esp}pt}}"
                     f"\\qbezier({a:.1f},{b:.1f})({(a + c) / 2:.1f},{(b + d) / 2:.1f})"
                     f"({c:.1f},{d:.1f})}}}}\n")
    for x, y, cor, tam in dados["pontos"]:
        saida.append(f"  \\put({px(x):.1f},{py(y):.1f}){{\\color{{{cor}}}\\circle*{{{tam}}}}}\n")
    for x, y, cor, texto in dados["rotulos"]:
        saida.append(f"  \\put({px(x):.1f},{py(y):.1f}){{\\makebox(0,0){{\\color{{{cor}}}"
                     f"\\fontsize{{23}}{{28}}\\selectfont {tex(texto)}}}}}\n")
    saida.append("\\end{picture}\\\\[22pt]\n\n")
    return "".join(saida)


def tabela(dados: dict) -> str:
    cab, linhas = dados["cabecalho"], dados["linhas"]
    azuis = set(dados.get("azuis", []))
    ncol = len(cab)
    spec = ">{\\bfseries}l" + " r" * (ncol - 1)
    cabecalho = " & ".join(
        [f"\\multicolumn{{1}}{{l}}{{{tex(cab[0])}}}" if not cab[0] else
         f"\\multicolumn{{1}}{{l}}{{\\textbf{{{tex(cab[0])}}}}}"]
        + [f"\\textbf{{{tex(c)}}}" for c in cab[1:]])
    corpo = []
    for i, lin in enumerate(linhas):
        celulas = []
        for j, c in enumerate(lin):
            t = tex(c)
            if (i, j) in azuis:
                t = f"\\textcolor{{azul}}{{\\bfseries {t}}}"
            celulas.append(("\\rule{0pt}{48pt}" if i == 0 and j == 0 else "") + t)
        corpo.append(" & ".join(celulas) + " \\\\")
    return ("\\begin{center}\n{\\fontsize{33}{52}\\selectfont\n"
            f"\\begin{{tabular}}{{{spec}}}\n"
            f"{cabecalho}\\\\[6pt]\n\\hline\n"
            + "\n".join(corpo) + "[10pt]\n\\hline\n"
            "\\end{tabular}}\n\\end{center}\\vspace{28pt}\n\n")


def main() -> int:
    partes = ["% Gerado por gerar_tex.py a partir de conteudo.py. Não editar à mão.\n\n"]

    partes.append("\\vspace*{104pt}\n\\begin{center}\n")
    partes.append("{\\fontsize{42}{56}\\selectfont\\bfseries "
                  + "\\\\[8pt]\n".join(tex(l) for l in conteudo.CAPA["titulo"].split("\n"))
                  + "}\\\\[26pt]\n")
    partes.append("{\\fontsize{29}{38}\\selectfont\\color{cinza} "
                  + "\\\\[6pt]\n".join(tex(l) for l in conteudo.CAPA["sub"].split("\n"))
                  + "}\\\\[46pt]\n\n")
    partes.append("\\includegraphics[height=124pt]{logos/ufopa.png}\\hspace{30pt}%\n"
                  "\\includegraphics[height=124pt]{logos/pet.png}\\\\[30pt]\n\n")
    partes.append("{\\fontsize{24}{34}\\selectfont\n"
                  + tex(conteudo.CAPA["rodape"][0]) + "\\\\[14pt]\n"
                  "\\fontsize{22}{32}\\selectfont\n"
                  + "\\\\\n".join(tex(l) for l in conteudo.CAPA["rodape"][1:])
                  + "}\n\\end{center}\n\\newpage\n\n")

    for s in conteudo.SLIDES:
        partes.append(f"\\begin{{slide}}{{{tex(s['titulo'])}}}\n")
        for tipo, valor in s["blocos"]:
            partes.append(bloco(tipo, valor))
        partes.append("\\end{slide}\n\n")

    SAIDA.write_text("".join(partes), encoding="utf-8")
    print(f"gerado: {SAIDA.name} ({len(conteudo.SLIDES) + 1} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
