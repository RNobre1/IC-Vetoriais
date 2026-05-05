---
tipo: paper
autores: ["Patel, L.", "Kraft, P.", "Guestrin, C.", "Zaharia, M."]
ano: 2024
titulo: "ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data"
venue: "Proceedings of the ACM on Management of Data (PACMMOD)"
tags: [ann, hnsw, predicate, filtros, pacmmod]
citacao_abnt: "PATEL, L.; KRAFT, P.; GUESTRIN, C.; ZAHARIA, M. ACORN: performant and predicate-agnostic search over vector embeddings and structured data. Proceedings of the ACM on Management of Data (PACMMOD), v. 2, n. 3, art. 120, p. 1–27, 2024."
arquivo_local: "ACORN_ Performant and Predicate-Agnostic Search Over Vector_Embeddings and Structured Data.pdf"
---

# ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data

> **Status do fichamento:** preenchido a partir do título e do problema declarado. Conteúdo factual específico (algoritmo proposto, garantias formais, baselines, métricas reportadas) **deve ser extraído do PDF antes de qualquer citação no relatório**. Nada nas seções abaixo está validado contra o paper.

## Síntese
*[1–2 frases após leitura. O título sugere uma abordagem para combinar busca vetorial com filtros estruturados sobre metadados de forma "predicate-agnostic" — sem precisar conhecer os filtros antecipadamente nem reconstruir o índice por predicado.]*

## Contribuições
*[Extrair do PDF.]*

## Método
*[Extrair do PDF: descrição do algoritmo, modificações sobre HNSW (se aplicável), baselines comparados, datasets usados.]*

## Resultados-chave
*[Extrair do PDF: métricas reportadas (recall, QPS, memória) sob diferentes seletividades de predicado.]*

## Limitações
*[Extrair do PDF.]*

## Relevância para a IC
**Sustenta §3.4** ([[referência/bancos-de-dados-vetoriais]]) e fundamenta o desenho do **Cenário B** ([[decisões/2026-04-28-cenarios-A-B-C]]) — busca com filtros de metadados em diferentes seletividades. ACORN é a referência mais atual sobre o trade-off de filtros sobre vetores; deve ser usado para discutir o cenário B no relatório final, em particular para enquadrar os achados desta IC frente ao estado da arte da área.

## Citáveis
> *[Extrair do PDF: definição operacional de "predicate-agnostic" e crítica aos esquemas pre-filter/post-filter.]*

## Backlinks
- [[referência/bancos-de-dados-vetoriais]]
- [[decisões/2026-04-28-cenarios-A-B-C]]
- [[papers/Pan-Wang-Li-2023-Survey-VDBMS]]
