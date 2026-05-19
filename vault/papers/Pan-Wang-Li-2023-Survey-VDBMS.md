---
tipo: paper
autores: ["Pan, J. J.", "Wang, J.", "Li, G."]
ano: 2023
titulo: "Survey of Vector Database Management Systems"
venue: "arXiv:2310.14021 (Cornell University)"
tags: [vdbms, survey, sgbd, taxonomia]
citacao_abnt: "PAN, J. J.; WANG, J.; LI, G. Survey of Vector Database Management Systems. arXiv:2310.14021 (Cornell University), 2023."
arquivo_local: "Survey of Vector Database Management Systems.pdf"
---

# Survey of Vector Database Management Systems

> **Status do fichamento:** **verificado contra o PDF** em 2026-05-20 (lidas p. 1–3: resumo, introdução, arquitetura de VDBMS e classificação de sistemas; arXiv:2310.14021v1, 21 out. 2023). Autores conferidos: James Jie Pan, Jianguo Wang, Guoliang Li.

## Síntese
Survey abrangente de *Vector Database Management Systems* (VDBMS): mais de 20 sistemas comerciais surgidos em ~5 anos, impulsionados por LLMs/EBR. Organiza técnicas de processamento de consulta, armazenamento/indexação e otimização/execução, e caracteriza os sistemas existentes.

## Contribuições
- **Cinco obstáculos** centrais ao gerenciamento de dados vetoriais: (1) vagueza da similaridade semântica; (2) custo alto da comparação (O(D) por par); (3) tamanho grande dos vetores; (4) ausência de partição/ordem natural; (5) incompatibilidade entre índices de atributo e índices vetoriais (consultas *hybrid*).
- Taxonomia de índices: *table-based* (E²LSH, SPANN, IVFADC), *tree-based* (FLANN, RPTree, ANNOY) e *graph-based* (KGraph, FANNG, **HNSW** — "shown to perform empirically well with less theoretical understanding"); técnicas de quantização e partição navigable.
- Arquitetura de referência do VDBMS (query processor + storage manager); operadores de consulta híbrida (scan "block-first" e "visit-first").

## Método
Survey de literatura/sistemas. Tabela de *similarity scores* (inner product e cosine — range [−1,1]; Minkowski; Mahalanobis; Hamming), com custo O(D).

## Resultados-chave — classificação dos sistemas (relevante a §3.4)
**Correção de rigor:** o paper classifica os VDBMS em **TRÊS** categorias, não duas como o relatório dizia:
1. **native** — projetados especificamente para gestão vetorial (ex.: Vearch, Milvus, Manu);
2. **extended** — adicionam capacidade vetorial sobre um SGBD existente (ex.: AnalyticDB-V, PASE);
3. **search engines and libraries** — fornecem apenas capacidade de busca (ex.: Apache Lucene, Elasticsearch, Meta Faiss).
O resumo enfatiza o espectro *native* × *extended*; a terceira categoria é tratada à parte. **pgvector** = *extended* (extensão do PostgreSQL); **Qdrant/Weaviate** = *native*. O estudo foca nas duas primeiras.

## Limitações
Survey sem contribuição experimental própria; panorama de out/2023 — campo evolui rápido (versões podem estar defasadas em 2026).

## Relevância para a IC
**Sustenta §3.4** ([[referência/bancos-de-dados-vetoriais]]) — fundamenta o contraste "SGBD estendido (pgvector)" × "especializado/native (Qdrant, Weaviate)", eixo central da IC ([[decisões/2026-04-28-sistemas-avaliados]]). **Pendência corrigida no relatório:** o texto dizia "duas categorias arquiteturais principais"; foi ajustado para refletir a classificação tripla do paper, com o estudo focando nas duas primeiras.

## Citáveis
> "...a variety of VDBMSs across a spectrum of design and runtime characteristics, including 'native' systems that are specialized for vectors and 'extended' systems that incorporate vector capabilities into existing systems." (Resumo)
> "We classify existing VDBMSs into native systems which are designed specifically around vector management [...]; extended systems which add vector capabilities on top of an existing data management system [...]; and search engines and libraries..." (§1)

## Backlinks
- [[referência/bancos-de-dados-vetoriais]]
- [[decisões/2026-04-28-sistemas-avaliados]]
- [[papers/Jing-2024-LLMs-Meet-Vector-Databases]]
- [[papers/Patel-2024-ACORN]]
- [[papers/Malkov-Yashunin-2018-HNSW]]
