#!/usr/bin/env python3
"""Gera o roteiro falado da apresentação como `.docx`.

Não há biblioteca de Office instalada nesta máquina, então o arquivo é montado
como OOXML mínimo — as quatro partes que o Word exige — em vez de depender de
um pacote que não está aqui. O conteúdo falado vive neste arquivo porque é a
única fonte dele: os slides carregam os tópicos, não a fala.

O tempo de cada bloco é somado e conferido contra a janela de 10 a 15 minutos:
o script falha se estourar.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

AQUI = Path(__file__).parent
SAIDA = AQUI / "Roteiro_Apresentacao_PET.docx"

JANELA_S = (10 * 60, 15 * 60)

# (número do slide, título, segundos, [parágrafos de fala], [notas])
# A fala é para ser lida em voz alta: frase curta, sem citação, sem jargão que
# o slide não tenha explicado antes.
ROTEIRO: list[tuple[int, str, int, list[str], list[str]]] = [
    (1, "Capa", 40, [
        "Boa tarde, pessoal. Eu sou o Rafael, sou bolsista de Iniciação Científica aqui no IEG, "
        "orientado pelo professor Celson. Nos próximos dez minutos eu queria contar o que a gente "
        "mediu neste ano sobre bancos de dados vetoriais.",
        "E já adianto qual é a parte interessante: o resultado que a gente ia apresentar no relatório "
        "estava errado, e o que descobriu o erro foi um número que parecia perfeito demais.",
    ], [
        "Não corra na capa. Essa promessa é o que segura a atenção até o slide 11.",
    ]),

    (2, "Roteiro", 20, [
        "O caminho é esse: primeiro por que esse tipo de banco existe, depois como a gente comparou "
        "três deles, e no fim o erro e a lição que ficou.",
    ], []),

    (3, "Buscar por palavra x buscar por significado", 55, [
        "Imagina que você digita, no site da universidade, “como faço para trancar o semestre”.",
        "A busca comum vai procurar essas palavras, exatamente essas. Só que o documento certo, a "
        "resolução, provavelmente não fala “trancar”. Fala “suspensão de matrícula”. Então ele "
        "simplesmente não aparece.",
        "A busca semântica resolve isso: em vez de casar letra com letra, ela procura o que tem o "
        "mesmo sentido. É a peça que faz um assistente conseguir responder sobre os documentos da "
        "sua instituição, e não sobre a internet inteira.",
    ], [
        "Se der abertura, pergunte à plateia se alguém já não achou algo que sabia que existia. "
        "Costuma render aceno de cabeça e engaja.",
    ]),

    (4, "Como um texto vira número", 55, [
        "Para isso funcionar, cada trecho de texto passa por um modelo de linguagem que devolve uma "
        "lista de trezentos e oitenta e quatro números.",
        "Pensa nesses números como uma coordenada. Textos que querem dizer coisas parecidas caem "
        "perto um do outro; textos sobre assuntos diferentes caem longe. Então buscar deixa de ser "
        "uma pergunta sobre palavras e passa a ser uma pergunta de geometria: quais são os dez "
        "pontos mais próximos deste aqui.",
        "No nosso experimento são quinhentos mil trechos. Cada busca, se fosse feita na força bruta, "
        "compararia cento e noventa e dois milhões de números.",
    ], [
        "A frase “é uma pergunta de geometria” é o que faz a ficha cair. Fale devagar.",
    ]),

    (5, "O atalho que todo banco vetorial usa", 55, [
        "Comparar com todos os pontos dá a resposta certa, sempre — e é lento demais para uma tela "
        "que precisa responder em milissegundos.",
        "Então esses bancos constroem um índice aproximado: uma rede de atalhos entre os pontos. A "
        "busca caminha por essa rede em vez de olhar tudo. Fica rapidíssimo, mas com um preço: ela "
        "erra de vez em quando.",
        "E existe um botão de ajuste. Se você deixa a busca explorar mais atalhos, ela acerta mais e "
        "responde mais devagar. Se explora menos, o contrário. Guardem esse botão, porque ele é o "
        "personagem principal daqui a alguns slides.",
    ], [
        "Plantar o botão aqui é o que faz o slide 12 funcionar sem precisar explicar nada de novo.",
    ]),

    (6, "A pergunta do trabalho", 40, [
        "Quem monta um sistema desses cai sempre na mesma dúvida: dá para usar o banco de dados que "
        "eu já tenho, ou eu preciso instalar um banco especializado?",
        "De um lado o PostgreSQL, que quase todo mundo já usa, com uma extensão chamada pgvector. Do "
        "outro, o Qdrant e o Weaviate, que nasceram só para isso. A nossa pergunta é o quanto essa "
        "escolha custa, medido de verdade.",
    ], []),

    (7, "Como medimos", 45, [
        "Para a comparação valer, só uma coisa pode mudar de cada vez. Então a gente travou todo o "
        "resto: mesma máquina, mesmo momento, mesmos textos, mesmo modelo de linguagem, mesmo tipo "
        "de índice com os mesmos parâmetros, mil buscas medidas em cada configuração.",
        "Sobrou uma diferença entre as três medições: o banco. Então a diferença que aparecer é do "
        "banco.",
        "E todo número que eu vou mostrar está num arquivo versionado no repositório do projeto. "
        "Qualquer pessoa aqui pode baixar e conferir.",
    ], [
        "Essa é a parte que dá credibilidade ao resto. Vale um segundo de pausa depois de “conferir”.",
    ]),

    (8, "Três réguas, e um preço", 55, [
        "A gente mede três coisas. Acerto, que é quantos dos dez documentos certos apareceram — o "
        "máximo é um. Tempo, que é quanto demora uma busca. E vazão, que é quantas buscas cabem no "
        "mesmo segundo.",
        "O ponto importante é que as três não melhoram juntas. Girar o botão para acertar mais custa "
        "tempo e vazão, sempre. Por isso a pergunta “qual é o mais rápido” não tem resposta: existe "
        "o melhor num ponto da curva, e o ponto depende do que você precisa.",
    ], []),

    (9, "Buscando: os três acertam", 40, [
        "Primeiro resultado, com cem mil trechos. Os três passam de noventa e sete por cento de "
        "acerto. Nenhum deles é ruim de buscar.",
        "A diferença não está em acertar, está no custo de acertar: o ajuste que cada um precisa "
        "para chegar nesse patamar é diferente, e fica mais alto conforme a base cresce. Nessa "
        "escala o pgvector até responde mais rápido que os outros dois.",
    ], [
        "Se perguntarem por que o Qdrant tem vazão menor: ele acerta mais no mesmo ajuste, então "
        "está num ponto diferente da curva, não numa curva pior.",
    ]),

    (10, "Construindo: aí a diferença aparece", 50, [
        "Segundo resultado, e aqui a diferença é grande. Esse é o tempo para o índice ficar pronto, "
        "com quinhentos mil trechos.",
        "O pgvector leva vinte e um minutos. Os especializados levam menos de três. É de oito a doze "
        "vezes mais tempo, e a diferença cresce com o tamanho da base. Em disco também: o pgvector "
        "ocupa mais que o dobro do Qdrant.",
        "Em troca, quem devora memória é o Weaviate: dois vírgula seis gigabytes, contra cento e "
        "setenta megabytes do Qdrant. Ele mantém a rede de atalhos inteira na memória.",
    ], [
        "Uma ressalva honesta, se o professor perguntar: o pgvector rodou com a configuração padrão "
        "da imagem, que não é dimensionada para construir esse índice. Está declarado no relatório.",
    ]),

    (11, "Com filtro, quase publicamos um erro", 60, [
        "Terceiro resultado, e é onde a história muda. Busca de verdade quase nunca é solta. É "
        "“busque só nos documentos do meu setor”, “só nos contratos vigentes”. Então a gente testou "
        "com filtro.",
        "E o resultado veio assim: com um filtro apertado, deixando só um por cento da base elegível, "
        "o Qdrant e o Weaviate deram acerto de exatamente um. Perfeito. O pgvector deu seis por "
        "cento.",
        "A conclusão estava pronta: os especializados são perfeitos com filtro e o pgvector desaba. "
        "Isso ia para o relatório. E estava errado.",
    ], [
        "Diga “e estava errado” e pare. O silêncio aqui vale mais que qualquer animação.",
    ]),

    (12, "A pista: o botão não fazia nada", 50, [
        "O que pegou foi o botão. Lembram? Girar o botão tem que mudar o acerto. Se não muda, o "
        "índice não está sendo usado.",
        "A gente olhou os cinco ajustes: um, um, um, um e um. Cinco vezes o mesmo valor exato.",
        "Fomos na documentação dos dois sistemas e estava escrito lá: quando o filtro deixa pouca "
        "coisa elegível, eles desistem do índice e conferem um por um, na força bruta. Ou seja, "
        "aquele acerto perfeito não media qualidade de busca. Media que não houve busca aproximada.",
    ], [
        "Aponte para a linha de uns na tela enquanto fala. É o momento mais visual da apresentação.",
    ]),

    (13, "A contraprova", 50, [
        "Para ter certeza, a gente desligou esse atalho e repetiu tudo, forçando os três a usar o "
        "índice de verdade.",
        "O Qdrant se manteve: a vantagem dele é real. O Weaviate caiu de um para cinquenta e seis por "
        "cento — pouco mais da metade dos documentos certos. A vantagem dele era só o atalho.",
        "E o pgvector não se moveu. A gente até acrescentou um índice no campo do filtro, achando que "
        "era isso, e não mudou nada. O problema dele é a ordem das operações, não a falta de índice.",
    ], []),

    (14, "A lição que vale para qualquer medição", 50, [
        "A lição que eu tiro disso não é sobre banco de dados. É sobre medir qualquer coisa.",
        "Resultado perfeito é suspeita, não é conquista. Se o número não muda quando você mexe no "
        "parâmetro que deveria mudá-lo, então o mecanismo que você acha que está medindo não é o que "
        "está rodando.",
        "No nosso caso isso custou uma reescrita do relatório. Se tivesse passado, custaria uma "
        "retratação depois da banca.",
    ], []),

    (15, "Onde estamos, e o que vem", 45, [
        "Fechando: está entregue o ambiente reproduzível dos três bancos, duzentos e quarenta e oito "
        "testes automatizados, dois cenários em duas escalas com os dados versionados, e o relatório "
        "parcial.",
        "Para a segunda metade fica a escala de um milhão, o cenário com escrita e leitura ao mesmo "
        "tempo, repetir as execuções para reportar variação, e comparar duas arquiteturas de máquina "
        "diferentes.",
        "Obrigado. O código e os dados estão nesse endereço, e eu fico à disposição para perguntas.",
    ], []),
]

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
    total = sum(b[2] for b in ROTEIRO)
    corpo = [
        par("Roteiro falado — apresentação do relatório parcial", negrito=True, tam=32, depois=80),
        par("Bancos de dados vetoriais: qual escolher, e por quê", tam=24, cor="464A51", depois=60),
        par(f"Programa de Educação Tutorial · IEG/UFOPA · {len(ROTEIRO)} slides · "
            f"tempo previsto {mmss(total)} (janela de 10 a 15 minutos)",
            tam=20, cor="464A51", depois=240),
        par("Como usar: cada bloco corresponde a um slide. O texto em corpo normal é para ser "
            "falado — não precisa ser decorado, mas foi escrito no ritmo de fala, então ler alto "
            "algumas vezes é suficiente. O que estiver em itálico é orientação de condução, não "
            "para falar.", italico=True, tam=20, cor="464A51", depois=140),
        par("Se o tempo apertar: os slides 4 e 8 são os que aceitam corte sem quebrar a história — "
            "no 4 basta dizer que o texto virou coordenada, e no 8 basta dizer que acertar mais "
            "custa tempo. O miolo são os slides 11, 12 e 13, e eles não devem ser apressados: é "
            "onde está o único achado que a plateia vai levar para casa.",
            italico=True, tam=20, cor="464A51", depois=300),
    ]
    acumulado = 0
    for num, titulo, seg, falas, notas in ROTEIRO:
        acumulado += seg
        corpo.append(par(f"Slide {num} — {titulo}", negrito=True, tam=26, antes=280, depois=40))
        corpo.append(par(f"{mmss(seg)} neste slide · {mmss(acumulado)} acumulados",
                         tam=18, cor="2C71AD", depois=140))
        for f in falas:
            corpo.append(par(f, tam=22, depois=140))
        for n in notas:
            corpo.append(par(n, italico=True, tam=20, cor="464A51", recuo=340, depois=140))

    corpo.append(par("Perguntas que provavelmente vêm", negrito=True, tam=26, antes=400, depois=60))
    for p, r in PERGUNTAS:
        corpo.append(par(p, negrito=True, tam=21, depois=40))
        corpo.append(par(r, tam=21, recuo=340, depois=160))

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(corpo) +
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1418"/></w:sectPr>'
        "</w:body></w:document>"
    )


PERGUNTAS: list[tuple[str, str]] = [
    ("“Então qual eu devo usar?”",
     "Depende do que aperta. Se o seu problema é buscar com filtro apertado, o Qdrant é o único que "
     "sustentou. Se você já tem PostgreSQL e o filtro não é restritivo, o pgvector resolve e você "
     "não instala mais nada. Se memória é o recurso escasso, o Weaviate é o pior dos três."),
    ("“Por que só quinhentos mil, e não milhões?”",
     "Um milhão está no cronograma para a segunda metade do ano. A escala atual já mostra o efeito, "
     "e a diferença de tempo de construção cresce com a base, então a tendência não deve mudar."),
    ("“Vocês testaram uma vez só?”",
     "Cada configuração foi medida uma vez, e isso é uma limitação que está declarada no relatório. "
     "O acerto se reproduziu quando refizemos a medição; a latência de cauda não. Repetir as "
     "execuções e reportar a variação é trabalho da próxima fase."),
    ("“Isso é comparação justa? Um é banco relacional.”",
     "É justa no que ela promete medir: os três receberam os mesmos dados, o mesmo tipo de índice e "
     "os mesmos parâmetros de construção. Onde não é simétrica, está dito — o pgvector rodou com a "
     "configuração padrão da imagem para construir o índice, e isso é uma ressalva no texto."),
]


def main() -> int:
    total = sum(b[2] for b in ROTEIRO)
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
    palavras = sum(len(f.split()) for _, _, _, falas, _ in ROTEIRO for f in falas)
    print(f"palavras de fala: {palavras} (~{palavras / (total / 60):.0f} por minuto)")
    print(f"gerado: {SAIDA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
