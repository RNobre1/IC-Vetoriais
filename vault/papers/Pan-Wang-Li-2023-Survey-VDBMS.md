---
tipo: paper
autores: ["Pan, J.", "Wang, J.", "Li, G."]
ano: 2023
titulo: "Survey of Vector Database Management Systems"
venue: "arXiv (Cornell University)"
tags: [vdbms, survey, sgbd, taxonomia]
citacao_abnt: "PAN, J.; WANG, J.; LI, G. Survey of Vector Database Management Systems. arXiv (Cornell University), 2023."
arquivo_local: "Survey of Vector Database Management Systems.pdf"
---

# Survey of Vector Database Management Systems

> **Status do fichamento:** preenchido a partir do escopo do paper inferido pelo título e da posição central no relatório. Refinar todas as seções factuais (taxonomias, sistemas comparados, métricas) lendo o PDF antes de citar.

## Síntese
Survey abrangente de sistemas de gerenciamento de bancos vetoriais (VDBMS), caracterizando o espaço de soluções tanto em termos arquiteturais (extensão de SGBD relacional vs. nativos especializados) quanto em termos algorítmicos (HNSW, IVF, IVF-PQ, etc.). Serve como **mapa do território** desta IC e justifica a seleção dos três sistemas avaliados (pgvector, Qdrant, Weaviate) como representantes adequados das categorias descritas.

## Contribuições
- Taxonomia arquitetural dos VDBMS: **extensão de SGBD relacional** (ex.: pgvector) vs. **bancos vetoriais nativos** (ex.: Qdrant, Weaviate, Milvus).
- Mapeamento sistemático de algoritmos de indexação ANN (HNSW, IVF, IVF-PQ, ScaNN, DiskANN) e suas implementações nos sistemas comerciais e open-source.
- Discussão de desafios abertos: filtros estruturados sobre vetores, escala distribuída, atualizações dinâmicas.

## Método
Survey de literatura. *[Detalhar critérios de inclusão de sistemas, escopo temporal, taxonomia exata — extrair do PDF.]*

## Resultados-chave
*[Sintetizar a partir do PDF: comparativo de sistemas, gaps identificados, recomendações da survey.]*

## Limitações
- Como toda survey, congela um momento (2023). Sistemas evoluem rapidamente — versões dos sistemas comparadas podem estar desatualizadas em 2026.
- Escopo amplo limita profundidade em qualquer sistema individual.

## Relevância para a IC
**Sustenta §3.4 do relatório parcial** ([[referência/bancos-de-dados-vetoriais]]). Citado para:
1. Definir VDBMS como categoria.
2. Justificar a escolha dos três sistemas avaliados ([[decisões/2026-04-28-sistemas-avaliados]]) como representantes das duas grandes famílias arquiteturais.
3. Identificar os **gaps** que esta IC pretende preencher experimentalmente (filtros estruturados, carga mista).

## Citáveis
> *[Citar a taxonomia "extensão vs. nativo" e a definição operacional de VDBMS.]*

## Backlinks
- [[referência/bancos-de-dados-vetoriais]]
- [[decisões/2026-04-28-sistemas-avaliados]]
- [[papers/Jing-2024-LLMs-Meet-Vector-Databases]]
- [[papers/Patel-2024-ACORN]]
