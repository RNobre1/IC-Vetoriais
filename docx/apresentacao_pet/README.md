# Apresentação do relatório parcial — PET/IEG

Duas saídas: os slides (`slides.pdf`, 15 slides em 16:9) e o roteiro falado
(`Roteiro_Apresentacao_PET.docx`). Janela de 10 a 15 minutos; o roteiro fecha
em 11:50, o que deixa margem para pergunta no meio.

## Comandos

```bash
make slides    # compila o PDF e imprime páginas e avisos de caixa
make roteiro   # gera o .docx e confere a soma dos tempos
make tudo
make clean
```

## Quem é fonte de quê

| Arquivo | Papel | Versionado |
|---|---|---|
| `slides.tex` | fonte dos slides | sim |
| `gerar_roteiro.py` | fonte do texto falado e gerador do `.docx` | sim |
| `logos/` | logos do PET e da UFOPA, extraídas da apresentação anterior do grupo | sim |
| `slides.pdf` | entregável, sai de `make slides` | não |
| `Roteiro_Apresentacao_PET.docx` | entregável, sai de `make roteiro` | não |

## Decisões de forma

**Segue a apresentação anterior do grupo** na diagramação: 16:9 em 1440×810 pt,
fundo branco, título em negrito no alto à esquerda, azul `#2C71AD` como cor de
destaque, navy `#152039`, número do slide no canto inferior direito. A paleta
foi amostrada dos pixels do arquivo anterior, não escolhida por semelhança.

**O que mudou em relação ao modelo:** a logo do PET aparece em todos os slides,
e não só na capa; os números importantes viraram manchete em vez de linha de
texto corrido; o corpo é alinhado à esquerda e não justificado, porque em fonte
grande a justificação parte palavra ao meio e atravanca quem lê de longe; e há
um slide de fecho com a lição metodológica, que o modelo não tinha.

**Não é uma apresentação acadêmica.** Nenhuma citação, nenhum termo técnico sem
tradução antes, uma ideia por slide. O jargão do relatório (`recall`, `HNSW`,
`ef_search`, seletividade) aparece como "acerto", "rede de atalhos" e "botão de
ajuste". A narrativa é a do erro que quase foi publicado, não a da lista de
métricas.

**Sem `beamer` e sem `tikz`.** Nenhum dos dois está instalado no TinyTeX desta
máquina, e instalar pacote é decisão do piloto, não do build. O deck sai com
`article`, `geometry`, `xcolor` e `graphicx`, que já existiam. As barras do
gráfico de tempo de indexação são `\rule`.

**O `.docx` é OOXML montado à mão.** Não há biblioteca de Office nesta máquina.
O `gerar_roteiro.py` escreve as quatro partes que o Word exige e valida o
resultado: o pacote é lido de volta, todo XML é parseado e a soma dos tempos é
conferida contra a janela de 10 a 15 minutos, falhando em vez de gerar arquivo
fora do combinado.

## Rastreabilidade dos números

Todo valor citado nos slides e no roteiro vem das tabelas do relatório parcial
(`docx/relatorio_parcial/secoes/06-resultados.tex`), conferidas por script
contra os JSONs de `code/results/` da sessão de medição de 2026-08-23. Nada foi
recalculado nem arredondado aqui sem conferência — inclusive os arredondamentos
para linguagem falada ("seis por cento" para 0,0595, "2,6 GiB" para 2.612,6
MiB).

## Se o tempo apertar

Os slides 4 e 8 aceitam corte sem quebrar a história. O miolo são os slides 11,
12 e 13 — o achado do `recall` igual a 1,0000 — e apressá-los tira o único
ponto que a plateia leva para casa. O roteiro registra isso no cabeçalho.
