#!/usr/bin/env python3
"""Gera o roteiro falado da apresentação como `.docx`.

Não há biblioteca de Office instalada nesta máquina, então o arquivo é montado
como OOXML mínimo — as quatro partes que o Word exige — em vez de depender de
um pacote que não está aqui. O texto falado vem de `conteudo.py`, a mesma
fonte dos slides e do `.pptx`.

O tempo de cada bloco é somado e conferido contra a janela de 10 a 15 minutos:
o script falha se estourar.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import conteudo

AQUI = Path(__file__).parent
SAIDA = AQUI / "Roteiro_Apresentacao_PET.docx"

JANELA_S = (10 * 60, 15 * 60)

ROTEIRO = conteudo.ROTEIRO
PERGUNTAS = conteudo.PERGUNTAS

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>
<w:sz w:val="22"/><w:szCs w:val="22"/>
</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
</w:styles>"""


def par(texto: str, *, negrito=False, italico=False, tam=22, cor=None,
        antes=0, depois=120, recuo=0) -> str:
    """Um parágrafo com um único run. `tam` em meios-pontos, como no OOXML."""
    rpr = ["<w:rFonts w:ascii=\"Calibri\" w:hAnsi=\"Calibri\"/>"]
    if negrito:
        rpr.append("<w:b/>")
    if italico:
        rpr.append("<w:i/>")
    if cor:
        rpr.append(f'<w:color w:val="{cor}"/>')
    rpr.append(f'<w:sz w:val="{tam}"/>')
    ind = f'<w:ind w:left="{recuo}"/>' if recuo else ""
    return (
        "<w:p><w:pPr>"
        f'<w:spacing w:before="{antes}" w:after="{depois}" w:line="276" w:lineRule="auto"/>'
        f"{ind}</w:pPr>"
        f"<w:r><w:rPr>{''.join(rpr)}</w:rPr>"
        f'<w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>'
    )


def mmss(seg: int) -> str:
    return f"{seg // 60}:{seg % 60:02d}"


def documento() -> str:
    total = sum(b["seg"] for b in ROTEIRO)
    corpo = [
        par("Roteiro de fala", negrito=True, tam=32, depois=80),
        par("Bancos de dados vetoriais: qual escolher, e por quê", tam=24, cor="464A51", depois=60),
        par(f"PET/IEG · {len(ROTEIRO)} slides · tempo previsto {mmss(total)} "
            f"(a janela é de 10 a 15 minutos)", tam=20, cor="464A51", depois=240),
        par("Cada bloco é um slide. As linhas são deixas, não texto para ler: são frases "
            "curtas na ordem em que fazem sentido, para você falar com as suas palavras. "
            "O que está em itálico é orientação de condução e não se fala.",
            italico=True, tam=20, cor="464A51", depois=140),
        par("Se o tempo apertar, corte nos slides 4 e 8. No 4 basta dizer que o texto virou "
            "coordenada; no 8, que acertar mais custa tempo. Os slides 11, 12 e 13 são o miolo "
            "e não devem ser apressados.",
            italico=True, tam=20, cor="464A51", depois=300),
    ]
    acumulado = 0
    for b in ROTEIRO:
        acumulado += b["seg"]
        corpo.append(par(f"Slide {b['slide']} — {b['titulo']}",
                         negrito=True, tam=26, antes=280, depois=30))
        corpo.append(par(f"{mmss(b['seg'])} · {mmss(acumulado)} acumulados   |   {b['ideia']}",
                         tam=18, cor="2C71AD", depois=120))
        for f in b["falas"]:
            corpo.append(par("— " + f, tam=22, depois=60, recuo=200))
        for n in b["notas"]:
            corpo.append(par(n, italico=True, tam=20, cor="464A51", recuo=200, antes=120, depois=60))

    corpo.append(par("Se perguntarem", negrito=True, tam=26, antes=400, depois=60))
    for p, r in PERGUNTAS:
        corpo.append(par(p, negrito=True, tam=21, antes=140, depois=40))
        corpo.append(par(r, tam=21, recuo=340, depois=100))

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(corpo) +
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1418"/></w:sectPr>'
        "</w:body></w:document>"
    )


def main() -> int:
    total = sum(b["seg"] for b in ROTEIRO)
    lo, hi = JANELA_S
    print(f"slides: {len(ROTEIRO)}")
    print(f"tempo previsto: {mmss(total)} (janela {mmss(lo)}–{mmss(hi)})")
    if not lo <= total <= hi:
        print("FORA DA JANELA DE TEMPO", flush=True)
        return 1

    partes = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": RELS,
        "word/_rels/document.xml.rels": DOC_RELS,
        "word/styles.xml": STYLES,
        "word/document.xml": documento(),
    }
    if SAIDA.exists():
        SAIDA.unlink()
    with zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, dados in partes.items():
            z.writestr(nome, dados.encode("utf-8"))
    palavras = sum(len(f.split()) for b in ROTEIRO for f in b["falas"])
    print(f"palavras de fala: {palavras} (~{palavras / (total / 60):.0f} por minuto)")
    print(f"gerado: {SAIDA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
