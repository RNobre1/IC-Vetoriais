---
tipo: lição-aprendida
data: 2026-08-16
contexto: Auditoria pré-entrega do relatório parcial. Descoberto que `docx/relatorio_parcial_envio/` era uma cópia integral do projeto LaTeX que havia divergido da fonte canônica em cinco arquivos. Vide [[../sessões/2026-08-16]].
tags: [latex, relatório, regra-2a, fonte-única, bibliografia, abnt]
---

# Copiar o projeto LaTeX para "gerar o PDF de envio" criou um fork que divergiu em 5 arquivos

## Situação

Em julho, na hora de produzir o PDF para o orientador, o projeto LaTeX inteiro foi copiado de `docx/relatorio_parcial/` para `docx/relatorio_parcial_envio/`. Os ajustes finais foram feitos **na cópia**. Um mês depois, a comparação mostrou divergência em cinco arquivos:

| Arquivo | O que só existia na cópia |
|---|---|
| `refs.bib` | entrada `aumueller2020ann` |
| `main.tex` | `\usepackage{float}` |
| `secoes/04-fundamentacao.tex` | remoção de um `\todo` |
| `secoes/05-metodologia.tex` | `\allowbreak` para quebra de linha |
| `secoes/06-resultados.tex` | posicionamento `[H]` / `[htbp]` das tabelas |

Ou seja: a cópia era a versão **mais avançada**, e a fonte declarada como canônica no `docs/metodologia.md` estava atrasada. Quem editasse o canônico estaria trabalhando no arquivo errado.

## O defeito que o fork produziu

O ponto mais sério não é a divergência em si — é o que ela escondia. O canônico cita `\cite{aumueller2020ann}` em `06-resultados.tex` **sem ter a entrada no `refs.bib`**: compilando a fonte canônica, a citação sai como `[?]`. A cópia "consertou" isso adicionando a entrada.

Só que `refs.bib` **já tinha** a mesma obra sob a chave `aumuller2020annbench` (Aumüller, Bernhardsson & Faithfull, *Information Systems*, v. 87, p. 101374, 2020), citada em `04-fundamentacao.tex`. O "conserto" criou uma **duplicata bibliográfica**: ANN-Benchmarks apareceria duas vezes na lista de referências do PDF entregue, e o orçamento de 13 referências viraria 14 sem que ninguém tivesse decidido isso.

A correção certa era de uma linha — apontar a citação para a chave que já existia.

## Causa

O fork nasce de uma necessidade legítima ("preciso de um PDF estável para enviar") resolvida da forma errada (copiar a árvore). A partir do momento em que existem duas cópias editáveis, toda edição precisa escolher um lado, e a escolha não é registrada em lugar nenhum. Em uma semana ninguém lembra qual é qual.

É a Regra 2-A no domínio de documentos: o PDF de envio é um **artefato derivado**, não uma segunda fonte. Deriva-se por compilação, não por cópia.

## Regra para o futuro

1. **Nunca duplicar a árvore do projeto LaTeX.** O PDF de envio sai de `make pdf` na fonte canônica, e o arquivo resultante é renomeado/copiado — só o PDF, nunca os `.tex`.
2. **Antes de qualquer edição em `docx/`, conferir que não existe diretório irmão com nome sufixado** (`_envio`, `_final`, `_v2`, `_orientador`). Se existir, consolidar **antes** de editar.
3. **Guarda de citações no ciclo de revisão**: cruzar as chaves citadas nos `.tex` com as entradas do `refs.bib`, nos dois sentidos. Pega citação órfã e entrada não citada:

   ```bash
   grep -ohE '\\cite(online)?\{[^}]+\}' secoes/*.tex | sed -E 's/.*\{([^}]+)\}/\1/' \
     | tr ',' '\n' | tr -d ' ' | sort -u > /tmp/citadas.txt
   grep -oE '^@[a-zA-Z]+\{[^,]+,' refs.bib | sed -E 's/^@[a-zA-Z]+\{([^,]+),/\1/' \
     | sort > /tmp/entradas.txt
   comm -23 /tmp/citadas.txt /tmp/entradas.txt   # citadas sem entrada
   comm -13 /tmp/citadas.txt /tmp/entradas.txt   # entradas não citadas
   ```
4. **Antes de adicionar entrada ao `refs.bib`, procurar a obra pelo título e pelos autores**, não pela chave. Chave diferente não significa obra diferente — foi exatamente assim que a duplicata quase entrou.

## Consequência

- Melhorias da cópia portadas para a fonte canônica; `relatorio_parcial_envio/` eliminado.
- Citação corrigida para `aumuller2020annbench`; orçamento permanece em 13 referências.
- O `Makefile` do projeto canônico passa a ser o único caminho de geração do entregável.

## Backlinks

- [[../decisões/2026-05-05-migracao-relatorio-para-latex]]
- [[2026-05-05-rigor-citacoes-abnt]]
- [[../sessões/2026-08-16]]
