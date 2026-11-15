---
tipo: paper
autores: ["Subramanya, S. J.", "Devvrit", "Kadekodi, R.", "Krishnaswamy, R.", "Simhadri, H. V."]
ano: 2019
titulo: "DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node"
venue: "NeurIPS 2019"
tags: [ann, indice-em-disco, memoria, trabalhos-futuros]
citacao_abnt: "SUBRAMANYA, S. J. et al. DiskANN: fast accurate billion-point nearest neighbor search on a single node. In: Advances in Neural Information Processing Systems 32 (NeurIPS 2019). Vancouver, 2019."
arquivo_local: ""
---

# DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node

Fichamento curto, feito em 15/11/2026 a partir do resumo e das seções consultadas para a ampliação da bibliografia do relatório final. Metadados conferidos em fonte primária. Ordem dos autores do PDF; a página do proceedings lista outra ordem. Páginas não constam do proceedings.

## Síntese
Observa que os índices ANN de ponta precisam ficar em memória principal, o que os encarece e limita o tamanho da coleção. Indexa um bilhão de pontos numa máquina com 64 GB de RAM e um SSD, mantendo grafo e vetores completos em disco e vetores comprimidos por quantização em memória.

## Relevância para a IC
Sustenta a direção futura de reduzir o custo de memória dos índices (§6), que no estudo aparece como o recurso mais desigual entre os sistemas.

## Backlinks
- [[../referência/busca-aproximada-vizinhos-proximos]]
