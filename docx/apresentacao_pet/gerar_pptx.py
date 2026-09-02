#!/usr/bin/env python3
"""Gera a apresentação em `.pptx` a partir do conteúdo declarado aqui.

Não há biblioteca de Office nesta máquina, então o arquivo é montado como
PresentationML mínimo: pacote, apresentação, um mestre, um layout em branco, um
tema e um XML por slide.

O texto vem de `conteudo.py`, que é a fonte única dos três artefatos — este
`.pptx`, o corpo do `slides.tex` e o roteiro falado. `--verificar` confere que
os números do PDF já compilado e os do conteúdo são o mesmo conjunto, o que
pega corpo gerado desatualizado no disco.

Limite honesto: sem PowerPoint nem LibreOffice instalados, não é possível
renderizar o `.pptx` para conferir a diagramação. O XML é validado, as caixas
têm folga e `normAutofit` está ligado para o PowerPoint encolher o texto se
alguma caixa apertar -- mas a conferência visual é do piloto.
"""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import conteudo

AQUI = Path(__file__).parent
SAIDA = AQUI / "Apresentacao_PET.pptx"
PDF = AQUI / "slides.pdf"

EMU = 914400  # por polegada
LARGURA = 12192000  # 13,333 in
ALTURA = 6858000  # 7,5 in
MARGEM = 609600  # 0,667 in, mesma proporção do deck em LaTeX
CONTEUDO = LARGURA - 2 * MARGEM

AZUL = "2C71AD"
NAVY = "152039"
CINZA = "464A51"
CINZACLARO = "E9F1F2"
PRETO = "000000"
BRANCO = "FFFFFF"

# -----------------------------------------------------------------------------
# Conteúdo: importado de conteudo.py, a fonte única.
# -----------------------------------------------------------------------------

CAPA = conteudo.CAPA
SLIDES = conteudo.SLIDES

NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')


# -----------------------------------------------------------------------------
# Marcação inline -> runs
# -----------------------------------------------------------------------------

def runs(texto: str, *, sz: int, cor: str = PRETO) -> str:
    """Converte `*azul*`, `**negrito**` e `_itálico_` em runs do DrawingML."""
    saida = []
    for parte in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_)", texto):
        if not parte:
            continue
        b, i, c = False, False, cor
        if parte.startswith("**") and parte.endswith("**"):
            parte, b = parte[2:-2], True
        elif parte.startswith("*") and parte.endswith("*"):
            parte, b, c = parte[1:-1], True, AZUL
        elif parte.startswith("_") and parte.endswith("_"):
            parte, i = parte[1:-1], True
        props = f'sz="{sz}" b="{1 if b else 0}" i="{1 if i else 0}" dirty="0"'
        saida.append(
            f'<a:r><a:rPr lang="pt-BR" {props}>'
            f'<a:solidFill><a:srgbClr val="{c}"/></a:solidFill>'
            f'<a:latin typeface="Arial"/></a:rPr>'
            f'<a:t>{escape(parte)}</a:t></a:r>'
        )
    return "".join(saida) or f'<a:endParaRPr lang="pt-BR" sz="{sz}"/>'


def paragrafo(texto: str, *, sz: int, cor: str = PRETO, alinha: str = "l",
              espaco_antes: int = 0, entrelinha: int = 100) -> str:
    return (
        f'<a:p><a:pPr algn="{alinha}">'
        f'<a:lnSpc><a:spcPct val="{entrelinha * 1000}"/></a:lnSpc>'
        f'<a:spcBef><a:spcPts val="{espaco_antes}"/></a:spcBef></a:pPr>'
        f"{runs(texto, sz=sz, cor=cor)}</a:p>"
    )


def caixa(idx: int, nome: str, x: int, y: int, cx: int, cy: int, paras: str,
          *, fundo: str | None = None, pad: int = 91440, ancora: str = "t") -> str:
    fill = (f'<a:solidFill><a:srgbClr val="{fundo}"/></a:solidFill>'
            if fundo else "<a:noFill/>")
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{idx}" name="{escape(nome)}"/>'
        f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fill}</p:spPr>'
        f'<p:txBody><a:bodyPr wrap="square" lIns="{pad}" tIns="{pad}" rIns="{pad}" '
        f'bIns="{pad}" anchor="{ancora}"><a:normAutofit/></a:bodyPr>'
        f"<a:lstStyle/>{paras}</p:txBody></p:sp>"
    )


def retangulo(idx: int, x: int, y: int, cx: int, cy: int, cor: str) -> str:
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{idx}" name="barra{idx}"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{cor}"/></a:solidFill>'
        f"<a:ln><a:noFill/></a:ln></p:spPr>"
        f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>'
    )


def imagem(idx: int, rid: str, x: int, y: int, cx: int, cy: int) -> str:
    return (
        f'<p:pic><p:nvPicPr><p:cNvPr id="{idx}" name="logo{idx}"/>'
        f'<p:cNvPicPr/><p:nvPr/></p:nvPicPr>'
        f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
    )


def envelope_slide(formas: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:sld {NS}><p:cSld><p:spTree>"
        f'<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        f'<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        f'<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        f"{formas}</p:spTree></p:cSld>"
        f'<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
    )


# -----------------------------------------------------------------------------
# Montagem dos slides
# -----------------------------------------------------------------------------

TITULO_SZ = 3200
CORPO_SZ = 1800
NOTA_SZ = 1500


def monta_capa() -> str:
    f = []
    f.append(caixa(2, "titulo", MARGEM, int(1.15 * EMU), CONTEUDO, int(1.5 * EMU),
                   "".join(paragrafo(f"**{l}**", sz=4000, alinha="ctr")
                           for l in CAPA["titulo"].split("\n"))))
    f.append(caixa(3, "sub", MARGEM, int(2.75 * EMU), CONTEUDO, int(0.95 * EMU),
                   "".join(paragrafo(l, sz=2000, cor=CINZA, alinha="ctr")
                           for l in CAPA["sub"].split("\n"))))
    alt = int(1.05 * EMU)
    larg_u = int(alt * 403 / 420)
    larg_p = int(alt * 420 / 397)
    total = larg_u + larg_p + int(0.22 * EMU)
    x0 = (LARGURA - total) // 2
    f.append(imagem(4, "rId2", x0, int(3.85 * EMU), larg_u, alt))
    f.append(imagem(5, "rId3", x0 + larg_u + int(0.22 * EMU), int(3.85 * EMU), larg_p, alt))
    paras = [paragrafo(CAPA["rodape"][0], sz=1600, alinha="ctr")]
    paras += [paragrafo(l, sz=1400, cor=CINZA, alinha="ctr", espaco_antes=200)
              for l in CAPA["rodape"][1:]]
    f.append(caixa(6, "rodape", MARGEM, int(5.15 * EMU), CONTEUDO, int(1.6 * EMU),
                   "".join(paras)))
    return envelope_slide("".join(f))


def monta_slide(dados: dict, numero: int) -> str:
    f = []
    idx = 2
    f.append(caixa(idx, "titulo", MARGEM, int(0.42 * EMU), CONTEUDO, int(0.75 * EMU),
                   paragrafo(f"**{dados['titulo']}**", sz=TITULO_SZ)))
    idx += 1
    y = int(1.35 * EMU)

    for tipo, valor in dados["blocos"]:
        if tipo == "texto":
            alt = int(0.34 * EMU) * (1 + len(valor) // 120)
            f.append(caixa(idx, "texto", MARGEM, y, CONTEUDO, alt,
                           paragrafo(valor, sz=CORPO_SZ, entrelinha=125), pad=0))
            y += alt + int(0.12 * EMU)
        elif tipo == "nota":
            alt = int(0.30 * EMU) * (1 + len(valor) // 130)
            f.append(caixa(idx, "nota", MARGEM, y, CONTEUDO, alt,
                           paragrafo(valor, sz=NOTA_SZ, cor=CINZA, entrelinha=125), pad=0))
            y += alt + int(0.12 * EMU)
        elif tipo == "nota_centro":
            f.append(caixa(idx, "nota", MARGEM, y, CONTEUDO, int(0.4 * EMU),
                           paragrafo(valor, sz=NOTA_SZ, cor=CINZA, alinha="ctr"), pad=0))
            y += int(0.5 * EMU)
        elif tipo == "frase":
            linhas = valor.split("\n")
            alt = int(0.52 * EMU) * len(linhas)
            f.append(caixa(idx, "frase", MARGEM, y, CONTEUDO, alt,
                           "".join(paragrafo(f"*{l}*", sz=2600, alinha="ctr")
                                   for l in linhas), pad=0))
            y += alt + int(0.16 * EMU)
        elif tipo == "cartoes":
            n = len(valor)
            vao = int(0.22 * EMU)
            larg = (CONTEUDO - vao * (n - 1)) // n
            altura = int(1.55 * EMU)
            for k, (tit, txt) in enumerate(valor):
                paras = (paragrafo(tit, sz=1700, cor=BRANCO)
                         + paragrafo(txt, sz=1400, cor=BRANCO, espaco_antes=500,
                                     entrelinha=120))
                f.append(caixa(idx, f"cartao{k}", MARGEM + k * (larg + vao), y,
                               larg, altura, paras, fundo=AZUL, pad=137160))
                idx += 1
            y += altura + int(0.18 * EMU)
            continue
        elif tipo == "destaques":
            n = len(valor)
            vao = int(0.22 * EMU)
            larg = (CONTEUDO - vao * (n - 1)) // n
            altura = int(1.35 * EMU)
            for k, (palavra, legenda) in enumerate(valor):
                paras = (paragrafo(palavra, sz=3200, cor=AZUL)
                         + paragrafo(legenda, sz=1400, cor=CINZA, espaco_antes=600,
                                     entrelinha=125))
                f.append(caixa(idx, f"destaque{k}", MARGEM + k * (larg + vao), y,
                               larg, altura, paras, pad=0))
                idx += 1
            y += altura + int(0.18 * EMU)
            continue
        elif tipo == "colunas":
            vao = int(0.3 * EMU)
            larg = (CONTEUDO - vao) // 2
            altura = int(0.42 * EMU) * max(len(c) for c in valor)
            for k, col in enumerate(valor):
                paras = "".join(paragrafo(l, sz=CORPO_SZ, espaco_antes=500 if j else 0)
                                for j, l in enumerate(col))
                f.append(caixa(idx, f"coluna{k}", MARGEM + k * (larg + vao), y,
                               larg, altura, paras, pad=0))
                idx += 1
            y += altura + int(0.18 * EMU)
            continue
        elif tipo == "colunas_titulo":
            vao = int(0.3 * EMU)
            larg = (CONTEUDO - vao) // 2
            altura = int(0.36 * EMU) * (1 + max(len(c[1]) for c in valor))
            for k, (tit, itens) in enumerate(valor):
                paras = paragrafo(f"**{tit}**", sz=2000, cor=PRETO)
                paras += "".join(paragrafo(l, sz=1600, espaco_antes=400)
                                 for l in itens)
                f.append(caixa(idx, f"colt{k}", MARGEM + k * (larg + vao), y,
                               larg, altura, paras, pad=0))
                idx += 1
            y += altura + int(0.2 * EMU)
            continue
        elif tipo == "barras":
            maior = int(6.9 * EMU) - MARGEM - int(2.4 * EMU)
            alt_b = int(0.34 * EMU)
            for k, (rot, prop, texto) in enumerate(valor):
                yy = y + k * int(0.55 * EMU)
                f.append(caixa(idx, f"rot{k}", MARGEM, yy, int(1.7 * EMU), alt_b,
                               paragrafo(rot, sz=1700), pad=0, ancora="ctr"))
                idx += 1
                largura_b = max(int(maior * prop), int(0.16 * EMU))
                f.append(retangulo(idx, MARGEM + int(1.8 * EMU), yy, largura_b, alt_b, AZUL))
                idx += 1
                f.append(caixa(idx, f"val{k}", MARGEM + int(1.95 * EMU) + largura_b, yy,
                               int(2.4 * EMU), alt_b,
                               paragrafo(f"**{texto}**", sz=1700), pad=0, ancora="ctr"))
                idx += 1
            y += len(valor) * int(0.55 * EMU) + int(0.16 * EMU)
            continue
        elif tipo == "tabela":
            f.append(tabela(idx, valor, y))
            idx += 1
            y += int(0.46 * EMU) * (1 + len(valor["linhas"])) + int(0.3 * EMU)
            continue
        elif tipo == "caixa":
            alt = int(0.36 * EMU) * (2 + len(valor) // 150)
            f.append(caixa(idx, "destaque", MARGEM, y, CONTEUDO, alt,
                           paragrafo(valor, sz=1900, entrelinha=130),
                           fundo=CINZACLARO, pad=137160, ancora="ctr"))
            y += alt + int(0.18 * EMU)
        elif tipo == "caixa_navy":
            paras = (paragrafo(valor[0], sz=2400, cor=BRANCO, entrelinha=125)
                     + paragrafo(valor[1], sz=1900, cor=BRANCO, espaco_antes=900,
                                 entrelinha=130))
            alt = int(1.75 * EMU)
            f.append(caixa(idx, "licao", MARGEM, y, CONTEUDO, alt, paras,
                           fundo=NAVY, pad=182880, ancora="ctr"))
            y += alt + int(0.22 * EMU)
        idx += 1

    # A diagramação do .pptx não pode ser conferida a olho nesta máquina, então
    # o limite inferior da área útil é verificado aqui. Estourar significa
    # conteúdo por baixo do rodapé, e é falha de build, não aviso.
    LIMITE = ALTURA - int(0.95 * EMU)
    if y > LIMITE:
        raise SystemExit(
            f"slide {numero} ({dados['titulo']!r}) estoura a área útil: "
            f"conteúdo termina em {y / EMU:.2f} in, limite {LIMITE / EMU:.2f} in"
        )
    ALTURAS[numero] = y

    # rodapé: logo do PET e número do slide, em todos os slides de conteúdo
    f.append(imagem(idx, "rId2", MARGEM, ALTURA - int(0.72 * EMU),
                    int(0.44 * EMU * 150 / 141), int(0.44 * EMU)))
    idx += 1
    f.append(caixa(idx, "num", LARGURA - MARGEM - int(0.6 * EMU),
                   ALTURA - int(0.66 * EMU), int(0.5 * EMU), int(0.34 * EMU),
                   paragrafo(str(numero), sz=1400, cor=CINZA, alinha="r"), pad=0))
    return envelope_slide("".join(f))


# Onde cada slide termina, em EMU. Preenchido por monta_slide e relatado no fim.
ALTURAS: dict[int, int] = {}


def tabela(idx: int, dados: dict, y: int) -> str:
    cab, linhas = dados["cabecalho"], dados["linhas"]
    azuis = set(dados.get("azuis", []))
    ncol = len(cab)
    prim = int(1.9 * EMU)
    resto = ncol - 1
    larg_total = min(CONTEUDO, prim + resto * int(1.7 * EMU))
    larg_col = (larg_total - prim) // resto
    alt_lin = int(0.46 * EMU)
    grid = "".join(f'<a:gridCol w="{prim if k == 0 else larg_col}"/>' for k in range(ncol))

    def celula(txt: str, *, negrito: bool, azul: bool, alinha: str) -> str:
        cor = AZUL if azul else PRETO
        marca = f"**{txt}**" if (negrito or azul) else txt
        return (
            f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>'
            f"{paragrafo(marca, sz=1800, cor=cor, alinha=alinha)}"
            f'</a:txBody><a:tcPr marL="45720" marR="45720" anchor="ctr"/></a:tc>'
        )

    linhas_xml = ['<a:tr h="%d">' % alt_lin]
    for k, c in enumerate(cab):
        linhas_xml.append(celula(c, negrito=True, azul=False,
                                 alinha="l" if k == 0 else "r"))
    linhas_xml.append("</a:tr>")
    for i, lin in enumerate(linhas):
        linhas_xml.append('<a:tr h="%d">' % alt_lin)
        for j, c in enumerate(lin):
            linhas_xml.append(celula(
                c, negrito=(j == 0), azul=((i, j) in azuis),
                alinha="l" if j == 0 else "r"))
        linhas_xml.append("</a:tr>")

    x = MARGEM + (CONTEUDO - larg_total) // 2
    return (
        f'<p:graphicFrame><p:nvGraphicFramePr>'
        f'<p:cNvPr id="{idx}" name="tabela"/><p:cNvGraphicFramePr/><p:nvPr/>'
        f"</p:nvGraphicFramePr>"
        f'<p:xfrm><a:off x="{x}" y="{y}"/>'
        f'<a:ext cx="{larg_total}" cy="{alt_lin * (1 + len(linhas))}"/></p:xfrm>'
        f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
        f'<a:tbl><a:tblPr firstRow="1"/><a:tblGrid>{grid}</a:tblGrid>'
        f'{"".join(linhas_xml)}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>'
    )


# -----------------------------------------------------------------------------
# Partes fixas do pacote
# -----------------------------------------------------------------------------

def content_types(n: int) -> str:
    over = "".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, n + 1))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
        f"{over}</Types>"
    )


RELS_RAIZ = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
    "</Relationships>"
)


def presentation(n: int) -> str:
    ids = "".join(f'<p:sldId id="{256 + i}" r:id="rId{i + 2}"/>' for i in range(n))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<p:presentation {NS} saveSubsetFonts=\"1\">"
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        f"<p:sldIdLst>{ids}</p:sldIdLst>"
        f'<p:sldSz cx="{LARGURA}" cy="{ALTURA}"/>'
        '<p:notesSz cx="6858000" cy="9144000"/>'
        "</p:presentation>"
    )


def presentation_rels(n: int) -> str:
    r = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    for i in range(n):
        r.append(f'<Relationship Id="rId{i + 2}" '
                 f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
                 f'Target="slides/slide{i + 1}.xml"/>')
    r.append(f'<Relationship Id="rId{n + 2}" '
             f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
             f'Target="theme/theme1.xml"/>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(r) + "</Relationships>")


ARVORE_VAZIA = (
    '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
    '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
    '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree>'
)

MAPA_CORES = ('<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
              'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
              'accent6="accent6" hlink="hlink" folHlink="folHlink"/>')

SLIDE_MASTER = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f"<p:sldMaster {NS}><p:cSld>"
    '<p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>'
    "<a:effectLst/></p:bgPr></p:bg>"
    f"{ARVORE_VAZIA}</p:cSld>{MAPA_CORES}"
    '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
    "</p:sldMaster>"
)

SLIDE_MASTER_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>'
    "</Relationships>"
)

SLIDE_LAYOUT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<p:sldLayout {NS} type="blank" preserve="1"><p:cSld name="Em branco">'
    f"{ARVORE_VAZIA}</p:cSld>"
    '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
)

SLIDE_LAYOUT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
    "</Relationships>"
)


def _estilo(nome: str) -> str:
    return (
        f"<a:{nome}><a:lnRef idx=\"0\"><a:scrgbClr r=\"0\" g=\"0\" b=\"0\"/></a:lnRef>"
        f'<a:fillRef idx="0"><a:scrgbClr r="0" g="0" b="0"/></a:fillRef>'
        f'<a:effectRef idx="0"><a:scrgbClr r="0" g="0" b="0"/></a:effectRef>'
        f'<a:fontRef idx="none"/></a:{nome}>'
    )


TEMA = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="PET">'
    "<a:themeElements>"
    '<a:clrScheme name="PET">'
    '<a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
    f'<a:dk2><a:srgbClr val="{NAVY}"/></a:dk2><a:lt2><a:srgbClr val="{CINZACLARO}"/></a:lt2>'
    f'<a:accent1><a:srgbClr val="{AZUL}"/></a:accent1>'
    f'<a:accent2><a:srgbClr val="{NAVY}"/></a:accent2>'
    '<a:accent3><a:srgbClr val="FFC857"/></a:accent3>'
    f'<a:accent4><a:srgbClr val="{CINZA}"/></a:accent4>'
    '<a:accent5><a:srgbClr val="B8BEBF"/></a:accent5>'
    '<a:accent6><a:srgbClr val="E9F1F2"/></a:accent6>'
    f'<a:hlink><a:srgbClr val="{AZUL}"/></a:hlink>'
    f'<a:folHlink><a:srgbClr val="{CINZA}"/></a:folHlink>'
    "</a:clrScheme>"
    '<a:fontScheme name="PET">'
    '<a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
    '<a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>'
    "</a:fontScheme>"
    '<a:fmtScheme name="PET">'
    "<a:fillStyleLst>"
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    "</a:fillStyleLst>"
    "<a:lnStyleLst>"
    '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    "</a:lnStyleLst>"
    "<a:effectStyleLst>"
    "<a:effectStyle><a:effectLst/></a:effectStyle>"
    "<a:effectStyle><a:effectLst/></a:effectStyle>"
    "<a:effectStyle><a:effectLst/></a:effectStyle>"
    "</a:effectStyleLst>"
    "<a:bgFillStyleLst>"
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    "</a:bgFillStyleLst>"
    "</a:fmtScheme></a:themeElements>"
    "</a:theme>"
)


def slide_rels(com_ufopa: bool) -> str:
    r = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>']
    if com_ufopa:
        r.append('<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/ufopa.png"/>')
        r.append('<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/pet.png"/>')
    else:
        r.append('<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/pet-rodape.png"/>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(r) + "</Relationships>")


# -----------------------------------------------------------------------------
# Guarda: os números daqui e os do PDF têm de ser o mesmo conjunto
# -----------------------------------------------------------------------------

def numeros(texto: str) -> set[str]:
    """Números com casa decimal ou separador de milhar, que são os que
    carregam resultado. Inteiros soltos ficam de fora de propósito: aparecem
    em contexto de prosa ('os 10 pontos', 'três sistemas') e gerariam ruído."""
    achados = re.findall(r"\d+(?:\.\d{3})+|\d+,\d+", texto)
    return {a.replace(".", "") for a in achados}


def texto_do_conteudo() -> str:
    partes = [CAPA["titulo"], CAPA["sub"], *CAPA["rodape"]]
    for s in SLIDES:
        partes.append(s["titulo"])
        for tipo, valor in s["blocos"]:
            if isinstance(valor, str):
                partes.append(valor)
            elif tipo == "tabela":
                partes += valor["cabecalho"]
                for lin in valor["linhas"]:
                    partes += lin
            elif tipo == "barras":
                partes += [f"{r} {t}" for r, _, t in valor]
            elif tipo == "cartoes" or tipo == "destaques":
                partes += [a for par in valor for a in par]
            elif tipo == "colunas":
                partes += [l for col in valor for l in col]
            elif tipo == "colunas_titulo":
                partes += [c[0] for c in valor] + [l for c in valor for l in c[1]]
            elif tipo == "caixa_navy":
                partes += valor
    return "\n".join(partes)


def verificar() -> int:
    if not PDF.exists():
        print(f"{PDF.name} não existe — rode `make slides` antes.", file=sys.stderr)
        return 1
    pdf = subprocess.run(["pdftotext", str(PDF), "-"], capture_output=True,
                         text=True, check=True).stdout
    a, b = numeros(texto_do_conteudo()), numeros(pdf)
    so_pptx, so_pdf = sorted(a - b), sorted(b - a)
    print(f"números no conteúdo do pptx: {len(a)} | no PDF dos slides: {len(b)}")
    if so_pptx or so_pdf:
        print("\nDIVERGÊNCIA entre gerar_pptx.py e slides.tex:", file=sys.stderr)
        if so_pptx:
            print(f"  só no pptx: {so_pptx}", file=sys.stderr)
        if so_pdf:
            print(f"  só no PDF:  {so_pdf}", file=sys.stderr)
        return 1
    print("os dois lados citam exatamente os mesmos números.")
    return 0


def main() -> int:
    if "--verificar" in sys.argv:
        return verificar()

    n = 1 + len(SLIDES)
    partes: dict[str, bytes | str] = {
        "[Content_Types].xml": content_types(n),
        "_rels/.rels": RELS_RAIZ,
        "ppt/presentation.xml": presentation(n),
        "ppt/_rels/presentation.xml.rels": presentation_rels(n),
        "ppt/slideMasters/slideMaster1.xml": SLIDE_MASTER,
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": SLIDE_MASTER_RELS,
        "ppt/slideLayouts/slideLayout1.xml": SLIDE_LAYOUT,
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": SLIDE_LAYOUT_RELS,
        "ppt/theme/theme1.xml": TEMA,
        "ppt/slides/slide1.xml": monta_capa(),
        "ppt/slides/_rels/slide1.xml.rels": slide_rels(True),
    }
    for i, dados in enumerate(SLIDES, start=2):
        partes[f"ppt/slides/slide{i}.xml"] = monta_slide(dados, i)
        partes[f"ppt/slides/_rels/slide{i}.xml.rels"] = slide_rels(False)
    for nome in ("ufopa.png", "pet.png", "pet-rodape.png"):
        partes[f"ppt/media/{nome}"] = (AQUI / "logos" / nome).read_bytes()

    if SAIDA.exists():
        SAIDA.unlink()
    with zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, dados in partes.items():
            z.writestr(nome, dados if isinstance(dados, bytes) else dados.encode("utf-8"))

    print(f"slides: {n} (capa + {len(SLIDES)})")
    print(f"partes no pacote: {len(partes)}")
    limite = (ALTURA - int(0.95 * EMU)) / EMU
    pior = max(ALTURAS.items(), key=lambda kv: kv[1])
    print(f"ocupação vertical: pior caso no slide {pior[0]} com "
          f"{pior[1] / EMU:.2f} in de {limite:.2f} in úteis")
    print(f"gerado: {SAIDA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
