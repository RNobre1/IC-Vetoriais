---
tipo: paper
autores: ["Patel, L.", "Kraft, P.", "Guestrin, C.", "Zaharia, M."]
ano: 2024
titulo: "ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data"
venue: "Proceedings of the ACM on Management of Data (PACMMOD)"
tags: [ann, hnsw, predicate, filtros, seletividade, pacmmod]
citacao_abnt: "PATEL, L.; KRAFT, P.; GUESTRIN, C.; ZAHARIA, M. ACORN: performant and predicate-agnostic search over vector embeddings and structured data. Proceedings of the ACM on Management of Data (PACMMOD), v. 2, n. 3, art. 120, p. 1–27, 2024."
arquivo_local: "ACORN_ Performant and Predicate-Agnostic Search Over Vector_Embeddings and Structured Data.pdf"
---

# ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data

> **Status do fichamento:** **verificado contra o PDF** em 2026-05-20 (lidas as p. 1–4: resumo, introdução, background HNSW, definição do problema e visão geral; versão arXiv:2403.04871v1, 7 mar. 2024, publicada na PACMMOD/SIGMOD 2024). Bibliografia conferida: autores, título e venue corretos.

## Síntese
Aborda *hybrid search*: busca ANN combinada com predicados estruturados ("similar a X **e** atributo=Y"). Propõe o ACORN, que estende o HNSW com *predicate subgraph traversal* para suportar conjuntos de predicados arbitrários e de alta cardinalidade (predicate-agnostic), superando as limitações de pré- e pós-filtragem e dos índices especializados de baixa cardinalidade.

## Contribuições
- Conceito de **predicate subgraph traversal**: a busca percorre o subgrafo do índice induzido pelos nós que passam o predicado, aproximando o "oracle partition index" (índice ideal hipotético) sem construí-lo.
- Dois índices: **ACORN-γ** (alto desempenho) e **ACORN-1** (menor custo de construção/TTI), ambos modificando o HNSW e fáceis de implementar sobre bibliotecas HNSW existentes.
- Construção predicate-agnostic (expansão/poda de vizinhos parametrizada por γ) que cria um grafo mais denso para navegar subgrafos arbitrários.

## Método
- Base: HNSW (grafo multinível, parâmetro M; busca controlada por *ef*). ACORN-γ usa fator de expansão de vizinhos γ; ACORN-1 aproxima ACORN-γ expandindo listas durante a busca.
- **Caracterização do problema (§3):** três características de workload governam o desempenho — **seletividade** s (fração das entidades que satisfazem o predicado, 0≤s≤1), **tamanho do dataset** e **query correlation**. Análise formal: pré-filtragem tem complexidade O(|Xp|)=O(sn+K) (escala mal em datasets grandes); pós-filtragem O(log n + K/s) no melhor caso, mas O(n) no pior sob correlação. Nenhum dos dois é robusto a variações de seletividade/correlação.
- Avaliação em 4 datasets: SIFT1M, Paper, LAION, TripClick (inclui predicados simples de baixa cardinalidade e datasets com milhões de predicados que métodos anteriores não suportam).

## Resultados-chave
- **ACORN-γ atinge 2–1.000× maior QPS a recall fixo (0,9)** vs. métodos anteriores (resumo e §5): >30× em benchmarks novos, >1.000× em escala (dataset de 25M vetores).
- ACORN-1 aproxima ACORN-γ: até 5× menor QPS a recall fixo, porém 9–53× menor TTI.

## Limitações
- Para queries de altíssima seletividade (subgrafo do predicado pode ficar desconectado no grafo ACORN), ACORN recai em pré-filtragem abaixo de uma seletividade mínima s_min configurável.
- Avaliação focada em HNSW (embora o framework de subgraph traversal seja generalizável a outros índices de grafo).

## Relevância para a IC
**Sustenta §3.4** ([[referência/bancos-de-dados-vetoriais]]) e fundamenta o desenho do **Cenário B** ([[decisões/2026-04-28-cenarios-A-B-C]] e [[decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]). É a base teórica de duas afirmações do relatório: (1) a taxonomia pré-/pós-/filtragem inline (§3.4); (2) que o **fator que governa o desempenho da busca filtrada é a seletividade do predicado, não a natureza semântica do atributo** (§4.2 — caráter predicate-agnostic). Ambas conferem com o paper (§3.1–3.2 formalizam seletividade; o título e a tese central estabelecem predicate-agnostic). Justifica a escolha metodológica desta IC de varrer seletividade (1/10/50/100%) com atributo sintético.

## Citáveis
> "ACORN achieves state-of-the-art performance on all datasets, outperforming prior methods with 2–1,000× higher throughput at a fixed recall." (Resumo)
> "Three commonly used methods are pre-filtering, post-filtering, and specialized data structures for low-cardinality predicate sets." (Introdução)
> "We refer to the selectivity (s) of predicate p as the fraction of entities from D that satisfy the predicate, where 0 ≤ s ≤ 1." (§3.1)

## Backlinks
- [[referência/bancos-de-dados-vetoriais]]
- [[referência/busca-aproximada-vizinhos-proximos]]
- [[decisões/2026-04-28-cenarios-A-B-C]]
- [[decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]
- [[papers/Pan-Wang-Li-2023-Survey-VDBMS]]
- [[papers/Malkov-Yashunin-2018-HNSW]]
