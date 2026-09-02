# Submissão à XIII Jornada Acadêmica da Ufopa (2026)

Resumo expandido derivado do relatório parcial, no formato exigido pelo modelo oficial do evento.

## Quem é fonte de quê

| Arquivo | Papel | Versionado |
|---|---|---|
| `main.tex` | **fonte única** do texto submetido, e réplica da diagramação do modelo | sim |
| `gerar_docx.py` | preenche uma cópia do modelo com o texto extraído do `main.tex` | sim |
| `modelo/*.docx` | modelo oficial baixado do evento, **nunca modificado** | sim |
| `Resumo_Jornada_Academica_2026_RafaelNobre.docx` | entregável, gerado por `make docx` | não |
| `main.pdf` | conferência de diagramação e contagem de páginas, gerado por `make pdf` | não |
| `banner-jornada.png` | logo extraída do próprio modelo por `make` | não |

**Não editar o `.docx` gerado à mão.** A edição se perde na próxima geração e as duas versões passam a divergir em silêncio — foi exatamente o que aconteceu com a cópia `relatorio_parcial_envio/` em julho de 2026 (vide `vault/lições/2026-08-16-fork-silencioso-do-relatorio.md`). Texto muda no `main.tex`, e só ali.

## Por que existem dois artefatos de saída

O `.docx` é o que adere ao modelo de forma estrita: sai de uma cópia do arquivo oficial, com estilos, cabeçalho com a logo, rodapé, margens e configuração de página preservados byte a byte — as 22 partes do pacote são as mesmas, e o `sectPr` é idêntico ao do original.

O `.pdf` existe porque não há LibreOffice nem Word na máquina de trabalho, e sem eles não é possível converter o `.docx` para conferir o limite de três páginas. A réplica em LaTeX reproduz a diagramação medida no XML do modelo e permite contar as páginas de fato, em vez de estimar.

## Comandos

```bash
make verificar   # confere os limites do modelo, sem gerar arquivo
make docx        # gera o entregável a partir do main.tex
make pdf         # gera o PDF de conferência e imprime a contagem de páginas
make tudo        # os três acima, na ordem
make clean
```

## Limites do modelo, aplicados por `make verificar`

| Seção | Limite | Atual |
|---|---|---|
| Resumo | 150 a 500 palavras, parágrafo único | 266 palavras |
| Introdução | 1.000 caracteres com espaços | 952 |
| Metodologia | 1.000 caracteres | 985 |
| Resultados e discussão | 2.000 caracteres | 1.983 |
| Conclusões | 1.000 caracteres | 841 |
| Palavras-chave | 3 a 5 termos | 4 |
| Documento | máximo 3 páginas | 2 |

O `gerar_docx.py` aplica os mesmos limites e **falha** em vez de gerar um arquivo fora da norma, para que o limite não dependa de alguém lembrar de conferir.

## Diagramação medida no modelo

Extraída do XML, não estimada: A4 (21,03 × 29,70 cm); margens superior e inferior de 0,80 cm, esquerda 2,00 cm, direita 1,50 cm; Times New Roman em todo o documento; subevento, título e autores em 12 pt centralizados, os dois primeiros em negrito; afiliações em 10 pt itálico; títulos de seção em 12 pt negrito e caixa alta; corpo em 10 pt justificado, entrelinha exata de 12 pt, recuo de primeira linha de 0,36 cm; índices dos autores em expoente; rodapé com o nome do evento, as oito cidades e o ano.

## O que falta preencher antes de submeter

- **Nome do subevento e o numeral da edição de 2026**, na primeira linha. Está como `[INSERIR NOME DO SUBEVENTO E O NUMERAL DA EDIÇÃO DE 2026]` porque o dado não consta em nenhum arquivo do projeto e o numeral do exemplo do modelo (XV) é de outra edição.
- **Apoio financeiro**, se houver. A linha foi omitida por decisão de 2026-09-02, mas o projeto é uma Iniciação Científica com bolsista, então vale confirmar se há órgão de fomento a declarar.

## Rastreabilidade dos números

Todo valor citado no texto vem das tabelas do relatório parcial (`docx/relatorio_parcial/secoes/06-resultados.tex`), que por sua vez foram conferidas por script contra os JSONs de `code/results/` da sessão de medição de 2026-08-23. Nenhum número foi recalculado aqui.
