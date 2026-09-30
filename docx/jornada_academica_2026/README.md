# Submissão à XIII Jornada Acadêmica da Ufopa (2026)

Resumo expandido derivado do relatório parcial, no formato exigido pelo modelo oficial do evento, submetido ao XII Seminário de Graduação. Aprovado; versão final, revisada conforme os pareceres, enviada pelo SIGEventos em 30/09/2026.

## De onde vem cada número

A cadeia é uma só e vai do dado mais recente ao texto derivado:

1. **Sessão de medição vigente** — os JSONs de `code/results/` da sessão que o relatório declara no §5 (em set/2026, a de 23/08).
2. **Relatório parcial** (`docx/relatorio_parcial/secoes/06-resultados.tex` e `07-consideracoes.tex`) — interpreta a sessão e carrega as ressalvas de cada número: tempo de indexação medido *default* contra *default*, QPS de cliente único, leitura só qualitativa da memória.
3. **Este resumo** (`main.tex`) — cita o relatório.

O valor reportado aqui é sempre o da sessão vigente. Execuções anteriores continuam sendo dado, e servem à comparação e à reprodutibilidade, mas não entram no lugar do valor vigente.

Antes de mudar qualquer afirmação, ler a seção correspondente do relatório atual e conferir que ela está lá com o mesmo sentido. A versão enviada em set/2026 tinha uma frase que nenhuma versão do relatório dizia (vide `vault/lições/2026-09-29-derivado-que-nao-confere-com-o-relatorio.md`).

### Afirmações que não estão, com essas palavras, no relatório

Cada uma foi derivada da sessão vigente, e a origem fica registrada aqui.

| Afirmação no `main.tex` | Origem |
|---|---|
| Construir o índice levou cerca de 21 minutos no pgvector com 500 mil vetores, contra menos de 3 nos especializados | Tabela de recursos (§5): 1.271,9 s, 159,3 s e 105,8 s, convertidos em minutos |
| No Weaviate o corte é de 40 mil itens; filtrar 10% dá 10 mil itens em 100 mil vetores e 50 mil em 500 mil | Texto do §5, Cenário B (`flatSearchCutoff`, padrão 40.000) |
| Com filtro de 1%, o pgvector recupera no máximo cerca de um quarto dos vizinhos corretos, mesmo no maior `ef_search` | JSONs de 23/08, Cenário B: o maior recall do pgvector em p = 1% é 0,2644 (500 mil, ef = 256), nas duas condições |
| No pgvector, subir o `ef_search` custa mais tempo por consulta que nos outros | Tabela do Cenário A, 100k (§5): p50 de 0,63 a 4,95 ms no pgvector, de 1,78 a 3,12 ms no Qdrant e de 0,84 a 1,89 ms no Weaviate |

## Quem é fonte de quê

| Arquivo | Papel | Versionado |
|---|---|---|
| `main.tex` | **fonte única** do texto submetido | sim |
| `gerar_docx.py` | preenche uma cópia do modelo com o texto extraído do `main.tex` e aplica os limites | sim |
| `test_gerar_docx.py` | testes das regras de limite (`make testar`) | sim |
| `modelo/*.docx` | modelo oficial baixado do evento, **nunca modificado** | sim |
| `Resumo_Jornada_Academica_2026_RafaelNobre.docx` | entregável, gerado por `make docx` | não |
| `Resumo_Jornada_Academica_2026_RafaelNobre.pdf` | entregável em PDF, exportado do `.docx` por `make pdf-entrega`; é nele que se contam as páginas | não |
| `main.pdf` | réplica aproximada em LaTeX, gerada por `make pdf`; **não serve para contar páginas** (vide abaixo) | não |
| `banner-jornada.png` | logo extraída do próprio modelo por `make` | não |

**Não editar o `.docx` gerado à mão.** A edição se perde na próxima geração e as duas versões passam a divergir em silêncio — foi exatamente o que aconteceu com a cópia `relatorio_parcial_envio/` em julho de 2026 (vide `vault/lições/2026-08-16-fork-silencioso-do-relatorio.md`). Texto muda no `main.tex`, e só ali.

## Como conferir o limite de três páginas

O `.docx` adere ao modelo de forma estrita: sai de uma cópia do arquivo oficial, com estilos, cabeçalho com a logo, rodapé, margens e configuração de página preservados — as 22 partes do pacote são as mesmas, e o `sectPr` é idêntico ao do original.

A contagem de páginas tem de sair **desse** `.docx`. Sem Word nem LibreOffice na máquina de trabalho, `make pdf-entrega` gera o `.docx`, exporta o PDF pelo Pages e imprime o número de páginas.

A réplica em LaTeX (`main.tex` → `main.pdf`) não substitui essa conferência. Ela foi montada com uma medição do modelo que não se confirma no XML (vide "Diagramação medida no modelo"), e por isso é mais compacta que o documento real: contava 2 páginas onde o `.docx` exportado tem 3.

## Comandos

```bash
make testar        # testes das regras de limite
make verificar     # confere os limites do modelo, sem gerar arquivo
make docx          # gera o .docx de entrega a partir do main.tex
make pdf-entrega   # gera o .docx, exporta o PDF de entrega e imprime a contagem de páginas
make pdf           # réplica LaTeX aproximada; não conta páginas
make tudo          # testar, verificar, pdf e docx, na ordem
make clean
```

## Limites do modelo

| Seção | Limite | Tipo |
|---|---|---|
| Resumo | 150 a 500 palavras, parágrafo único | rígido |
| Introdução | 1.000 caracteres com espaços | rígido |
| Metodologia | 1.000 caracteres com espaços | rígido |
| Resultados e discussão | 2.000 caracteres com espaços | flexível |
| Conclusões | 1.000 caracteres com espaços | flexível |
| Palavras-chave | 3 a 5 termos | rígido |
| Documento | máximo 3 páginas | conferido no PDF de entrega |

Os valores atuais saem de `make verificar`, não desta tabela.

O modelo permite passar dos limites de resultados e de conclusões "desde que o tamanho total do documento não ultrapasse três páginas". O `gerar_docx.py` **falha** nos limites rígidos e só **avisa** nos flexíveis; a condição das três páginas se confere com `make pdf-entrega`.

## Diagramação medida no modelo

Extraída da formatação direta dos parágrafos em `word/document.xml`: A4 (21,03 × 29,70 cm); margens superior e inferior de 0,80 cm, esquerda de 2,00 cm e direita de 1,50 cm; Times New Roman 12 pt no corpo, com entrelinha simples; subevento, título e autores centralizados, os dois primeiros em negrito; afiliações em 12 pt, sem itálico (o `<w:i w:val="0"/>` desliga o itálico); títulos de seção em negrito, caixa alta e vermelho (`#C00000`); rótulos `Palavras-chave:`, `Autorização legal:` e `Apoio financeiro:` em negrito vermelho, com o conteúdo em preto; corpo justificado, com recuo de primeira linha de 1,27 cm nas seções e sem recuo no resumo; rodapé com o nome do evento, as oito cidades e o ano.

Até set/2026 esta seção registrava corpo em 10 pt, entrelinha exata de 12 pt, recuo de 0,36 cm e afiliações em 10 pt itálico. O XML não confirma nenhum desses valores, e a réplica em `main.tex` ainda os usa.

## Campos de identificação

- **Subevento:** `XII Seminário de Graduação`, na seção `SUBEVENTO` do `main.tex`. O gerador falha se a linha ainda tiver o texto de exemplo do modelo.
- **Programa:** o modelo não tem campo para o programa, mas as normas do seminário (seção 6) pedem o nome do programa e o vínculo com a PROEN. O parágrafo `Autorização legal:` do modelo, que não se aplica a este trabalho, é reaproveitado com o rótulo `Programa:`, o que preserva a contagem de parágrafos do modelo.
- **Apoio financeiro:** FNDE/MEC, como as normas pedem para o PET.
