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
   - Prós: ~8.8M passages, ~1M queries com julgamentos de relevância (qrels) BM25-rotuladas e versões refinadas. Padrão da literatura de retrieval (BEIR, MTEB, ANN-Benchmarks textual). Inglês, gratuito, redistribuível para pesquisa.
   - Contras: julgamentos esparsos (média ~1 relevante por query). Não é em PT-BR.
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
- ANN-Benchmarks (Aumüller et al., 2020) e a literatura de SGBD vetoriais (Pan et al., 2023) usam MS MARCO ou derivados como referência. Resultados são comparáveis com a literatura.
- Tamanho de 8.8M permite cortar 100k / 500k / 1M com margem.
- Inglês não é problema: a IC compara **SGBDs**, não qualidade linguística do embedding em PT-BR. O modelo MiniLM foi treinado em inglês.

## Consequência
- Pipeline precisa baixar `collection.tsv` (~3 GB) e `qrels.dev.tsv` do site oficial. Datasets entram em `data/` (gitignored).
- Subsets são determinísticos: seed fixo + ordenação por `passage_id`. Documentado em `vault/experimentos/`.
- O ground truth para recall@K na IC é **busca exata** (brute-force) sobre o mesmo subset, não os qrels originais. Isso porque queremos medir fidelidade do índice ANN, não qualidade do modelo de embedding. Os qrels originais ficam disponíveis se o orientador pedir avaliação de qualidade do retrieval no relatório final.

## Critério de revisão
Reabrir se: (a) MS MARCO mudar de licença ou ficar indisponível, ou (b) houver requisito explícito do orientador para avaliar em PT-BR no relatório final.

## Backlinks
- [[decisões/2026-04-28-tamanhos-100k-500k-1m]]
- [[referência/metodologia-benchmarking-ann]]
