---
tipo: paper
autores: ["Douze, M.", "Guzhva, A.", "Deng, C.", "Johnson, J.", "Szilvasy, G.", "Mazaré, P.-E.", "Lomeli, M.", "Hosseini, L.", "Jégou, H."]
ano: 2026
titulo: "The Faiss library"
venue: "IEEE Transactions on Big Data, v. 12, n. 2, p. 346–361"
tags: [ann, busca-exata, ground-truth, biblioteca]
citacao_abnt: "DOUZE, M. et al. The Faiss library. IEEE Transactions on Big Data, v. 12, n. 2, p. 346–361, 2026. DOI: 10.1109/TBDATA.2025.3618474."
arquivo_local: ""
---

# The Faiss library

Fichamento curto, feito em 15/11/2026 a partir do resumo e das seções consultadas para a ampliação da bibliografia do relatório final. Metadados conferidos em fonte primária. Metadados do periódico conferidos no Crossref; autores e título também no arXiv (2401.08281 v4). O README do projeto ainda indica o preprint.

## Síntese
Descreve a biblioteca Faiss de busca por similaridade em vetores densos: índices exatos e aproximados, compressão e a forma de avaliá-los. Define o recall de um índice aproximado como a fração dos vizinhos exatos (ground truth) presente entre os primeiros resultados, e implementa a busca exaustiva no `IndexFlat`.

## Relevância para a IC
Sustenta o ground truth exato do estudo, calculado com `IndexFlatIP` (§3.3 e §5). O artigo cita o `IndexFlat` de forma genérica; a variante de produto interno é detalhe da API.

## Backlinks
- [[../referência/busca-aproximada-vizinhos-proximos]]
