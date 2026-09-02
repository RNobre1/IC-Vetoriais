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
                 "**5.** O resultado anômalo e a contraprova",
                 "**6.** Considerações e próximas etapas"],
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
            ("cartoes", [
                ("Consequência", "O resultado deixa de ser exato. A busca pode retornar vizinhos incorretos."),
                ("Parâmetro de ajuste", "Percorrer mais da malha eleva o acerto e o tempo de resposta. Percorrer menos produz o inverso."),
            ]),
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
                      "busca a um subconjunto dos documentos**. Medida com 1% da base elegível:"),
            ("tabela", {
                "cabecalho": ["", "Acerto com filtro de 1%"],
                "linhas": [["pgvector", "0,0595"],
                           ["Qdrant", "1,0000"],
                           ["Weaviate", "1,0000"]],
                "azuis": [(1, 1), (2, 1)],
            }),
            ("texto", "A leitura imediata seria a superioridade dos sistemas especializados sob "
                      "filtro restritivo. *Essa leitura não se sustentou.*"),
        ],
    },
    {
        "titulo": "Diagnóstico do resultado anômalo",
        "blocos": [
            ("texto", "Alterar o parâmetro de ajuste deve alterar o acerto. Os cinco valores "
                      "medidos:"),
            ("tabela", {
                "cabecalho": ["Ajuste", "16", "32", "64", "128", "256"],
                "linhas": [["Weaviate", "1,0000", "1,0000", "1,0000", "1,0000", "1,0000"]],
                "azuis": [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
            }),
            ("texto", "Cinco ajustes distintos e o mesmo valor nos cinco. A documentação dos "
                      "dois sistemas descreve o mecanismo: com poucos elementos elegíveis, o "
                      "executor *abandona o índice* e resolve a consulta por varredura completa."),
            ("texto", "O valor de 1,0000 media a varredura exata, e não a qualidade da busca "
                      "aproximada sob filtro."),
        ],
    },
    {
        "titulo": "Contraprova",
        "blocos": [
            ("texto", "Com o mecanismo desativado e os três sistemas obrigados a percorrer o "
                      "índice:"),
            ("tabela", {
                "cabecalho": ["", "Antes", "Índice obrigado a trabalhar"],
                "linhas": [["pgvector", "0,0595", "0,0592"],
                           ["Qdrant", "1,0000", "0,9996"],
                           ["Weaviate", "1,0000", "0,5662"]],
                "azuis": [(2, 2)],
            }),
            ("texto", "O Qdrant mantém o desempenho, o que confirma a vantagem. O Weaviate cai "
                      "para pouco mais da metade. O pgvector não se altera: um índice sobre o "
                      "campo de filtro não modificou o resultado, o que localiza a limitação na "
                      "ordem das operações."),
        ],
    },
    {
        "titulo": "Consideração metodológica",
        "blocos": [
            ("caixa_navy", ["Resultado exato pede verificação antes de conclusão.",
                            "Se a medida não responde ao parâmetro que deveria alterá-la, a "
                            "grandeza sob medição não é a esperada."]),
            ("texto", "A verificação custou a reescrita de parte do relatório. Sem ela, "
                      "custaria uma correção posterior à avaliação."),
        ],
    },
    {
        "titulo": "Situação atual e próximas etapas",
        "blocos": [
            ("colunas_titulo", [
                ("Concluído", ["• ambiente reproduzível dos 3 sistemas",
                               "• 248 testes automatizados",
                               "• 2 cenários em 2 escalas, dados no repositório",
                               "• relatório parcial fechado"]),
                ("Previsto", ["• escala de 1 milhão de trechos",
                              "• carga concorrente de escrita e leitura",
                              "• repetição das medições, com dispersão",
                              "• comparação entre duas arquiteturas de máquina"]),
            ]),
            ("frase", "Obrigado. Perguntas?"),
            ("nota_centro", "Código e dados: github.com/RNobre1/IC-Vetoriais"),
        ],
    },
]

# -----------------------------------------------------------------------------
# Roteiro falado. Deixas curtas, não texto corrido: parágrafo lido em pé soa
# lido. Registro sóbrio, sem coloquialismo, mas em frase falável.
# -----------------------------------------------------------------------------

ROTEIRO: list[dict] = [
    {
        "slide": 1, "titulo": "Capa", "seg": 40,
        "ideia": "Apresentar-se e enunciar o achado principal.",
        "falas": [
            "Boa tarde. Eu sou o Rafael, do curso de Ciência da Computação.",
            "Sou bolsista de Iniciação Científica, orientado pelo professor Celson.",
            "Vou apresentar o relatório parcial deste ano, que compara três bancos de dados vetoriais.",
            "Adianto o achado principal: uma das conclusões que eu tinha pronta estava errada.",
            "O que revelou o erro foi um resultado exato demais para ser verdadeiro.",
        ],
        "notas": ["Não corra na capa. Esse enunciado é o que sustenta a atenção até o slide 11."],
    },
    {
        "slide": 2, "titulo": "Roteiro", "seg": 20,
        "ideia": "Dar a estrutura em uma frase.",
        "falas": [
            "A estrutura é essa: primeiro o problema e como esses sistemas o resolvem.",
            "Depois o objetivo, a metodologia e os resultados.",
            "E ao final o resultado anômalo, a contraprova e o que fica de consideração.",
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
        "notas": ["Se houver abertura, pergunte se alguém já não encontrou algo que sabia existir. "
                  "Ancora o problema sem custo de tempo."],
    },
    {
        "slide": 4, "titulo": "Representação vetorial do texto", "seg": 55,
        "ideia": "Texto como coordenada. Vocabulário que a turma de engenharia já domina.",
        "falas": [
            "Para isso funcionar, cada trecho de texto passa por um modelo de linguagem.",
            "O modelo devolve 384 números.",
            "Esses números funcionam como uma coordenada em um espaço de 384 eixos.",
            "Trechos de conteúdo semelhante ficam em posições próximas. Conteúdos distintos ficam distantes.",
            "A busca deixa de comparar palavras e passa a ser um cálculo de distância.",
            "Na base que eu usei são 500 mil trechos. Fazer isso ponto a ponto envolve 192 milhões de números por consulta.",
        ],
        "notas": ["Vetor e distância é conteúdo que essa turma tem. Não peça desculpa pela "
                  "matemática nem simplifique além do necessário."],
    },
    {
        "slide": 5, "titulo": "Busca exata e busca aproximada", "seg": 55,
        "ideia": "Introduzir o índice aproximado e o parâmetro de ajuste.",
        "falas": [
            "Comparar a consulta com os 500 mil pontos dá o resultado exato.",
            "E tem custo incompatível com uma tela que precisa responder em milissegundos.",
            "Os sistemas constroem então um índice: uma malha de ligações entre os pontos.",
            "A busca percorre a malha em vez de varrer a base inteira.",
            "O ganho de tempo é grande, e o resultado deixa de ser exato.",
            "Existe um parâmetro de ajuste: percorrer mais da malha eleva o acerto e o tempo.",
            "Guardem esse parâmetro. Ele é o centro do diagnóstico que vem alguns slides adiante.",
        ],
        "notas": ["Plantar o parâmetro aqui é o que permite o slide 11 dispensar explicação nova."],
    },
    {
        "slide": 6, "titulo": "Objetivo do trabalho", "seg": 40,
        "ideia": "Enquadrar a decisão de projeto que o trabalho responde.",
        "falas": [
            "A decisão aparece em qualquer projeto que dependa de busca semântica.",
            "Utilizar o banco de dados que a instituição já tem, ou adotar um sistema especializado?",
            "De um lado o PostgreSQL com a extensão pgvector, que a literatura chama de sistema estendido.",
            "Do outro o Qdrant e o Weaviate, projetados desde a origem para busca por similaridade.",
            "O objetivo do trabalho é medir o que essa escolha custa, em condições controladas.",
        ],
        "notas": [],
    },
    {
        "slide": 7, "titulo": "Metodologia: controle das variáveis", "seg": 45,
        "ideia": "Controle de variável e rastreabilidade. É o slide que sustenta os resultados.",
        "falas": [
            "Para a comparação ter validade, só uma variável pode ficar livre.",
            "Fixei mesma máquina, mesma sessão de medição e mesmos textos.",
            "Mesmo modelo de linguagem, mesmo tipo de índice e mesmos parâmetros de construção.",
            "Mil buscas medidas em cada configuração.",
            "A única diferença entre as três medições é o banco de dados.",
            "E cada valor está registrado em arquivo no repositório, junto da configuração que o produziu.",
        ],
        "notas": ["Vale uma pausa depois de mencionar o repositório. Procedimento e "
                  "rastreabilidade é linguagem que essa turma leva a sério."],
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
        "slide": 9, "titulo": "Resultados: busca sem filtro", "seg": 40,
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
        "slide": 10, "titulo": "Resultados: construção do índice e recursos", "seg": 50,
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
        "slide": 11, "titulo": "Resultados: busca com filtro", "seg": 60,
        "ideia": "Apresentar o resultado anômalo e a conclusão que ele sugeria.",
        "falas": [
            "Terceiro resultado, e é o cenário mais próximo de uso real.",
            "Consulta com filtro: restringir a busca a um subconjunto dos documentos.",
            "Medi com um por cento da base elegível.",
            "O Qdrant e o Weaviate deram acerto de exatamente um.",
            "O pgvector deu seis por cento.",
            "A leitura imediata seria a superioridade dos especializados sob filtro restritivo.",
            "Essa leitura não se sustentou.",
        ],
        "notas": ["Diga a última linha e faça uma pausa. O silêncio aqui vale mais que "
                  "qualquer recurso de animação."],
    },
    {
        "slide": 12, "titulo": "Diagnóstico do resultado anômalo", "seg": 50,
        "ideia": "A pista, enquadrada como verificação de instrumentação.",
        "falas": [
            "O que chamou atenção foi o parâmetro de ajuste.",
            "Alterar o ajuste deve alterar o acerto. Se não altera, a medição não está medindo o que se pensa.",
            "Fui aos cinco valores medidos: um, um, um, um e um.",
            "Cinco ajustes distintos e o mesmo valor nos cinco.",
            "A documentação dos dois sistemas descreve o mecanismo.",
            "Com poucos elementos elegíveis, o executor abandona o índice e resolve por varredura completa.",
            "Ou seja: aquele valor exato media a varredura, e não a qualidade da busca aproximada.",
        ],
        "notas": ["Aponte para a linha de valores iguais na tela. É o momento mais visual da "
                  "apresentação."],
    },
    {
        "slide": 13, "titulo": "Contraprova", "seg": 50,
        "ideia": "Confirmar a hipótese e separar as três limitações.",
        "falas": [
            "Para confirmar, desativei esse mecanismo e repeti todas as medições.",
            "Os três obrigados a percorrer o índice.",
            "O Qdrant manteve o desempenho, o que confirma que a vantagem dele existe.",
            "O Weaviate caiu de um para cinquenta e seis por cento.",
            "E o pgvector não se alterou.",
            "Eu havia criado um índice sobre o campo de filtro supondo que fosse essa a causa, e o resultado não mudou.",
            "A limitação dele está na ordem das operações, não na ausência de índice.",
        ],
        "notas": [],
    },
    {
        "slide": 14, "titulo": "Consideração metodológica", "seg": 50,
        "ideia": "A lição, que é de método e não de banco de dados.",
        "falas": [
            "A consideração que eu tiro daqui não é sobre banco de dados. É sobre medição.",
            "Resultado exato pede verificação antes de conclusão.",
            "Se a medida não responde ao parâmetro que deveria alterá-la, a grandeza sob medição não é a esperada.",
            "No meu caso, a verificação custou reescrever parte do relatório.",
            "Sem ela, custaria uma correção posterior à avaliação.",
        ],
        "notas": ["Essa é a parte que a plateia leva. Fale devagar e olhe para a plateia, não "
                  "para o slide."],
    },
    {
        "slide": 15, "titulo": "Situação atual e próximas etapas", "seg": 45,
        "ideia": "Estado do trabalho e abertura para perguntas.",
        "falas": [
            "Para encerrar. Está concluído o ambiente reproduzível dos três sistemas.",
            "Duzentos e quarenta e oito testes automatizados.",
            "Dois cenários em duas escalas, com os dados no repositório.",
            "E o relatório parcial fechado.",
            "Está previsto a escala de um milhão, carga concorrente de escrita e leitura, repetição das medições com dispersão, e a comparação entre duas arquiteturas de máquina.",
            "Obrigado. O código e os dados estão nesse endereço, e eu fico à disposição.",
        ],
        "notas": [],
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
