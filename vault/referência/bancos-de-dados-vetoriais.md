---
tipo: referência
conceito: "Vector Database Management Systems (VDBMS)"
tags: [vdbms, sgbd, pgvector, qdrant, weaviate]
---

# Bancos de Dados Vetoriais (VDBMS)

## Definição
Sistemas de gerenciamento de banco de dados projetados para armazenar, indexar e consultar embeddings de alta dimensionalidade com suporte a busca por similaridade (kNN ou ANN) como operação de primeira classe. Pan, Wang e Li (2023) caracterizam-nos como uma extensão natural dos SGBDs para o domínio de aplicações de IA.

## Variantes / Famílias
Duas categorias arquiteturais principais:

### A. Extensão de SGBD relacional
- **PostgreSQL + pgvector:** extensão que adiciona o tipo `vector` e operadores de distância (`<->` L2, `<=>` cosseno, `<#>` produto interno). Reaproveita planejador SQL, transações ACID, replicação física/lógica, ferramentas de operação maduras (psql, pg_dump, monitoração via pg_stat_*). Suporta IVF-Flat e HNSW.
- **Outros:** Oracle AI Vector Search, SingleStore, MariaDB com plugins, MySQL HeatWave Vector Store.

### B. Bancos vetoriais nativos (especializados)
- **Qdrant:** Rust, foco em performance, baixa latência e filtros estruturados nativos. HNSW. APIs REST e gRPC. Persistência em disco com snapshots.
- **Weaviate:** Go, foco em esquema explícito, GraphQL e modularidade (módulos de geração de embedding embutidos). HNSW. Boa integração com fluxos de RAG.
- **Milvus:** C++/Go, foco em escala distribuída e GPU. HNSW, IVF, DiskANN.
- **Pinecone:** SaaS proprietário, fora do escopo open-source.
- **Vespa, Chroma, LanceDB:** outras opções com posicionamentos distintos (Vespa para search híbrido, Chroma para protótipos, LanceDB com formato em disco columnar).

## Onde aparece neste estudo
Seção §3.4. Os três sistemas avaliados (pgvector, Qdrant, Weaviate) representam, juntos, ambas as categorias — ver [[decisões/2026-04-28-sistemas-avaliados]]. A IC busca evidência experimental para o trade-off categórico (relacional estendido vs. especializado nativo).

## Papers canônicos
- [[papers/Pan-Wang-Li-2023-Survey-VDBMS]]
- [[papers/Jing-2024-LLMs-Meet-Vector-Databases]]
- [[papers/Patel-2024-ACORN]]

## Pegadinhas
- "Banco vetorial" virou termo guarda-chuva. Marketing usa para qualquer coisa que armazena vetores; a literatura técnica reserva o termo para sistemas com indexação ANN nativa, persistência confiável, filtros estruturados e operação contínua.
- Latência reportada na documentação dos sistemas tipicamente é "warm cache, single client, índice ideal" — não comparável diretamente com cargas reais.
- Filtros estruturados sobre vetores ("predicate-aware ANN") é uma área aberta de pesquisa: cada sistema implementa diferente — pre-filter (filtra metadados antes do ANN), post-filter (busca ANN, filtra depois), ou in-index (filtros embutidos no grafo). O **Cenário B** da IC explora exatamente essa diferença.
- Qdrant e Weaviate suportam criação de coleções com metadados arbitrários; pgvector usa colunas SQL nativas. Modelagem de dados muda significativamente entre os três.
- Replicação e alta disponibilidade: pgvector herda do Postgres (maduro); Qdrant e Weaviate têm modelos próprios menos testados em produção crítica.
