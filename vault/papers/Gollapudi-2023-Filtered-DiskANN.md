---
tipo: paper
autores: ["Gollapudi, S.", "Karia, N.", "Sivashankar, V.", "Krishnaswamy, R.", "Begwani, N.", "Raz, S.", "Lin, Y.", "Zhang, Y.", "Mahapatro, N.", "Srinivasan, P.", "Singh, A.", "Simhadri, H. V."]
ano: 2023
titulo: "Filtered-DiskANN: Graph Algorithms for Approximate Nearest Neighbor Search with Filters"
venue: "WWW '23, p. 3406–3416"
tags: [ann, filtro, pos-filtragem, cenario-b]
citacao_abnt: "GOLLAPUDI, S. et al. Filtered-DiskANN: graph algorithms for approximate nearest neighbor search with filters. In: Proceedings of the ACM Web Conference 2023 (WWW '23). Austin: ACM, 2023. p. 3406–3416."
arquivo_local: ""
---

# Filtered-DiskANN: Graph Algorithms for Approximate Nearest Neighbor Search with Filters

Fichamento curto, feito em 15/11/2026 a partir do resumo e das seções consultadas para a ampliação da bibliografia do relatório final. Metadados conferidos em fonte primária. Ordem dos autores conferida no Crossref e no formato de referência da ACM no PDF.

## Síntese
Trata a busca ANN com filtro como problema próprio. Mostra que o pós-processamento (filtrar depois da busca) funciona mal quando o filtro é pouco específico, porque é preciso recuperar muitos candidatos antes de achar um elegível, e que um índice por rótulo é caro demais. Propõe um grafo construído com os rótulos.

## Relevância para a IC
Sustenta a leitura do pós-filtro do pgvector no Cenário B (§3.4 e §5): recall baixo sob seletividade restritiva. Cuidado: os filtros do artigo são de igualdade de rótulo, e ele não testa pgvector nem Qdrant.

## Backlinks
- [[../referência/bancos-de-dados-vetoriais]]
- [[Patel-2024-ACORN]]
