# IC — Bancos de Dados Vetoriais

> Iniciação Científica · UFOPA / IEG · 2026

**TL;DR (English):** Undergraduate research project comparing PostgreSQL+pgvector against
specialized vector databases (Qdrant, Weaviate) for semantic search and RAG.
Methodology inspired by ANN-Benchmarks. Reporting recall × QPS curves at
100k / 500k / 1M embeddings using MS MARCO passages, sentence-transformers
all-MiniLM-L6-v2 (384-dim), HNSW indexing across all three systems.

---

## Pergunta de pesquisa

PostgreSQL + extensão `pgvector` tem desempenho competitivo com bancos vetoriais
especializados em cenários reais de busca semântica e RAG?

## Sistemas avaliados

- **PostgreSQL + pgvector** — banco relacional com extensão vetorial
- **Qdrant** — banco vetorial especializado
- **Weaviate** — banco vetorial especializado

Mesmo índice (HNSW) em todos os três — diferenças observadas refletem
implementação e arquitetura, não algoritmo.

## Pipeline de avaliação

- **Modelo de embedding:** `sentence-transformers/all-MiniLM-L6-v2` (384 dim, CPU-only — viabiliza datasets grandes no hardware disponível)
- **Dataset:** subset de MS MARCO passages (com ground truth de relevância)
- **Tamanhos avaliados:** 100k, 500k, 1M embeddings
- **Cenários:**
  - **A** — busca pura (top-K nearest neighbors)
  - **B** — busca com filtros de metadados
  - **C** — carga mista de RAG (busca + retrieval + filtro)

## Métricas

- **Latência por consulta** — p50 / p95 / p99
- **Throughput** — QPS sustentado
- **Qualidade** — recall@K vs busca exata
- **Custo** — footprint de memória, footprint em disco, tempo de indexação
- **Reportagem visual** — curvas recall × QPS (estilo ANN-Benchmarks), nunca números pontuais

## Stack

- **Linguagem:** Python (`sentence-transformers`)
- **Orquestração:** Docker Compose (3 serviços: postgres+pgvector, qdrant, weaviate)
- **Hardware base:** Dell G15 5530 — Intel i5-13450HX (10c/16t), 16 GiB DDR5, NVIDIA RTX 3050 6 GB, NVMe Kingston 1 TB
- **Possível extensão:** Cluster HPC do IEG/UFOPA na fase final, condicionada a viabilidade técnica e disponibilidade de acesso

## Estrutura do repositório

```
.
├── CLAUDE.md       # fonte de verdade do projeto (metodologia, decisões, cronograma)
├── code/           # docker-compose, scripts Python, benchmarks
├── docx/           # entregáveis canônicos (relatório parcial e final)
└── vault/          # workspace Obsidian — notas, fichamentos, drafts (parcialmente gitignored)
```

`data/` (datasets brutos), `vault/papers/` (artigos com direitos autorais) e `vault/.obsidian/workspace*` são gitignored.

## Cronograma — Mai/Dez 2026

| Etapa | Período | Saída |
|---|---|---|
| 1 — Revisão e planejamento | Mai/2026 | Fundamentação teórica consolidada |
| 2 — Ambiente e scripts | Mai-Jun/2026 | Pipeline rodando local |
| 3 — Experimentos fase 1 | Jul/2026 | Cenários A e B em 100k e 500k |
| **▶ Relatório parcial** | **Jul/2026** | **fecha Etapas 1-3** |
| 4 — Experimentos fase 2 | Ago-Out/2026 | 1M + cenário C, possível execução em HPC |
| 5 — Análise e redação final | Nov-Dez/2026 | — |
| **▶ Relatório final** | **Dez/2026** | **fecha Etapas 4-5** |

## Status atual

Em revisão bibliográfica e planejamento metodológico. Ambiente de benchmark em construção.

## Inspiração metodológica

- Aumüller, M., Bernhardsson, E., Faithfull, A. (2020). *ANN-Benchmarks: A benchmarking tool for approximate nearest neighbor algorithms.* Information Systems.
- Malkov, Y. A., Yashunin, D. A. (2018). *Efficient and robust approximate nearest neighbor search using HNSW graphs.* IEEE TPAMI.

## Equipe

- **Bolsista:** Rafael Nobre de Souza
- **Orientador:** Prof. Dr. Celson Pantoja Lima — UFOPA / IEG
- **Instituição:** Universidade Federal do Oeste do Pará — Instituto de Engenharia e Geociências, Santarém-PA
- **Curso:** Bacharelado em Ciência da Computação

## Licença / uso

Este repositório acompanha um projeto de Iniciação Científica institucional. O conteúdo é divulgado para fins acadêmicos e de transparência. Para reuso de scripts, dados ou metodologia, contate o bolsista ou o orientador.

---

*Última atualização: 2026-05-01.*
