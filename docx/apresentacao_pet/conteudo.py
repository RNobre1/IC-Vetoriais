#!/usr/bin/env python3
"""Fonte única do conteúdo da apresentação para o PET.

Os três artefatos derivam daqui: o corpo do `slides.tex` (por `gerar_tex.py`),
o `.pptx` (por `gerar_pptx.py`) e o roteiro falado em `.docx` (por
`gerar_roteiro.py`). Texto muda aqui e em nenhum outro lugar.

Registro: sóbrio. Títulos de slide são frases nominais descritivas, como em
apresentação técnica, e não frases de narrativa em primeira pessoa. O corpo
evita jargão de banco de dados sem tradução, porque o público é o PET do IEG,
em maioria de engenharia, mas evita também tom coloquial: o professor
orientador está na sala e o trabalho é o mesmo do artigo submetido.

O título da capa é o título oficial do trabalho, igual ao da submissão à
Jornada Acadêmica. Não encurtar nem reescrever.

Marcação inline aceita pelos três geradores:
  *texto*    destaque em azul e negrito
  **texto**  negrito
  _texto_    itálico
"""

CAPA = {
    # Título oficial do trabalho, o mesmo do artigo. Quebrado em linhas apenas
    # para caber na capa; o texto é literal.
    "titulo": "Comparação de desempenho de soluções de bancos de dados\n"
              "vetoriais para busca semântica:",
    "sub": "uma análise entre pgvector e bancos de dados especializados",
    "rodape": [
        "Rafael Nobre de Souza   |   Orientador: Prof. Dr. Celson Pantoja Lima",
        "Universidade Federal do Oeste do Pará",
        "Instituto de Engenharia e Geociências",
        "Programa de Educação Tutorial",
        "Relatório parcial de Iniciação Científica · 2026",
    ],
}

SLIDES: list[dict] = [
    {
        "titulo": "Roteiro",
        "blocos": [
            ("colunas", [
                ["**1.** Busca semântica: o problema",
                 "**2.** Representação vetorial e busca aproximada",
                 "**3.** Objetivo e metodologia"],
                ["**4.** Resultados",
                 "**5.** Próximas etapas"],
            ]),
        ],
    },
    {
        "titulo": "Busca por palavra-chave e busca semântica",
        "blocos": [
            ("texto", "Uma consulta por **trancar o semestre** não encontra a resolução que "
                      "trata do assunto, porque o documento usa outro termo: **suspensão de "
                      "matrícula**."),
            ("texto", "A busca por palavra-chave compara caracteres. Termos diferentes para o "
                      "mesmo conceito não são reconhecidos."),
            ("cartoes", [
                ("Busca por palavra-chave", "Compara caracteres. Termo diferente, resultado ausente."),
                ("Busca semântica", "Compara significado. Reconhece o conceito em outra redação."),
                ("Aplicação", "Assistentes que respondem sobre o acervo de documentos de uma instituição."),
            ]),
        ],
    },
    {
        "titulo": "Representação vetorial do texto",
        "blocos": [
            ("texto", "Um modelo de linguagem converte cada trecho de texto em *384 números*, "
                      "que funcionam como uma coordenada em um espaço de 384 eixos."),
            ("texto", "Trechos de conteúdo semelhante ocupam posições próximas nesse espaço. A "
                      "busca passa a ser um **cálculo de distância**."),
            ("diagrama", {
                "altura": 190,
                "pontos": [(14, 74, "azul", 14), (22, 60, "azul", 14), (10, 52, "azul", 14),
                           (20, 82, "azul", 14), (30, 68, "azul", 14),
                           (74, 30, "navy", 14), (82, 44, "navy", 14), (88, 26, "navy", 14),
                           (70, 46, "navy", 14)],
                "arestas": [],
                "rotulos": [(20, 30, "cinza", "trechos sobre o mesmo assunto"),
                            (79, 70, "cinza", "trechos sobre outro assunto")],
            }),
            ("nota", "Na base utilizada há 500 mil trechos. Comparar a consulta com todos, um a "
                     "um, envolve 192 milhões de números por busca."),
        ],
    },
    {
        "titulo": "Busca exata e busca aproximada",
        "blocos": [
            ("texto", "A comparação com todos os pontos fornece o resultado exato, com custo "
                      "incompatível com resposta em milissegundos."),
            ("texto", "Os sistemas constroem então um *índice aproximado*: uma malha de ligações "
                      "entre os pontos, percorrida no lugar da varredura completa."),
            ("diagrama", {
                "altura": 250,
                "pontos": [(6, 82, 'navy', 12), (23, 90, 'navy', 12), (39, 76, 'navy', 12), (8, 58, 'navy', 12), (41, 54, 'navy', 12), (7, 30, 'navy', 12), (22, 16, 'navy', 12), (38, 26, 'navy', 12), (25, 68, 'navy', 12), (62, 82, 'navy', 12), (79, 90, 'navy', 12), (95, 76, 'navy', 12), (64, 58, 'navy', 12), (97, 54, 'navy', 12), (63, 30, 'navy', 12), (78, 16, 'navy', 12), (94, 26, 'navy', 12), (81, 68, 'navy', 12), (22, 46, 'navy', 26), (22, 46, 'amarelo', 20), (70, 48, 'navy', 26), (70, 48, 'amarelo', 20)],
                "arestas": [(22, 46, 6, 82, 'cinza', 1), (22, 46, 23, 90, 'cinza', 1), (22, 46, 39, 76, 'cinza', 1), (22, 46, 8, 58, 'cinza', 1), (22, 46, 41, 54, 'cinza', 1), (22, 46, 7, 30, 'cinza', 1), (22, 46, 22, 16, 'cinza', 1), (22, 46, 38, 26, 'cinza', 1), (22, 46, 25, 68, 'cinza', 1), (62, 82, 79, 90, 'cinza', 1), (79, 90, 95, 76, 'cinza', 1), (95, 76, 97, 54, 'cinza', 1), (64, 58, 62, 82, 'cinza', 1), (64, 58, 81, 68, 'cinza', 1), (81, 68, 79, 90, 'cinza', 1), (63, 30, 64, 58, 'cinza', 1), (63, 30, 78, 16, 'cinza', 1), (78, 16, 94, 26, 'cinza', 1), (94, 26, 97, 54, 'cinza', 1), (81, 68, 97, 54, 'cinza', 1), (79, 90, 81, 68, 'azul', 4), (81, 68, 64, 58, 'azul', 4), (64, 58, 70, 48, 'azul', 4), (50, -4, 50, 96, 'cinzaclaro', 1)],
                "rotulos": [(22, 2, "preto", "comparar com todos"),
                            (78, 2, "preto", "percorrer a malha")],
            }),
            ("texto", "O resultado deixa de ser exato, e um *parâmetro de ajuste* controla o "
                      "compromisso: percorrer mais da malha eleva o acerto e o tempo de resposta."),
        ],
    },
    {
        "titulo": "Objetivo do trabalho",
        "blocos": [
            ("texto", "A decisão aparece em qualquer projeto que dependa de busca semântica:"),
            ("frase", "Utilizar o banco de dados já existente\nou adotar um sistema especializado?"),
            ("cartoes", [
                ("Sistema estendido", "PostgreSQL com a extensão pgvector. Banco relacional que recebeu suporte a vetores."),
                ("Sistemas especializados", "Qdrant e Weaviate. Projetados para busca por similaridade."),
            ]),
        ],
    },
    {
        "titulo": "Metodologia: controle das variáveis",
        "blocos": [
            ("texto", "A comparação exige uma única variável livre. As demais foram fixadas:"),
            ("colunas", [
                ["• mesma máquina, mesma sessão de medição",
                 "• mesmos textos: 100 mil e 500 mil trechos",
                 "• mesmo modelo de linguagem"],
                ["• mesmo índice, mesmos parâmetros de construção",
                 "• 1.000 buscas medidas por configuração",
                 "• cada sistema em contêiner, versão fixada"],
            ]),
            ("nota", "A única diferença entre as três medições é o sistema de banco de dados. "
                     "Cada valor está registrado em arquivo no repositório, junto da "
                     "configuração que o produziu."),
        ],
    },
    {
        "titulo": "Grandezas medidas",
        "blocos": [
            ("destaques", [
                ("Acerto", "proporção dos 10 documentos corretos presentes na resposta. Máximo 1,0."),
                ("Tempo", "duração de uma busca, em milissegundos."),
                ("Vazão", "buscas atendidas por segundo."),
            ]),
            ("caixa", "As três grandezas não melhoram em conjunto. Elevar o acerto sempre "
                      "aumenta o tempo e reduz a vazão. Cada sistema descreve uma curva, e a "
                      "escolha de projeto é o **ponto de operação** sobre essa curva."),
        ],
    },
    {
        "titulo": "Resultados: busca sem filtro",
        "blocos": [
            ("texto", "Base de 100 mil trechos, os três sistemas no mesmo ponto de operação:"),
            ("tabela", {
                "cabecalho": ["", "Acerto", "Tempo", "Buscas/s"],
                "linhas": [["pgvector", "0,987", "1,1 ms", "822"],
                           ["Qdrant", "0,998", "2,3 ms", "433"],
                           ["Weaviate", "0,973", "1,3 ms", "777"]],
                "azuis": [],
            }),
            ("texto", "Os três superam *97% de acerto*. A diferença está no custo de atingir "
                      "esse patamar, e o ajuste necessário cresce com o tamanho da base."),
        ],
    },
    {
        "titulo": "Resultados: construção do índice e recursos",
        "blocos": [
            ("texto", "Tempo até o índice estar utilizável, com 500 mil trechos:"),
            ("barras", [("pgvector", 1.0, "21 minutos"),
                        ("Qdrant", 0.125, "2,7 minutos"),
                        ("Weaviate", 0.083, "1,8 minuto")]),
            ("texto", "O pgvector requer de *8 a 12 vezes* o tempo dos demais, e a diferença "
                      "aumenta com a base. O consumo de disco também é o maior: 1.768 MiB "
                      "contra 809 MiB do Qdrant."),
            ("texto", "O Weaviate apresenta o maior consumo de memória: *2,6 GiB* contra "
                      "171 MiB do Qdrant."),
        ],
    },
    {
        "titulo": "Resultados: busca com filtro",
        "blocos": [
            ("texto", "Consulta com filtro é o caso frequente em aplicação real: **restringir a "
                      "busca a um subconjunto dos documentos**. Medida com 1% da base elegível, "
                      "com os três sistemas percorrendo o índice:"),
            ("tabela", {
                "cabecalho": ["", "Acerto com filtro de 1%"],
                "linhas": [["pgvector", "0,0592"],
                           ["Qdrant", "0,9996"],
                           ["Weaviate", "0,5662"]],
                "azuis": [(1, 1)],
            }),
            ("texto", "É o cenário que mais separa os três. O Qdrant preserva o acerto, o "
                      "Weaviate entrega pouco mais da metade, e o pgvector fica limitado pela "
                      "ordem em que aplica o filtro: acrescentar um índice sobre o campo de "
                      "filtro não altera o resultado."),
        ],
    },
    {
        "titulo": "Próximas etapas",
        "blocos": [
            ("colunas", [
                ["• escala de 1 milhão de trechos",
                 "• carga concorrente de escrita e leitura"],
                ["• repetição das medições, com dispersão",
                 "• comparação entre duas arquiteturas de máquina"],
            ]),
        ],
    },
    {
        "titulo": "",
        "blocos": [("central", "Obrigado")],
    },
]


# -----------------------------------------------------------------------------
# Roteiro falado. Deixas curtas, não texto corrido: parágrafo lido em pé soa
# lido. Registro sóbrio, sem coloquialismo, mas em frase falável.
# -----------------------------------------------------------------------------

ROTEIRO: list[dict] = [
    {
        "slide": 1, "titulo": "Capa", "seg": 35,
        "ideia": "Apresentar-se e enunciar a pergunta do trabalho.",
        "falas": [
            "Boa tarde. Eu sou o Rafael, do curso de Ciência da Computação.",
            "Sou bolsista de Iniciação Científica, orientado pelo professor Celson.",
            "Vou apresentar o relatório parcial deste ano.",
            "O trabalho compara três bancos de dados para busca por significado, e mede o que a escolha entre eles custa.",
        ],
        "notas": [],
    },
    {
        "slide": 2, "titulo": "Roteiro", "seg": 20,
        "ideia": "Dar a estrutura em uma frase.",
        "falas": [
            "A estrutura é essa: primeiro o problema e como esses sistemas o resolvem.",
            "Depois o objetivo, a metodologia e os resultados.",
            "E ao final as próximas etapas.",
        ],
        "notas": [],
    },
    {
        "slide": 3, "titulo": "Busca por palavra-chave e busca semântica", "seg": 55,
        "ideia": "Delimitar o problema com um caso concreto.",
        "falas": [
            "Considerem uma consulta no site da universidade por trancar o semestre.",
            "A resolução que trata disso não usa esse termo. Ela usa suspensão de matrícula.",
            "A busca por palavra-chave compara caracteres, então esse documento não aparece.",
            "A busca semântica compara significado, e reconhece o conceito escrito de outra forma.",
            "É a camada que permite a um assistente responder sobre o acervo de uma instituição.",
        ],
        "notas": ["Se houver abertura, pergunte se alguém já não encontrou algo que sabia existir."],
    },
    {
        "slide": 4, "titulo": "Representação vetorial do texto", "seg": 70,
        "ideia": "Texto como coordenada. O diagrama mostra proximidade e distância.",
        "falas": [
            "Para isso funcionar, cada trecho de texto passa por um modelo de linguagem.",
            "O modelo devolve 384 números.",
            "Esses números funcionam como uma coordenada em um espaço de 384 eixos.",
            "No diagrama estão dois grupos: à esquerda, trechos sobre o mesmo assunto; à direita, sobre outro.",
            "Conteúdo semelhante ocupa posições próximas. Conteúdo distinto fica distante.",
            "A busca deixa de comparar palavras e passa a ser um cálculo de distância.",
            "Na base que eu usei são 500 mil trechos. Ponto a ponto, isso envolve 192 milhões de números por consulta.",
        ],
        "notas": ["O diagrama está em duas dimensões por necessidade de desenho. Se alguém "
                  "perguntar, confirme: são 384 eixos, e a ideia de distância é a mesma."],
    },
    {
        "slide": 5, "titulo": "Busca exata e busca aproximada", "seg": 80,
        "ideia": "O diagrama é o centro do slide. Explique os dois lados antes do texto.",
        "falas": [
            "Comparar a consulta com os 500 mil pontos dá o resultado exato.",
            "É o desenho da esquerda: o ponto amarelo é a consulta, e sai uma ligação para cada ponto da base.",
            "O custo disso é incompatível com uma tela que precisa responder em milissegundos.",
            "À direita está a alternativa: os sistemas constroem uma malha de ligações entre os pontos.",
            "A busca entra por um ponto e caminha pela malha, em azul, até a região mais próxima.",
            "Ela visita uma fração da base em vez de varrer tudo.",
            "O resultado deixa de ser exato: o caminho pode parar perto do certo sem chegar nele.",
            "E existe um parâmetro de ajuste: percorrer mais da malha eleva o acerto e o tempo.",
        ],
        "notas": ["Aponte os dois desenhos enquanto fala. Este slide é o que sustenta a leitura "
                  "de todos os resultados adiante."],
    },
    {
        "slide": 6, "titulo": "Objetivo do trabalho", "seg": 40,
        "ideia": "Enquadrar a decisão de projeto que o trabalho responde.",
        "falas": [
            "A decisão aparece em qualquer projeto que dependa de busca semântica.",
            "Utilizar o banco de dados que a instituição já tem, ou adotar um sistema especializado?",
            "De um lado o PostgreSQL com a extensão pgvector, que a literatura chama de sistema estendido.",
            "Do outro o Qdrant e o Weaviate, projetados desde a origem para busca por similaridade.",
            "O objetivo é medir o que essa escolha custa, em condições controladas.",
        ],
        "notas": [],
    },
    {
        "slide": 7, "titulo": "Metodologia: controle das variáveis", "seg": 45,
        "ideia": "Controle de variável e rastreabilidade. Sustenta os resultados.",
        "falas": [
            "Para a comparação ter validade, só uma variável pode ficar livre.",
            "Fixei mesma máquina, mesma sessão de medição e mesmos textos.",
            "Mesmo modelo de linguagem, mesmo tipo de índice e mesmos parâmetros de construção.",
            "Mil buscas medidas em cada configuração.",
            "A única diferença entre as três medições é o banco de dados.",
            "E cada valor está registrado em arquivo no repositório, junto da configuração que o produziu.",
        ],
        "notas": ["Pausa curta depois de mencionar o repositório. Procedimento e rastreabilidade "
                  "é linguagem que essa turma leva a sério."],
    },
    {
        "slide": 8, "titulo": "Grandezas medidas", "seg": 55,
        "ideia": "As três grandezas e o compromisso entre elas.",
        "falas": [
            "São três grandezas medidas.",
            "Acerto: dos dez documentos corretos, quantos vieram na resposta. O máximo é um.",
            "Tempo: a duração de uma busca.",
            "Vazão: quantas buscas o sistema atende por segundo.",
            "As três não melhoram em conjunto.",
            "Elevar o acerto sempre aumenta o tempo e reduz a vazão.",
            "Por isso não existe o mais rápido. Cada sistema descreve uma curva, e a escolha de projeto é o ponto de operação sobre ela.",
        ],
        "notas": ["Se alguém observar que isso é curva de operação, confirme: é a mesma ideia."],
    },
    {
        "slide": 9, "titulo": "Resultados: busca sem filtro", "seg": 45,
        "ideia": "Os três acertam; a diferença está no custo.",
        "falas": [
            "Primeiro resultado, com cem mil trechos.",
            "Os três superam noventa e sete por cento de acerto.",
            "A diferença não está em acertar, e sim no custo de atingir esse patamar.",
            "E o ajuste necessário cresce com o tamanho da base.",
            "Nessa escala o pgvector responde em menos tempo que os outros dois.",
        ],
        "notas": ["Se questionarem a vazão menor do Qdrant: ele atinge acerto maior no mesmo "
                  "ajuste, logo está em outro ponto da curva."],
    },
    {
        "slide": 10, "titulo": "Resultados: construção do índice e recursos", "seg": 55,
        "ideia": "A diferença é grande, e cada sistema perde em uma grandeza diferente.",
        "falas": [
            "Segundo resultado, e é onde a diferença é maior.",
            "Este é o tempo até o índice estar utilizável, com quinhentos mil trechos.",
            "O pgvector leva vinte e um minutos. Os outros dois levam menos de três.",
            "São de oito a doze vezes mais tempo, e a diferença aumenta com a base.",
            "O consumo de disco dele também é o maior, mais que o dobro do Qdrant.",
            "Em contrapartida, o maior consumo de memória é do Weaviate: dois vírgula seis gigabytes contra cento e setenta e um megabytes.",
            "Ele mantém a malha inteira em memória.",
        ],
        "notas": ["Ressalva a declarar se o orientador cobrar: o pgvector construiu o índice com "
                  "a configuração padrão da imagem, que não é dimensionada para essa operação. "
                  "Está registrado no relatório."],
    },
    {
        "slide": 11, "titulo": "Resultados: busca com filtro", "seg": 75,
        "ideia": "O cenário que mais separa os três. A menção ao artefato é rápida e sem slide.",
        "falas": [
            "Terceiro resultado, e é o cenário mais próximo de uso real.",
            "Consulta com filtro: restringir a busca a um subconjunto dos documentos.",
            "Medi com um por cento da base elegível.",
            "O Qdrant preserva o acerto, quase um.",
            "O Weaviate entrega pouco mais da metade.",
            "E o pgvector fica em seis centésimos, limitado pela ordem em que aplica o filtro.",
            "Eu cheguei a criar um índice sobre o campo de filtro supondo que fosse a causa, e o resultado não mudou.",
            "Um detalhe de método que vale registrar em uma frase:",
            "na configuração padrão, dois desses sistemas abandonam o índice quando sobra pouca coisa e resolvem por varredura completa, o que produz acerto igual a um.",
            "Esses números são da condição em que os três foram obrigados a usar o índice.",
        ],
        "notas": ["A menção ao artefato é uma frase, sem se estender. Se houver interesse, o "
                  "detalhe está no relatório e rende conversa depois."],
    },
    {
        "slide": 12, "titulo": "Próximas etapas", "seg": 35,
        "ideia": "O que vem na segunda metade do ano.",
        "falas": [
            "Para a segunda metade do ano ficam quatro frentes.",
            "A escala de um milhão de trechos.",
            "Carga concorrente de escrita e leitura.",
            "Repetir as medições para reportar dispersão.",
            "E comparar duas arquiteturas de máquina diferentes.",
        ],
        "notas": [],
    },
    {
        "slide": 13, "titulo": "Obrigado", "seg": 10,
        "ideia": "Encerrar e abrir para perguntas.",
        "falas": [
            "Obrigado. Fico à disposição para perguntas.",
        ],
        "notas": ["O código e os dados estão em github.com/RNobre1/IC-Vetoriais, caso alguém peça."],
    },
]

PERGUNTAS: list[tuple[str, str]] = [
    ("Qual dos três eu deveria usar?",
     "Depende do recurso escasso no caso. Sob filtro restritivo, o Qdrant foi o único que "
     "sustentou o desempenho. Se o PostgreSQL já está em uso e o filtro é amplo, o pgvector "
     "atende sem introduzir um sistema novo. Se memória é o limite, o Weaviate é o mais "
     "custoso dos três."),
    ("Por que apenas quinhentos mil trechos?",
     "A escala de um milhão está no cronograma para a segunda metade do ano. Nessa escala o "
     "efeito já é observável, e a diferença de tempo de construção cresce com a base, então a "
     "tendência não deve se inverter."),
    ("As medições foram repetidas?",
     "Cada configuração foi medida uma vez, e essa é uma limitação declarada no relatório. O "
     "acerto se reproduziu quando refiz a medição; a latência de cauda não. Repetir as "
     "execuções e reportar a dispersão é trabalho da próxima fase."),
    ("A comparação é justa? Um deles é banco relacional.",
     "É justa no que se propõe medir: os três receberam os mesmos dados, o mesmo tipo de índice "
     "e os mesmos parâmetros de construção. As assimetrias remanescentes estão declaradas no "
     "texto, entre elas a configuração padrão de construção de índice do pgvector."),
]
