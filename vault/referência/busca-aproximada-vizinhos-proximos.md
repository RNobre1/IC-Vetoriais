---
tipo: referência
conceito: "Busca aproximada de vizinhos próximos (ANN) e HNSW"
tags: [ann, hnsw, ivf, indexação, busca]
---

# Busca aproximada de vizinhos próximos (ANN)

## Definição
Família de algoritmos que retornam K vetores aproximadamente mais próximos de uma consulta q em ℝᵈ, trocando garantia de exatidão por **redução drástica de tempo de busca**. Em vez de O(N·d) da busca exata (brute-force), ANN típica entrega O(log N · d) ou similar, ao custo de recall < 100%.

## Formalização
Dado X = {x₁, ..., xₙ} ⊂ ℝᵈ e consulta q, a busca exata kNN retorna:

NNₖ(q) = argtop-K_{x ∈ X} sim(q, x)

ANN retorna ÑNₖ(q) ⊆ X com |ÑNₖ(q)| = K, e a métrica de qualidade é:

recall@K = |ÑNₖ(q) ∩ NNₖ(q)| / K

A métrica conjunta é a **fronteira Pareto recall × QPS** (queries per second): para cada configuração de parâmetros, plota-se (recall@K, QPS). Um sistema domina outro se entrega maior QPS ao mesmo recall (ou maior recall ao mesmo QPS).

## Variantes
- **HNSW (Hierarchical Navigable Small World)** — Malkov & Yashunin (2018). Grafo de proximidade em camadas; busca greedy do topo para a base. Padrão de fato em 2024–2026 para ANN em alta dimensionalidade.
  - Parâmetros: **M** (conexões por nó), **efConstruction** (qualidade da construção), **efSearch** (qualidade da consulta).
- **IVF (Inverted File Index):** clusteriza vetores (e.g. k-means com K_centroides), busca apenas em clusters próximos da query (parâmetro `nprobe`).
- **IVF-PQ (Product Quantization):** IVF + compressão dos vetores em sub-quantizadores. Trade-off explícito: muito menor memória, recall menor.
- **ScaNN (Google):** combina IVF, anisotropic quantization e re-ranking exato.
- **DiskANN (Microsoft):** otimizado para datasets que não cabem em RAM; usa disco com layout cuidadoso.

## Onde aparece neste estudo
Seção §3.3. Decisão metodológica chave: **HNSW em todos os três sistemas** ([[decisões/2026-04-28-índice-hnsw-em-todos]]) para isolar efeito de implementação. Os parâmetros M, efConstruction e efSearch são reportados em cada experimento ([[experimentos/]]).

## Papers canônicos
- [[papers/Malkov-Yashunin-2018-HNSW]]
- [[papers/Aumuller-Bernhardsson-Faithfull-2020-ANN-Benchmarks]]

## Pegadinhas
- "Recall" em ANN é medido **contra a busca exata sobre o mesmo conjunto**, não contra ground truth de relevância humana. Não confundir com qualidade de retrieval do modelo de embedding.
- Aumentar `efSearch` melhora recall ao custo de latência. Curva monotônica até saturar próximo de 1.0.
- HNSW guarda o índice **em memória**. Estimar uso: ~1.5× a 2× o tamanho dos vetores em fp32, dependendo de M.
- IVF e HNSW têm comportamento muito diferente sob escrita: IVF degrada graciosamente (basta atribuir o vetor novo ao cluster mais próximo); HNSW degrada porque cada inserção custa O(log N) navegações no grafo. Importante para o **Cenário C** (carga mista RAG).
- "Busca exata" para ground truth em 1M vetores ainda é cara: ~minutos por query em CPU. Cachear resultados por query para reuso entre sistemas.
