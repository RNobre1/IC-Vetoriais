---
tipo: referência
conceito: "Retrieval-Augmented Generation (RAG)"
tags: [rag, llm, retrieval, generation]
---

# Retrieval-Augmented Generation (RAG)

## Definição
Arquitetura proposta por Lewis et al. (2020) que combina um **modelo recuperador** (retriever) — tipicamente busca por similaridade em um banco de embeddings — com um **modelo gerador** (decoder LLM) que condiciona a resposta nos passages recuperados. Endereça duas limitações de LLMs puros: conhecimento congelado no momento do treino e tendência à confabulação (hallucination).

## Formalização
Para uma consulta q:

1. **Retriever:** r(q) → {p₁, ..., pₖ} (top-K passages do índice de embeddings)
2. **Gerador:** g(q, p₁, ..., pₖ) → resposta y

A qualidade final P(y | q) depende de duas distribuições:
- P(p | q) — qualidade do retriever (recall e precision dos passages relevantes)
- P(y | q, p) — qualidade do gerador condicionada aos passages

A composição implica: **se o retriever falhar, nem o melhor gerador salva a resposta** — ele tende a confabular sobre passages irrelevantes.

## Variantes
- **Naive RAG:** retrieval simples → prompt direto ao LLM com os passages concatenados.
- **Advanced RAG:** query rewriting (HyDE, multi-query), re-ranking com cross-encoder, fusão de múltiplas consultas (RRF).
- **Modular RAG:** roteador de consultas, multi-hop retrieval, agentes que decidem quando recuperar.
- **GraphRAG:** integra grafos de conhecimento ao retrieval (entidades + relações além de passages).

## Onde aparece neste estudo
Seção §3.5. RAG é a **motivação aplicada principal** da IC: como o desempenho do banco vetorial impacta a viabilidade prática de sistemas RAG em produção (latência percebida pelo usuário, throughput sob carga, custo de hardware). O **Cenário C** ([[decisões/2026-04-28-cenarios-A-B-C]]) simula carga RAG mista (busca + ingestão concorrente).

## Papers canônicos
- [[papers/Lewis-2020-RAG]]
- [[papers/Bovas-2025-Navi-RAG-Chatbot]]
- [[papers/Pawlik-2025-LLM-Selection-Vector-DB-Tuning]]

## Pegadinhas
- Métricas de qualidade RAG (faithfulness, answer relevancy, context precision/recall) **não são objeto de estudo desta IC**. Aqui mede-se **infraestrutura de retrieval**, não qualidade do gerador.
- Latência total de RAG = latência de embedding da query + latência de busca vetorial + latência do LLM. A busca vetorial costuma ser a fração menor; mas em escala (1000+ usuários simultâneos) vira gargalo se mal dimensionada.
- "Vector store" e "vector database" são usados como sinônimos no jargão RAG; tecnicamente, um vector store pode ser apenas uma estrutura em memória (FAISS, NumPy), enquanto um VDBMS oferece persistência, transações e operação contínua.
- **Chunking** (como dividir o texto em passages) afeta dramaticamente o recall — variável de confusão se não controlada. Esta IC fixa estratégia de chunking e a documenta.
