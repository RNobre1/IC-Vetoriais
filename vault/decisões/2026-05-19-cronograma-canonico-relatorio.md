---
tipo: decisão
data: 2026-05-19
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [cronograma, governança, relatório-parcial, rigor]
---

# Cronograma canônico = tabela do relatório parcial; demais documentos a espelham

## Contexto
Havia dois cronogramas conflitantes no projeto. (1) A tabela "Distribuição mensal" do relatório parcial (`docx/relatorio_parcial/secoes/08-cronograma.tex`): Etapa 1 Jan–Fev, **Etapa 2 Mar–Abr**, Etapa 3 Mai–Jun (fecha com o parcial), Etapa 4 Jul–Set, Etapa 5 Out–Dez; parcial fim Jul, final Dez. (2) Um bloco "Cronograma comprimido (Mai–Dez)" no `docs/metodologia.md`, criado porque a execução real começou em final de abril (Etapa 2 Mai–Jun, Etapa 3 Jul). Os dois documentos se contradiziam — risco de rigor: o entregável canônico não pode afirmar um plano que outro documento do projeto nega. Detectado em 2026-05-19 ao revisar onde a Etapa 2 estava.

## Opções consideradas
1. **Alinhar o relatório à execução real** — reescrever `08-cronograma.tex` para Mai–Dez comprimido.
   - Prós: documento reflete o que de fato aconteceu.
   - Contras: o piloto não quer alterar a tabela canônica; mexe no entregável.
2. **Manter tabela original + linha "execução real"** — duas verdades lado a lado no `.tex`.
   - Prós: transparente.
   - Contras: polui o entregável; o piloto rejeitou.
3. **Tabela do relatório é canônica e intocável; `docs/metodologia.md` e demais docs a espelham** — o cronograma de *planejamento* é o da tabela; as datas reais de execução vivem apenas no log factual (`vault/sessões/`, `vault/experimentos/`), nunca falsificadas.
   - Prós: uma única fonte de verdade para planejamento; entregável preservado; log de execução continua honesto e auditável (separação explícita planejamento × execução).
   - Contras: o cronograma de planejamento assume início em Jan (que não ocorreu) — assumido conscientemente pelo piloto.

## Decisão
**Escolhida:** Opção 3. A tabela "Distribuição mensal" de `docx/relatorio_parcial/secoes/08-cronograma.tex` é a **fonte de verdade do cronograma** e não deve ser alterada por desalinhamento com a execução. `docs/metodologia.md` (seção "Cronograma (Jan-Dez 2026)") e `docs/tasks/etapa-2-preparacao-ambiente.md` foram reescritos para espelhá-la. As datas reais (`2026-05-*`) permanecem nas notas de sessão/experimento como **log factual de execução**, explicitamente distintas do cronograma de planejamento.

## Justificativa
Decisão do piloto (Regra 1: o piloto define o rumo). Preserva o entregável canônico intacto e mantém rigor: nenhum dado de execução é falsificado — apenas se separa, de forma nomeada, "cronograma planejado" de "quando de fato foi feito". O `\todo` já presente no `.tex` ("Atualizar este cronograma a cada entrega") permanece válido para ajustes futuros, se o piloto decidir.

## Consequência
- Cronograma canônico vigente: Etapa 1 Jan–Fev · **Etapa 2 Mar–Abr** · Etapa 3 Mai–Jun (fecha parcial) · Etapa 4 Jul–Set · Etapa 5 Out–Dez. Parcial fim Jul/2026; final Dez/2026.
- "Onde estamos" passa a ser medido contra essa régua: em 19/Mai estamos no início da **Etapa 3** (experimentos A e B em 100k/500k), com a cauda da Etapa 2 (`cenario_b.py` + Dia 4) ainda aberta e bloqueando o avanço pleno.
- Qualquer documento novo que cite prazo deve referenciar a tabela canônica, não inventar cronograma paralelo.

## Critério de revisão
Reabrir só se o piloto decidir atualizar a própria tabela do relatório (o `\todo` prevê isso a cada entrega) ou se o orientador requisitar cronograma alinhado à execução real.

## Backlinks
- [[../../docs/tasks/etapa-2-preparacao-ambiente]]
- [[2026-05-05-migracao-relatorio-para-latex]]
- [[../sessões/2026-05-10]]
