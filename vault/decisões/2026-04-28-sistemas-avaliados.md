---
tipo: decisão
data: 2026-04-28
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [metodologia, sistemas, escopo]
---

# Sistemas avaliados: PostgreSQL+pgvector, Qdrant e Weaviate

## Contexto
A IC compara desempenho de soluções de armazenamento e busca de embeddings. O universo de candidatos relevantes em 2026 é amplo (Milvus, Pinecone, Chroma, Vespa, FAISS standalone, Elasticsearch+kNN, Redis VSS, etc.). Avaliar todos os sistemas seria inviável dentro do prazo do edital (Mai–Dez 2026) com um único bolsista.

## Opções consideradas
1. **Apenas pgvector vs. um especializado** (ex.: pgvector vs. Qdrant)
   - Prós: experimentos profundos, mais ablation study possível.
   - Contras: amostra fraca para sustentar conclusão geral sobre "relacional vs. especializado".
2. **pgvector + Qdrant + Weaviate** (escolhida)
   - Prós: representa o trade-off relacional (pgvector) vs. especializado em duas variantes arquiteturais (Qdrant Rust/foco em performance; Weaviate Go/foco em esquema e GraphQL).
   - Contras: triplica a engenharia de pipeline e seeders.
3. **pgvector + 3 ou mais especializados** (Qdrant, Weaviate, Milvus)
   - Prós: maior cobertura.
   - Contras: prazo do edital não suporta. Risco de ficar superficial.

## Decisão
**Escolhida:** opção 2 — pgvector, Qdrant e Weaviate.

## Justificativa
- pgvector é o caso "use o que você já tem" — reflete a decisão real de muitos times brasileiros que já operam PostgreSQL.
- Qdrant e Weaviate são os dois especializados open-source mais maduros em 2026, com licença permissiva, suporte nativo a HNSW e a filtros estruturados em metadados (necessário para o cenário B).
- Os três rodam em Docker no hardware-alvo (Dell G15, 16 GB) sem requerer GPU para o caminho de busca, o que viabiliza reprodução por terceiros.
- Survey de Pan, Wang e Li (2023) caracteriza pgvector e Qdrant/Weaviate como representantes das duas grandes famílias arquiteturais (extensão de SGBD vs. nativa). Manter um de cada lado dá amostra defensável.

## Consequência
- Pipeline de embeddings precisa de três adaptadores (um por sistema).
- Scripts de benchmark recebem flag `--system` para escolher o alvo.
- Comparação entre Qdrant e Weaviate é parte do estudo (não apenas pgvector vs. "um genérico").
- Milvus, Pinecone e Vespa ficam **fora de escopo** desta IC; podem ser citados na seção de trabalhos futuros.

## Critério de revisão
Reabrir se: (a) algum dos três sistemas se mostrar inviável de subir/operar no hardware-alvo dentro de Mai–Jun, ou (b) houver demanda do orientador para incluir um quarto sistema antes do relatório final.

## Backlinks
- [[papers/Survey of Vector Database Management Systems]]
- [[referência/bancos-de-dados-vetoriais]]
- [[decisões/2026-04-28-índice-hnsw-em-todos]]
