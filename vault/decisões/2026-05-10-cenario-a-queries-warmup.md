---
tipo: decisão
data: 2026-05-10
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [metodologia, cenario-a, benchmark, queries, warmup, recall]
---

# Cenário A: origem das queries, warmup de latência e escopo na Etapa 2

## Contexto
A ADR [[2026-04-28-dataset-ms-marco]] fixou que o ground truth para recall@K na IC é **busca exata (brute-force)** sobre o mesmo subset (não os qrels originais), para medir *fidelidade do índice ANN*, não qualidade do modelo de embedding. A ADR [[2026-04-28-cenarios-A-B-C]] definiu o Cenário A como busca semântica pura com métricas p50/p95/p99, QPS e recall@K. Ao implementar `benchmarks/cenario_a.py` (Dia 3 da Etapa 2), três pontos não cobertos pelas ADRs anteriores precisaram de decisão, pois mudam o protocolo experimental e o código.

## Decisões

### 1. Origem dos vetores de query: passages held-out
**Escolhido:** usar passages do MS MARCO **fora do range seedado** como vetores de query (split held-out), no estilo ANN-Benchmarks.

- **Opções consideradas:**
  - (a) *Passages held-out* — passages de índice `N..N+Q` (após os `N` seedados), embeddados pelo mesmo MiniLM, usados como queries. **Escolhido.**
  - (b) *queries.dev.tsv oficiais* — queries reais de usuário do MS MARCO.
- **Justificativa:** o objetivo declarado do Cenário A (ADR de cenários + de dataset) é medir a **fidelidade do índice ANN** contra busca exata, não o realismo do retrieval. A fidelidade é medida da mesma forma (ANN vs brute-force sobre o subset) independentemente da naturalidade da query. A metodologia da IC cita explicitamente ANN-Benchmarks (Aumüller et al., 2020) como inspiração, e ANN-Benchmarks usa split held-out do mesmo dataset como query set. Opção (a) elimina download adicional, mapeamento de qrels e dependência de formato externo, sem perda metodológica para o que o Cenário A testa.
- **Consequência:** o pipeline reserva os primeiros `N` passages (por `passage_id` ascendente) para o seed e os `Q` seguintes como queries. Determinístico e reproduzível. Queries reais (`queries.dev.tsv` + qrels) ficam disponíveis para uma eventual avaliação de *qualidade de retrieval* no relatório final, se o orientador solicitar — não confundir com fidelidade do índice.

### 2. Warmup + descarte nas medições de latência
**Escolhido:** rodar um lote de **warmup** (default ~50 queries) descartado antes de medir, e registrar o número de warmup no JSON de resultado.

- **Justificativa:** p95/p99 são sensíveis a efeitos de cache frio (page cache do SO, conexões TCP, plano de consulta, JIT). Medir desde a primeira query infla as caudas e torna a comparação entre os 3 SGBDs injusta (cada um aquece em ritmo diferente). Descartar o warmup mede regime estacionário, que é o que importa para a comparação. Prática padrão em benchmark de latência.
- **Consequência:** o `ResultadoBenchmark.parametros` inclui `warmup` (nº de queries descartadas) para rastreabilidade. O número é configurável; default documentado.

### 3. Escopo na Etapa 2: script + smoke com N pequeno
**Escolhido:** no Dia 3 da Etapa 2, entregar o script `cenario_a.py` correto e validá-lo com **N pequeno** (smoke ~10k, conforme a "Definição de pronto" da Etapa 2). A execução experimental real (100k/500k) é da **Etapa 3**.

- **Justificativa:** a Etapa 2 entrega *ambiente e scripts reproduzíveis*; a Etapa 3 produz os *resultados*. Gerar embeddings de 100k custa horas (vide [[../experimentos/2026-05-10-validacao-embeddings-100-passages]], extrapolação ~3 h só para 100k) e produziria nota de experimento real antes da hora, fora do escopo planejado.
- **Consequência:** `cenario_a.py` nasce com testes unitários (lógica de orquestração com fake) + capacidade de smoke de integração com N pequeno. A primeira execução experimental real vira nota em `vault/experimentos/` na Etapa 3.

## Critério de revisão
Reabrir se: (a) o orientador requisitar avaliação de qualidade de retrieval (aí entram `queries.dev.tsv` + qrels, decisão separada — não substitui esta); (b) o warmup default se mostrar insuficiente para estabilizar p99 em algum SGBD durante a Etapa 3 (ajustar e registrar em nota de experimento); (c) o split held-out introduzir viés de distribuição detectável (improvável — mesmo corpus, mesmo modelo).

## Backlinks
- [[2026-04-28-dataset-ms-marco]]
- [[2026-04-28-cenarios-A-B-C]]
- [[2026-04-28-modelo-embedding-minilm]]
- [[../experimentos/2026-05-10-validacao-embeddings-100-passages]]
- [[../../docs/tasks/etapa-2-preparacao-ambiente]]
- [[../referência/metodologia-benchmarking-ann]]
