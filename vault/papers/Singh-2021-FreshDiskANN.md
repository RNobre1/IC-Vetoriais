---
tipo: paper
autores: ["Singh, A.", "Subramanya, S. J.", "Krishnaswamy, R.", "Simhadri, H. V."]
ano: 2021
titulo: "FreshDiskANN: A Fast and Accurate Graph-Based ANN Index for Streaming Similarity Search"
venue: "arXiv:2105.09613 (preprint)"
tags: [ann, indice-dinamico, insercao, cenario-c]
citacao_abnt: "SINGH, A. et al. FreshDiskANN: a fast and accurate graph-based ANN index for streaming similarity search. arXiv:2105.09613, 2021."
arquivo_local: ""
---

# FreshDiskANN: A Fast and Accurate Graph-Based ANN Index for Streaming Similarity Search

Fichamento curto, feito em 15/11/2026 a partir do resumo e das seções consultadas para a ampliação da bibliografia do relatório final. Metadados conferidos em fonte primária. Não há versão publicada em periódico ou conferência localizada em 15/11/2026; citado como preprint.

## Síntese
Aponta que índices ANN de grafo são estáticos e, na prática, reconstruídos periodicamente a custo alto. Propõe um índice que absorve milhares de inserções, remoções e buscas concorrentes por segundo mantendo mais de 95% de 5-recall@5, com o recall medido sobre o conteúdo corrente do índice.

## Relevância para a IC
Fundamenta o Cenário C (§3.3) e a escolha de medir o recall contra a verdade exata que cresce com as inserções confirmadas. Cuidado: os resultados são do sistema dos autores, não de HNSW nos três SGBDs; o artigo trata sobretudo de remoções, e o Cenário C só insere.

## Backlinks
- [[../referência/busca-aproximada-vizinhos-proximos]]
