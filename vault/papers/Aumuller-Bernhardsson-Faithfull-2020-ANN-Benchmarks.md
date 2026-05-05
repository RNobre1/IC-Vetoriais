---
tipo: paper
autores: ["Aumüller, M.", "Bernhardsson, E.", "Faithfull, A."]
ano: 2020
titulo: "ANN-Benchmarks: A benchmarking tool for approximate nearest neighbor algorithms"
venue: "Information Systems"
tags: [ann, benchmark, metodologia, foundational]
citacao_abnt: "AUMÜLLER, M.; BERNHARDSSON, E.; FAITHFULL, A. ANN-Benchmarks: A benchmarking tool for approximate nearest neighbor algorithms. Information Systems, v. 87, p. 101374, 2020."
arquivo_local: ""
---

# ANN-Benchmarks: A benchmarking tool for approximate nearest neighbor algorithms

> **Status do fichamento:** PDF **não disponível localmente** em `vault/papers/`. Preenchido a partir de conhecimento da metodologia ANN-Benchmarks (também documentada em http://ann-benchmarks.com). Baixar PDF e revisar antes de citar no relatório final.

## Síntese
Paper que introduz o framework open-source **ANN-Benchmarks** e estabelece a metodologia que se tornou padrão para comparação de algoritmos de busca aproximada de vizinhos próximos: avaliação por **curvas Pareto recall × QPS** sobre datasets padronizados. Substitui a prática anterior de reportar números pontuais (que mascaram trade-offs configuráveis) por uma fronteira de Pareto que torna comparações honestas.

## Contribuições
- Framework reproduzível para avaliar bibliotecas de ANN (FAISS, Annoy, HNSW, IVF-PQ, ScaNN etc.) sob condições controladas.
- Conjunto de datasets padronizados (SIFT-1M, GIST-1M, GloVe, MNIST, MS MARCO etc.).
- Metodologia explícita: para cada algoritmo, varrer parâmetros em uma grade; plotar (recall, QPS) e extrair a fronteira de Pareto.
- Apresentação visual padrão (eixos log-QPS × recall) que se tornou referência da literatura.

## Método
- Cada algoritmo é executado sob múltiplas configurações de hiperparâmetros (e.g. M, ef em HNSW; nlist, nprobe em IVF).
- Para cada configuração: medir recall@K (K tipicamente 10 ou 100) e QPS sob single-thread, single-client.
- Pontos formam uma nuvem; a fronteira superior-direita é a Pareto frontier do algoritmo.
- Sistemas são comparados pela posição relativa de suas fronteiras.

## Resultados-chave
- HNSW (versão `hnswlib`) emerge como Pareto-dominante em vários datasets densos.
- IVF-PQ relevante quando memória é restrição forte (compressão por quantização).
- Algoritmos baseados em árvores (Annoy, FLANN) ficam atrás em alta dimensionalidade.

## Limitações
- Single-client por padrão — não captura comportamento sob concorrência.
- Não mede latência de inserção (índices estáticos).
- Foco em algoritmos in-memory; não cobre cenários disk-resident.
- Não mede uso de memória de forma uniforme entre algoritmos.

## Relevância para a IC
**Sustenta §3.6 do relatório parcial** ([[referência/metodologia-benchmarking-ann]]). É a inspiração metodológica direta dos cenários A e B desta IC. Mas o estudo **vai além** de ANN-Benchmarks ao incluir:
- Cenário B: filtros estruturados sobre vetores (não coberto).
- Cenário C: carga mista busca + ingestão concorrente (não coberto — ANN-Benchmarks assume índice estático).
- Comparação no nível do **SGBD** (pgvector, Qdrant, Weaviate), não só do algoritmo (hnswlib, FAISS).

A contribuição metodológica da IC é justamente preencher esses vazios.

## Citáveis
> *[Localizar a justificativa do uso de fronteiras Pareto vs. números pontuais para citar em §3.6.]*

## Backlinks
- [[referência/metodologia-benchmarking-ann]]
- [[referência/busca-aproximada-vizinhos-proximos]]
- [[papers/Malkov-Yashunin-2018-HNSW]]
- [[papers/Aerospike-2025-DB-Benchmarking-Best-Practices]]
