#!/usr/bin/env python3
"""Fonte única do conteúdo da apresentação para o PET.

Os três artefatos derivam daqui: o corpo do `slides.tex` (por `gerar_tex.py`),
o `.pptx` (por `gerar_pptx.py`) e o roteiro falado em `.docx` (por
`gerar_roteiro.py`). Texto muda aqui e em nenhum outro lugar.

Público: o PET do IEG, em maioria de engenharia. Dois colegas de computação
além de mim. Então nada de vocabulário de banco de dados sem tradução, e as
comparações vêm de ensaio de bancada, instrumentação e curva de operação, que
é linguagem que essa turma já tem.

Marcação inline aceita pelos três geradores:
  *texto*    destaque em azul e negrito
  **texto**  negrito
  _texto_    itálico
"""

CAPA = {
    "titulo": "Bancos de dados vetoriais:\nqual escolher, e por quê",
    "sub": "Um ensaio comparativo entre PostgreSQL + pgvector, Qdrant e Weaviate",
    "rodape": [
        "Rafael Nobre de Souza   |   Orientador: Prof. Dr. Celson Pantoja Lima",
        "Universidade Federal do Oeste do Pará",
        "Instituto de Engenharia e Geociências",
        "Programa de Educação Tutorial",
    ],
}

SLIDES: list[dict] = [
    {
        "titulo": "Por onde eu vou passar",
        "blocos": [
            ("colunas", [
                ["**1.** Que problema esses bancos resolvem",
                 "**2.** Como um computador compara sentido",
                 "**3.** Por que ninguém compara tudo",
                 "**4.** A pergunta que eu quis responder"],
                ["**5.** A bancada",
                 "**6.** O que os números deram",
                 "**7.** O erro que quase entrou no relatório",
                 "**8.** O que eu levo disso"],
            ]),
        ],
    },
    {
        "titulo": "Quando buscar por palavra não resolve",
        "blocos": [
            ("texto", "Você procura no site da universidade como **trancar o semestre**. "
                      "A resolução que responde isso usa outro termo: **suspensão de matrícula**."),
            ("texto", "A busca comum compara caractere com caractere. As letras são outras, "
                      "então o documento certo simplesmente não aparece na lista."),
            ("cartoes", [
                ("Busca por palavra", "Compara os caracteres. Muda o termo, não acha."),
                ("Busca por sentido", "Compara o significado. Acha mesmo com outras palavras."),
                ("Onde isso aparece", "Em qualquer assistente que precisa responder sobre os documentos de uma instituição."),
            ]),
        ],
    },
    {
        "titulo": "Como um computador compara sentido",
        "blocos": [
            ("texto", "Um modelo de linguagem lê o trecho de texto e devolve *384 números*. "
                      "Pense nisso como um endereço num espaço de 384 eixos."),
            ("texto", "Trechos que falam da mesma coisa ficam próximos nesse espaço. Assuntos "
                      "diferentes ficam distantes. Buscar passou a ser **medir distância**."),
            ("nota", "Na minha base são 500 mil trechos. Comparar a pergunta com todos eles, um "
                     "por um, dá 192 milhões de números por busca."),
        ],
    },
    {
        "titulo": "Por que ninguém compara tudo",
        "blocos": [
            ("texto", "Medir a distância até os 500 mil pontos acerta sempre. E é lento demais "
                      "para uma tela que precisa responder na hora."),
            ("texto", "Então o banco monta um *índice*: uma malha de ligações entre os pontos. "
                      "A busca percorre a malha em vez de varrer a base."),
            ("cartoes", [
                ("O acerto deixa de ser garantido", "A busca passa perto do certo. Às vezes ela erra."),
                ("Existe um ajuste", "Percorrer mais da malha sobe o acerto e sobe o tempo. Percorrer menos faz o inverso."),
            ]),
        ],
    },
    {
        "titulo": "A pergunta que eu quis responder",
        "blocos": [
            ("texto", "Quem vai montar um sistema desses tropeça sempre na mesma dúvida:"),
            ("frase", "Dá para usar o banco que a gente já tem,\nou tem que instalar um banco feito só para isso?"),
            ("cartoes", [
                ("O que a gente já tem", "PostgreSQL com a extensão pgvector. Banco comum que ganhou suporte a vetores."),
                ("Os feitos para isso", "Qdrant e Weaviate. Nasceram para busca por sentido."),
            ]),
        ],
    },
    {
        "titulo": "A bancada",
        "blocos": [
            ("texto", "Para a comparação valer, só uma coisa pode variar. Travei todo o resto:"),
            ("colunas", [
                ["• mesma máquina, na mesma sessão",
                 "• mesmos textos: 100 mil e 500 mil trechos",
                 "• mesmo modelo de linguagem"],
                ["• mesmo tipo de índice, mesmos parâmetros",
                 "• 1.000 buscas medidas em cada configuração",
                 "• cada banco em contêiner, versão travada"],
            ]),
            ("nota", "Sobrou o banco como única diferença entre as três medições. Cada número "
                     "está num arquivo no repositório, junto da configuração que o produziu."),
        ],
    },
    {
        "titulo": "O que eu medi",
        "blocos": [
            ("destaques", [
                ("Acerto", "dos 10 documentos certos, quantos vieram na resposta. O máximo é 1,0."),
                ("Tempo", "quanto demora uma busca, em milissegundos."),
                ("Vazão", "quantas buscas o banco atende por segundo."),
            ]),
            ("caixa", "As três não andam juntas. Apertar o ajuste para acertar mais sempre custa "
                      "tempo e vazão. Então a pergunta **qual é o mais rápido** não tem resposta: "
                      "cada banco tem uma curva, e você escolhe em que ponto dela vai operar."),
        ],
    },
    {
        "titulo": "Resultado 1: buscando",
        "blocos": [
            ("texto", "Base de 100 mil trechos, os três no mesmo ponto de ajuste:"),
            ("tabela", {
                "cabecalho": ["", "Acerto", "Tempo", "Buscas/s"],
                "linhas": [["pgvector", "0,987", "1,1 ms", "822"],
                           ["Qdrant", "0,998", "2,3 ms", "433"],
                           ["Weaviate", "0,973", "1,3 ms", "777"]],
                "azuis": [],
            }),
            ("texto", "Os três passam de *97% de acerto*. Nenhum é ruim de buscar. A diferença "
                      "está no que cada um cobra para chegar nesse patamar, e o ajuste que eles "
                      "pedem sobe conforme a base cresce."),
        ],
    },
    {
        "titulo": "Resultado 2: montando o índice",
        "blocos": [
            ("texto", "Tempo até o índice ficar pronto, com 500 mil trechos:"),
            ("barras", [("pgvector", 1.0, "21 minutos"),
                        ("Qdrant", 0.125, "2,7 minutos"),
                        ("Weaviate", 0.083, "1,8 minuto")]),
            ("texto", "O pgvector leva de *8 a 12 vezes* o tempo dos outros dois, e a distância "
                      "aumenta com a base. Em disco ele também gasta mais: 1.768 MiB contra 809 "
                      "do Qdrant."),
            ("texto", "Do outro lado, quem come memória é o Weaviate: *2,6 GiB* contra 171 MiB "
                      "do Qdrant."),
        ],
    },
    {
        "titulo": "Resultado 3: buscando com filtro",
        "blocos": [
            ("texto", "Busca de verdade quase nunca é solta. É **procure só nos documentos do "
                      "meu setor**. Testei assim, e o número veio bonito:"),
            ("tabela", {
                "cabecalho": ["", "Acerto com filtro de 1%"],
                "linhas": [["pgvector", "0,0595"],
                           ["Qdrant", "1,0000"],
                           ["Weaviate", "1,0000"]],
                "azuis": [(1, 1), (2, 1)],
            }),
            ("texto", "Dava para escrever que os bancos especializados são perfeitos com filtro "
                      "e que o pgvector não serve. *Foi o que eu quase escrevi.*"),
        ],
    },
    {
        "titulo": "O instrumento não respondia ao ajuste",
        "blocos": [
            ("texto", "Se eu mexo no ajuste, o acerto tem que mudar. Fui olhar os cinco valores "
                      "que eu tinha medido:"),
            ("tabela", {
                "cabecalho": ["Ajuste", "16", "32", "64", "128", "256"],
                "linhas": [["Weaviate", "1,0000", "1,0000", "1,0000", "1,0000", "1,0000"]],
                "azuis": [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
            }),
            ("texto", "Cinco ajustes diferentes e o mesmo 1,0000 nos cinco. Fui na documentação "
                      "dos dois bancos e estava escrito lá: quando o filtro deixa pouca coisa "
                      "elegível, eles *abandonam o índice* e conferem um por um."),
            ("texto", "Aquele acerto perfeito media a varredura completa. Não media a busca "
                      "aproximada, que era o que eu pensava estar comparando."),
        ],
    },
    {
        "titulo": "A contraprova",
        "blocos": [
            ("texto", "Desliguei esse desvio e rodei tudo outra vez, com os três obrigados a usar "
                      "o índice:"),
            ("tabela", {
                "cabecalho": ["", "Antes", "Índice obrigado a trabalhar"],
                "linhas": [["pgvector", "0,0595", "0,0592"],
                           ["Qdrant", "1,0000", "0,9996"],
                           ["Weaviate", "1,0000", "0,5662"]],
                "azuis": [(2, 2)],
            }),
            ("texto", "O Qdrant se manteve, então a vantagem dele existe. O Weaviate caiu para "
                      "pouco mais da metade. E o pgvector nem se mexeu: eu tinha colocado um "
                      "índice no campo do filtro achando que era isso, e não mudou nada."),
        ],
    },
    {
        "titulo": "O que eu levo disso",
        "blocos": [
            ("caixa_navy", ["Número redondo pede desconfiança antes de comemoração.",
                            "Se a medida não muda quando você mexe no ajuste, o que está sendo "
                            "medido não é o que você pensa que é."]),
            ("texto", "Aqui custou reescrever parte do relatório. Se tivesse passado, custaria "
                      "uma correção depois da banca."),
        ],
    },
    {
        "titulo": "Onde eu estou, e o que falta",
        "blocos": [
            ("colunas_titulo", [
                ("Pronto", ["• ambiente reproduzível dos 3 bancos",
                            "• 248 testes automatizados",
                            "• 2 cenários em 2 escalas, dados no repositório",
                            "• relatório parcial fechado"]),
                ("Falta", ["• escala de 1 milhão de trechos",
                           "• escrita e leitura ao mesmo tempo",
                           "• repetir medições e reportar a variação",
                           "• comparar duas arquiteturas de máquina"]),
            ]),
            ("frase", "Obrigado. Perguntas?"),
            ("nota_centro", "Código e dados: github.com/RNobre1/IC-Vetoriais"),
        ],
    },
]

# -----------------------------------------------------------------------------
# Roteiro falado. Formato de deixa, não de texto corrido: cada linha é uma
# frase curta para falar. Ler parágrafo em pé soa lido; deixa curta soa fala.
# -----------------------------------------------------------------------------

ROTEIRO: list[dict] = [
    {
        "slide": 1, "titulo": "Capa", "seg": 40,
        "ideia": "Se apresentar e prometer a parte interessante.",
        "falas": [
            "Boa tarde. Eu sou o Rafael, do curso de Ciência da Computação.",
            "Sou bolsista de Iniciação Científica com o professor Celson.",
            "Vou contar o que eu medi neste ano sobre bancos de dados vetoriais.",
            "E já adianto onde fica a parte interessante: o resultado que eu ia colocar no relatório estava errado.",
            "Quem entregou o erro foi um número que ficou bonito demais.",
        ],
        "notas": ["Não corra aqui. Essa promessa é o que segura a turma até o slide 11."],
    },
    {
        "slide": 2, "titulo": "Por onde eu vou passar", "seg": 20,
        "ideia": "Dar o mapa em uma frase.",
        "falas": [
            "O caminho é esse: primeiro por que esse tipo de banco existe.",
            "Depois como eu comparei três deles.",
            "E no fim o erro e o que ficou de lição.",
        ],
        "notas": [],
    },
    {
        "slide": 3, "titulo": "Quando buscar por palavra não resolve", "seg": 55,
        "ideia": "Mostrar o problema com um caso que todo mundo já viveu.",
        "falas": [
            "Imagina você procurando no site da universidade como trancar o semestre.",
            "A resolução que responde isso não fala trancar. Ela fala suspensão de matrícula.",
            "A busca comum compara letra com letra. As letras são outras, então ela não acha.",
            "Buscar por sentido resolve isso: compara o significado em vez dos caracteres.",
            "É a peça que faz um assistente conseguir responder sobre os documentos da instituição.",
        ],
        "notas": ["Se der abertura, pergunte se alguém já não achou algo que sabia que existia. "
                  "Costuma render aceno de cabeça."],
    },
    {
        "slide": 4, "titulo": "Como um computador compara sentido", "seg": 55,
        "ideia": "Traduzir texto em coordenada. Aqui a turma de engenharia já tem o vocabulário.",
        "falas": [
            "Para isso funcionar, cada trecho de texto passa por um modelo de linguagem.",
            "O modelo devolve 384 números.",
            "Vocês podem pensar nesses números como um endereço num espaço de 384 eixos.",
            "Trechos que falam da mesma coisa caem perto. Assuntos diferentes caem longe.",
            "Então buscar deixou de ser comparar palavras e passou a ser medir distância.",
            "Na minha base são 500 mil trechos. Fazer isso um por um dá 192 milhões de números por busca.",
        ],
        "notas": ["Vetor e distância é terreno conhecido dessa turma. Use isso a seu favor e "
                  "não peça desculpa pela matemática."],
    },
    {
        "slide": 5, "titulo": "Por que ninguém compara tudo", "seg": 55,
        "ideia": "Introduzir o índice aproximado e, principalmente, o ajuste.",
        "falas": [
            "Medir a distância até os 500 mil pontos acerta sempre.",
            "E é lento demais para uma tela que tem que responder na hora.",
            "Então o banco monta um índice: uma malha de ligações entre os pontos.",
            "A busca percorre a malha em vez de varrer a base inteira.",
            "Fica muito mais rápido, mas o acerto deixa de ser garantido.",
            "E existe um ajuste: percorrer mais da malha sobe o acerto e sobe o tempo.",
            "Guardem esse ajuste. Ele é o personagem principal daqui a alguns slides.",
        ],
        "notas": ["Plantar o ajuste aqui é o que faz o slide 11 funcionar sem explicação nova."],
    },
    {
        "slide": 6, "titulo": "A pergunta que eu quis responder", "seg": 40,
        "ideia": "Enquadrar a decisão de projeto.",
        "falas": [
            "Quem monta um sistema desses tropeça sempre na mesma dúvida.",
            "Dá para usar o banco que a gente já tem, ou tem que instalar um banco feito só para isso?",
            "De um lado o PostgreSQL, que praticamente todo sistema já usa, com uma extensão chamada pgvector.",
            "Do outro o Qdrant e o Weaviate, que nasceram para busca por sentido.",
            "O que eu quis medir foi quanto essa escolha custa de fato.",
        ],
        "notas": [],
    },
    {
        "slide": 7, "titulo": "A bancada", "seg": 45,
        "ideia": "Mostrar controle de variável. É o slide que dá credibilidade ao resto.",
        "falas": [
            "Para uma comparação valer, só uma coisa pode variar.",
            "Então eu travei todo o resto: mesma máquina, mesma sessão, mesmos textos.",
            "Mesmo modelo de linguagem, mesmo tipo de índice, mesmos parâmetros de construção.",
            "Mil buscas medidas em cada configuração.",
            "Sobrou o banco como única diferença. Então a diferença que aparecer é do banco.",
            "E cada número está num arquivo no repositório, junto da configuração que gerou ele.",
        ],
        "notas": ["Vale uma pausa depois de falar do repositório. Essa turma valoriza "
                  "procedimento e rastreabilidade."],
    },
    {
        "slide": 8, "titulo": "O que eu medi", "seg": 55,
        "ideia": "As três grandezas e o compromisso entre elas.",
        "falas": [
            "Eu medi três coisas.",
            "Acerto: dos dez documentos certos, quantos vieram na resposta. O máximo é um.",
            "Tempo: quanto demora uma busca.",
            "Vazão: quantas buscas o banco atende por segundo.",
            "As três não andam juntas.",
            "Apertar o ajuste para acertar mais sempre custa tempo e vazão.",
            "Por isso a pergunta qual é o mais rápido não tem resposta. Cada banco tem uma curva, e você escolhe onde operar nela.",
        ],
        "notas": ["Se alguém de engenharia comentar que isso é curva de operação, concorde: é "
                  "exatamente a mesma ideia."],
    },
    {
        "slide": 9, "titulo": "Resultado 1: buscando", "seg": 40,
        "ideia": "Os três acertam. A diferença é o preço.",
        "falas": [
            "Primeiro resultado, com cem mil trechos.",
            "Os três passam de noventa e sete por cento de acerto. Nenhum é ruim de buscar.",
            "A diferença não está em acertar, está no que cada um cobra para acertar.",
            "E o ajuste que eles pedem sobe conforme a base cresce.",
            "Nessa escala o pgvector até responde mais rápido que os outros dois.",
        ],
        "notas": ["Se perguntarem por que o Qdrant tem vazão menor: ele acerta mais no mesmo "
                  "ajuste, então está em outro ponto da curva."],
    },
    {
        "slide": 10, "titulo": "Resultado 2: montando o índice", "seg": 50,
        "ideia": "Aqui a diferença é grande, e cada banco perde numa grandeza diferente.",
        "falas": [
            "Segundo resultado, e aqui a diferença é grande.",
            "Esse é o tempo até o índice ficar pronto, com quinhentos mil trechos.",
            "O pgvector leva vinte e um minutos. Os outros dois levam menos de três.",
            "É de oito a doze vezes mais tempo, e a distância aumenta com a base.",
            "Em disco ele também gasta mais que o dobro do Qdrant.",
            "Só que quem come memória é o Weaviate: dois vírgula seis gigabytes contra cento e setenta megabytes.",
            "Ele mantém a malha inteira na memória.",
        ],
        "notas": ["Ressalva honesta, se o professor cobrar: o pgvector rodou com a configuração "
                  "padrão da imagem, que não é dimensionada para construir esse índice. Está "
                  "declarado no relatório."],
    },
    {
        "slide": 11, "titulo": "Resultado 3: buscando com filtro", "seg": 60,
        "ideia": "Apresentar o resultado bonito e admitir que ele ia para o relatório.",
        "falas": [
            "Terceiro resultado, e é aqui que a história vira.",
            "Busca de verdade quase nunca é solta.",
            "É procure só nos documentos do meu setor, só nos contratos vigentes.",
            "Testei assim, deixando só um por cento da base elegível.",
            "O Qdrant e o Weaviate deram acerto de exatamente um. Perfeito.",
            "O pgvector deu seis por cento.",
            "Dava para escrever que os especializados são perfeitos com filtro e o pgvector não serve.",
            "Foi o que eu quase escrevi.",
        ],
        "notas": ["Fale essa última linha e pare. O silêncio aqui vale mais que qualquer animação."],
    },
    {
        "slide": 12, "titulo": "O instrumento não respondia ao ajuste", "seg": 50,
        "ideia": "A pista. Enquadrar como falha de instrumentação, que essa turma reconhece.",
        "falas": [
            "O que pegou foi o ajuste.",
            "Se eu mexo no ajuste, o acerto tem que mudar. Se não muda, tem algo errado na medição.",
            "Fui olhar os cinco valores: um, um, um, um e um.",
            "Cinco ajustes diferentes e o mesmo número nos cinco.",
            "Fui na documentação dos dois bancos e estava escrito lá.",
            "Quando o filtro deixa pouca coisa elegível, eles abandonam o índice e conferem um por um.",
            "Ou seja: aquele acerto perfeito media a varredura completa, não a busca aproximada.",
        ],
        "notas": ["Aponte para a linha de uns na tela. É o momento mais visual da apresentação."],
    },
    {
        "slide": 13, "titulo": "A contraprova", "seg": 50,
        "ideia": "Provar a hipótese, e mostrar que cada banco falha por motivo diferente.",
        "falas": [
            "Para confirmar, eu desliguei esse desvio e rodei tudo outra vez.",
            "Os três obrigados a usar o índice.",
            "O Qdrant se manteve. A vantagem dele existe.",
            "O Weaviate caiu de um para cinquenta e seis por cento. Pouco mais da metade.",
            "E o pgvector nem se mexeu.",
            "Eu tinha colocado um índice no campo do filtro achando que o problema era esse, e não mudou nada.",
            "O problema dele é a ordem das operações, não a falta de índice.",
        ],
        "notas": [],
    },
    {
        "slide": 14, "titulo": "O que eu levo disso", "seg": 50,
        "ideia": "A lição, que não é sobre banco de dados.",
        "falas": [
            "A lição que eu levo daqui não é sobre banco de dados. É sobre medir qualquer coisa.",
            "Número redondo pede desconfiança antes de comemoração.",
            "Se a medida não muda quando você mexe no ajuste, o que está sendo medido não é o que você pensa.",
            "No meu caso isso custou reescrever parte do relatório.",
            "Se tivesse passado, custaria uma correção depois da banca.",
        ],
        "notas": ["Essa é a frase que a turma leva para casa. Fale devagar e olhe para a plateia, "
                  "não para o slide."],
    },
    {
        "slide": 15, "titulo": "Onde eu estou, e o que falta", "seg": 45,
        "ideia": "Fechar com estado do trabalho e abrir para perguntas.",
        "falas": [
            "Fechando. Está pronto o ambiente reproduzível dos três bancos.",
            "Duzentos e quarenta e oito testes automatizados.",
            "Dois cenários em duas escalas, com os dados no repositório.",
            "E o relatório parcial fechado.",
            "Falta a escala de um milhão, escrita e leitura ao mesmo tempo, repetir as medições para reportar variação, e comparar duas arquiteturas de máquina.",
            "Obrigado. O código e os dados estão nesse endereço, e eu fico à disposição.",
        ],
        "notas": [],
    },
]

PERGUNTAS: list[tuple[str, str]] = [
    ("Então qual eu devo usar?",
     "Depende do que aperta no seu caso. Se o filtro é restritivo, o Qdrant foi o único que "
     "sustentou. Se você já tem PostgreSQL e o filtro é largo, o pgvector resolve e você não "
     "instala mais nada. Se memória é o recurso escasso, o Weaviate é o pior dos três."),
    ("Por que só quinhentos mil, e não milhões?",
     "Um milhão está no cronograma para a segunda metade do ano. Nessa escala o efeito já "
     "aparece, e a diferença de tempo de construção cresce com a base, então a tendência não "
     "deve mudar."),
    ("Você mediu uma vez só?",
     "Uma vez por configuração, e isso é uma limitação que está declarada no relatório. O acerto "
     "se repetiu quando eu refiz a medição. O tempo de cauda não se repetiu. Repetir as "
     "execuções e reportar a variação é trabalho da próxima fase."),
    ("Isso é comparação justa? Um deles é banco relacional.",
     "É justa no que ela promete medir: os três receberam os mesmos dados, o mesmo tipo de índice "
     "e os mesmos parâmetros de construção. Onde não é simétrica, está dito no texto. O pgvector "
     "construiu o índice com a configuração padrão da imagem, e isso é uma ressalva declarada."),
]
