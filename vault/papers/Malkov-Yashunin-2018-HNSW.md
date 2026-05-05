---
tipo: paper
autores: ["Malkov, Y. A.", "Yashunin, D. A."]
ano: 2018
titulo: "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs"
venue: "IEEE Transactions on Pattern Analysis and Machine Intelligence"
tags: [ann, hnsw, indexação, foundational]
citacao_abnt: "MALKOV, Y. A.; YASHUNIN, D. A. Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2018."
arquivo_local: ""
---

# Efficient and robust approximate nearest neighbor search using HNSW graphs

> **Status do fichamento:** PDF **não disponível localmente** em `vault/papers/`. Preenchido a partir de conhecimento amplamente difundido do algoritmo HNSW. Baixar o PDF (acesso aberto via arXiv:1603.09320) e revisar antes de citar no relatório final.

## Síntese
Paper canônico que introduz o algoritmo **HNSW (Hierarchical Navigable Small World)** para busca aproximada de vizinhos próximos em alta dimensionalidade. Constrói um grafo de proximidade em múltiplas camadas (inspirado em skip lists): camadas superiores têm poucos nós com conexões longas, camadas inferiores têm todos os nós com conexões curtas. A busca começa no topo, navega greedily até a base. Tornou-se o algoritmo de referência para ANN em SGBDs vetoriais — pgvector, Qdrant, Weaviate, Milvus e outros oferecem HNSW como índice principal.

## Contribuições
- Generalização do conceito de Navigable Small World para múltiplas camadas hierárquicas.
- Heurística de seleção de vizinhos (não trivial: balanço entre conexões diversas vs. concentradas) que mantém o grafo navegável sob inserções incrementais.
- Algoritmo de busca aproximada com priority queue e parâmetro `ef` que permite trade-off explícito entre recall e velocidade.
- Análise teórica de complexidade e ampla validação empírica contra alternativas (FLANN, NN-Descent, Annoy, FAISS-IVF).

## Método
- Construção: inserção incremental dos N pontos. Cada ponto é atribuído a uma camada máxima sorteada de uma distribuição exponencial. Em cada camada, conecta-se aos M vizinhos mais próximos via busca greedy + heurística de seleção.
- Busca: começa em um ponto entry da camada superior; em cada camada, faz busca greedy mantendo um conjunto dinâmico de candidatos de tamanho `ef`; desce camadas até a base; retorna os K mais próximos.
- Parâmetros principais: **M** (conexões por nó), **M_max** (limite superior em camadas baixas), **efConstruction** (qualidade de construção), **efSearch** (qualidade de consulta).

## Resultados-chave
- Pareto-dominante na época para datasets densos em alta dimensionalidade (SIFT, GIST, GloVe).
- Recall > 0.95 com QPS uma a duas ordens de grandeza acima de alternativas a recall comparável.
- Robusto em regime de inserções dinâmicas (não requer reconstrução total).

## Limitações
- Grafo guardado **em memória** — RAM cresce com N e M.
- Inserção custa O(log N) navegações; sob carga de escrita alta, latência de inserção pode degradar latência de consulta concorrente (relevante para o Cenário C da IC).
- Sensível à ordem de inserção em casos patológicos.
- Reconstrução parcial após muitas remoções é tópico aberto.

## Relevância para a IC
**Sustenta §3.3 do relatório parcial** e a [[decisões/2026-04-28-índice-hnsw-em-todos|decisão metodológica de usar HNSW nos três sistemas]]. Os parâmetros M, efConstruction e efSearch reportados em cada experimento referem-se a este paper. A discussão de resultados precisa explicitar que comparamos **três implementações** do mesmo algoritmo, isolando o efeito de implementação.

## Citáveis
> *[Localizar e citar a definição formal do grafo HNSW e a heurística de seleção de vizinhos. Páginas específicas a partir do PDF.]*

## Backlinks
- [[referência/busca-aproximada-vizinhos-proximos]]
- [[decisões/2026-04-28-índice-hnsw-em-todos]]
- [[papers/Aumuller-Bernhardsson-Faithfull-2020-ANN-Benchmarks]]
