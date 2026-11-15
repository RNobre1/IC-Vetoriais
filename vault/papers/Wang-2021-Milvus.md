---
tipo: paper
autores: ["Wang, J.", "Yi, X.", "Guo, R.", "Jin, H.", "Xu, P.", "Li, S.", "Wang, X.", "Guo, X.", "Li, C.", "Xu, X.", "Yu, K.", "Yuan, Y.", "Zou, Y.", "Long, J.", "Cai, Y.", "Li, Z.", "Zhang, Z.", "Mo, Y.", "Gu, J.", "Jiang, R.", "Wei, Y.", "Xie, C."]
ano: 2021
titulo: "Milvus: A Purpose-Built Vector Data Management System"
venue: "SIGMOD '21, p. 2614–2627"
tags: [vdbms, sistemas-especializados, arquitetura]
citacao_abnt: "WANG, J. et al. Milvus: a purpose-built vector data management system. In: Proceedings of the 2021 International Conference on Management of Data (SIGMOD '21). ACM, 2021. p. 2614–2627."
arquivo_local: ""
---

# Milvus: A Purpose-Built Vector Data Management System

Fichamento curto, feito em 15/11/2026 a partir do resumo e das seções consultadas para a ampliação da bibliografia do relatório final. Metadados conferidos em fonte primária. Título completo no PDF dos autores; o Crossref deposita só "Milvus".

## Síntese
Apresenta o Milvus e argumenta que estender um SGBD relacional com uma coluna vetorial (cita o PASE sobre PostgreSQL) não atende bem a dados vetoriais em larga escala e dinâmicos. Trata dados dinâmicos com árvore LSM e isolamento por snapshot, e descreve filtragem por atributos.

## Relevância para a IC
Sustenta a contraposição entre sistemas estendidos e especializados que organiza o estudo (§3.4). O Milvus ficou fora dos sistemas avaliados ([[../decisões/2026-04-28-sistemas-avaliados]]) e aparece como trabalho futuro.

## Backlinks
- [[../referência/bancos-de-dados-vetoriais]]
- [[Pan-Wang-Li-2023-Survey-VDBMS]]
