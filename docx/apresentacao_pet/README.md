# Apresentação do relatório parcial — PET/IEG

Três saídas, uma fonte. `conteudo.py` guarda o texto; o PDF, o `.pptx` e o
roteiro falado derivam dele. Janela de 10 a 15 minutos; o roteiro fecha em
11:50, o que deixa folga para pergunta no meio.

## Comandos

```bash
make tudo      # corpo do .tex, PDF, roteiro .docx e .pptx
make slides    # só o PDF
make pptx      # só o .pptx, e roda a guarda de consistência
make roteiro   # só o roteiro
make clean
```

## Quem é fonte de quê

| Arquivo | Papel | Versionado |
|---|---|---|
| `conteudo.py` | **fonte única** do texto, do roteiro e dos tempos | sim |
| `slides.tex` | só a diagramação; dá `\input` no corpo gerado | sim |
| `gerar_tex.py` | escreve `corpo-gerado.tex` a partir de `conteudo.py` | sim |
| `gerar_pptx.py` | monta o `.pptx` a partir de `conteudo.py` | sim |
| `gerar_roteiro.py` | monta o roteiro `.docx` a partir de `conteudo.py` | sim |
| `logos/` | logos do PET e da UFOPA, extraídas da apresentação anterior | sim |
| `corpo-gerado.tex`, `slides.pdf`, `Apresentacao_PET.pptx`, `Roteiro_Apresentacao_PET.docx` | saídas | não |

Editar o texto num dos arquivos gerados não faz sentido: a próxima execução do
`make` sobrescreve. Texto muda em `conteudo.py`.

## Linguagem

O público é o PET do IEG, em maioria de engenharia — dois colegas de computação
além do bolsista. Duas exigências ao mesmo tempo: sem jargão de banco de dados
e sem tom coloquial, porque o orientador está na sala e o trabalho é o mesmo do
artigo submetido.

- **Títulos são frases nominais descritivas**, como em apresentação técnica:
  "Objetivo do trabalho", "Metodologia: controle das variáveis", "Diagnóstico
  do resultado anômalo", "Contraprova". Não títulos de narrativa em primeira
  pessoa.
- **O título da capa é o título oficial do trabalho**, literalmente o mesmo da
  submissão à Jornada Acadêmica. Não encurtar nem reescrever.
- Vocabulário técnico traduzido, não omitido: `recall` é "acerto", `ef_search`
  é "o parâmetro de ajuste", o índice HNSW é "uma malha de ligações entre os
  pontos", e a curva recall × vazão é uma curva de operação com um ponto de
  operação a escolher. A taxonomia do artigo entra como está — "sistema
  estendido" e "sistemas especializados".
- As comparações vêm de controle de variável e verificação de instrumentação,
  repertório que essa turma já tem. O achado central é apresentado como
  diagnóstico de resultado anômalo, não como reviravolta narrativa.
- Vetor, coordenada e distância entram sem rodeio: é conteúdo que a turma tem.
- Zero citação, uma ideia por slide.
- O roteiro é em **deixas**, não em parágrafos. Frase curta na ordem em que faz
  sentido, para o apresentador falar com as palavras dele. Parágrafo lido em pé
  soa lido.

## Forma

Segue a diagramação da apresentação anterior do grupo: 16:9, fundo branco,
título em negrito no alto à esquerda, azul `#2C71AD` como destaque, navy
`#152039`, número do slide no canto inferior direito. A paleta foi amostrada
dos pixels do arquivo anterior.

Sobre o modelo, muda: a logo do PET aparece em todos os slides e não só na
capa; os números importantes viram manchete; o corpo é alinhado à esquerda,
porque em fonte grande a justificação parte palavra ao meio; e há um slide de
fecho com a lição, que o modelo não tinha.

`slides.tex` não usa `beamer` nem `tikz` — nenhum dos dois está instalado no
TinyTeX desta máquina, e instalar pacote é decisão do piloto. O deck sai de
`article`, `geometry`, `xcolor` e `graphicx`; as barras são `\rule`.

## O que é verificado, e o que não é

Verificado automaticamente:

- **PDF**: 15 páginas e zero avisos de caixa (`Overfull`/`Underfull`).
- **Roteiro**: soma dos tempos dentro da janela de 10 a 15 minutos — o gerador
  falha em vez de gravar um roteiro fora do combinado.
- **`.pptx`**: pacote lido de volta, todo XML parseado, toda relação apontando
  para parte existente, todo `r:embed` declarado no `.rels` do próprio slide, e
  nenhum slide passando do limite inferior da área útil.
- **Consistência**: `gerar_pptx.py --verificar` extrai os números do PDF
  compilado e os do conteúdo e falha se os conjuntos diferirem. Pega corpo
  gerado velho no disco.

**Não** verificado: a diagramação do `.pptx`. Não há PowerPoint nem LibreOffice
nesta máquina. O Quick Look do macOS renderiza a capa, e foi assim que a fonte
errada apareceu — Calibri não existe aqui e caía em serifa, por isso o deck usa
Arial, que existe nos dois sistemas. Dos outros 14 slides, o que garante o
resultado é a checagem de área útil e o `normAutofit` ligado, que faz o
PowerPoint encolher o texto se alguma caixa apertar. Abrir e passar o olho
continua sendo trabalho do piloto.

## Rastreabilidade dos números

Todo valor citado vem das tabelas do relatório parcial
(`docx/relatorio_parcial/secoes/06-resultados.tex`), conferidas por script
contra os JSONs de `code/results/` da sessão de 2026-08-23. Os arredondamentos
para linguagem falada também foram conferidos: "seis por cento" para 0,0595 e
"2,6 GiB" para 2.612,6 MiB.

## Se o tempo apertar

Corte nos slides 4 e 8. Os slides 11, 12 e 13 são o miolo — é onde está o
único achado que a plateia leva para casa — e apressá-los esvazia a
apresentação. O roteiro registra isso no cabeçalho.
