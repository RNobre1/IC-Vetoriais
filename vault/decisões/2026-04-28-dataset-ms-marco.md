---
tipo: decisão
data: 2026-04-28
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [metodologia, dataset, ground-truth]
---

# Dataset textual: subset de MS MARCO passages

## Contexto
Para responder à pergunta "qual sistema oferece melhor recall × QPS", é obrigatório existir um **ground truth** de relevância. Sem ground truth, comparações de recall@K perdem significado. O dataset precisa também ter volume suficiente para ser dividido em 100k / 500k / 1M passages.

## Opções consideradas
1. **MS MARCO passages** (escolhido)
   - Prós: 8.841.823 passages e 532.761 pares de treino, com julgamentos de relevância (qrels) **anotados por avaliadores humanos** — derivam das passagens marcadas como contendo a resposta no conjunto QnA. Padrão da literatura de retrieval: o BEIR o adota como conjunto *in-domain* e registra que "the majority of the evaluated approaches are trained on the MS MARCO dataset". Inglês, sem custo, licença de uso para pesquisa não comercial.
   - Contras: julgamentos esparsos — a Tabela 1 do BEIR reporta **1,1 documento relevante por query**, com 6.980 queries de avaliação. Não é em PT-BR. A licença **não concede direito de redistribuição** — o `collection.tsv` fica em `data/` (gitignored) e cada pessoa baixa da fonte oficial.
2. **Wikipedia + queries sintéticas via LLM**
   - Prós: PT-BR disponível, volume amplo.
   - Contras: ground truth seria gerado pelo próprio bolsista — circular e frágil.
3. **Common Crawl com sampling temático**
   - Prós: volume elevado.
   - Contras: sem ground truth nativo. Precisaria curar.
4. **NQ (Natural Questions)**
   - Prós: ground truth de qualidade.
   - Contras: dataset menor (~300k passages no formato comum). Limita o teste em 1M.

## Decisão
**Escolhida:** opção 1 — subset reproduzível de MS MARCO passages.

## Justificativa
- Ground truth gratuito e bem documentado é condição necessária para reportar recall@K honesto.
- O Big-ANN Challenge da NeurIPS'23 usa exatamente este conjunto na *sparse track* — "the common MSMARCO passage retrieval dataset, which has 8,841,823 text passages" ([big-ann-benchmarks.com](https://big-ann-benchmarks.com/neurips23.html)). Resultados ficam comparáveis com essa literatura.
- Tamanho de 8.841.823 permite cortar 100k / 500k / 1M com margem.
- Inglês não é problema: a IC compara **SGBDs**, não qualidade linguística do embedding em PT-BR. O modelo MiniLM foi treinado em inglês.

## Consequência
- Pipeline precisa baixar `collection.tsv` (~3 GB) e `qrels.dev.tsv` do site oficial. Datasets entram em `data/` (gitignored).
- Subsets são determinísticos: seed fixo + ordenação por `passage_id`. Documentado em `vault/experimentos/`.
- O ground truth para recall@K na IC é **busca exata** (brute-force) sobre o mesmo subset, não os qrels originais. Isso porque queremos medir fidelidade do índice ANN, não qualidade do modelo de embedding. Os qrels originais ficam disponíveis se o orientador pedir avaliação de qualidade do retrieval no relatório final.

## Critério de revisão
Reabrir se: (a) MS MARCO mudar de licença ou ficar indisponível, ou (b) houver requisito explícito do orientador para avaliar em PT-BR no relatório final.

## Correções (2026-08-16)

Auditoria de proveniência desta ADR. A decisão em si continua válida; três afirmações de apoio estavam erradas e foram corrigidas acima:

| Afirmação original | Verificação | Correção |
|---|---|---|
| "qrels BM25-rotuladas" | O site oficial diz que os rótulos derivam das passagens marcadas como contendo a resposta no conjunto QnA — **anotação humana**. O BM25 gerou os candidatos do *reranking*, não os rótulos. | "anotados por avaliadores humanos" |
| "gratuito, redistribuível para pesquisa" | A licença é *"for non-commercial research purposes only (...) without extending any license or other intellectual property rights"* — **não concede redistribuição**. | "licença de uso para pesquisa não comercial", com nota de que não há direito de redistribuição |
| "ANN-Benchmarks (Aumüller et al., 2020) (...) usa MS MARCO" | O repositório oficial lista DEEP1B, Fashion-MNIST, GIST, GloVe, Kosarak, MNIST, MovieLens-10M, NYTimes, SIFT, Last.fm e COCO — **nenhum MS MARCO**. | Substituída pelo Big-ANN NeurIPS'23, cuja *sparse track* usa o conjunto |
| "a literatura de SGBD vetoriais (Pan et al., 2023) usa MS MARCO" | `pdftotext` sobre o PDF local (115.238 caracteres extraídos): **0 ocorrências** de "marco". O survey é conceitual e cita datasets nominais apenas duas vezes ("Yandex" e "Audio"). Falsa em dobro — não usa MS MARCO e praticamente não usa datasets nomeados. | Removida |

O número de *passages* passa a ser reportado exato (8.841.823), confirmado em **três fontes independentes**: a contagem de linhas do `collection.tsv` local, a página do Big-ANN NeurIPS'23 e a Tabela 1 do BEIR (PDF em `vault/papers/2104.08663v4.pdf`), que também fornece 6.980 queries de avaliação e 1,1 relevante por query.

A menção ao **BEIR** na lista original estava correta e foi restaurada com fonte — 31 ocorrências de "MS MARCO" no PDF, incluindo a declaração de que a maioria das abordagens avaliadas é treinada nele. O erro estava em agrupá-la com ANN-Benchmarks e Pan et al., que não sustentam a afirmação.

Nenhuma dessas afirmações havia chegado ao relatório — a verificação cobriu `docx/relatorio_parcial/secoes/` e não encontrou ocorrências. O que o relatório tinha era a ausência de citação para o dataset, corrigida com a entrada `bajaj2016msmarco` (orçamento bibliográfico: 13 → 14).

## Backlinks
- [[2026-04-28-tamanhos-100k-500k-1m]]
- [[../referência/metodologia-benchmarking-ann]]
- [[../papers/Aumuller-Bernhardsson-Faithfull-2020-ANN-Benchmarks]]
