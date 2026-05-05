---
tipo: decisão
data: 2026-04-28
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [metodologia, cenarios, workload]
---

# Cenários de avaliação: A (busca pura), B (com filtros), C (carga mista RAG)

## Contexto
Bancos vetoriais têm comportamentos distintos sob diferentes padrões de carga. Reportar apenas latência média de uma única consulta de similaridade pura mascara as diferenças que importam em produção (combinação com filtros estruturados e cargas de escrita concorrente). Precisamos definir cenários que cobrem o espectro real de uso.

## Opções consideradas
1. **Apenas busca pura**
   - Prós: simples, comparável com ANN-Benchmarks.
   - Contras: não responde a perguntas relevantes para sistemas de RAG em produção.
2. **Três cenários: A, B, C** (escolhido)
   - A: busca semântica pura.
   - B: busca com filtros de metadados (predicados estruturados).
   - C: carga mista — busca + ingestão concorrente, simulando RAG em operação.
   - Prós: cobre o trade-off entre simplicidade comparável e relevância prática.
   - Contras: triplica engenharia de scripts.
3. **Quatro+ cenários** (incluindo update-heavy, multi-tenant)
   - Prós: cobertura ainda maior.
   - Contras: prazo da IC não suporta sem cortar análise.

## Decisão
**Escolhida:** opção 2 — três cenários A, B, C.

## Justificativa
- **Cenário A** é a baseline canônica. Permite comparação direta com a literatura (ANN-Benchmarks, MTEB).
- **Cenário B** estressa a integração de busca vetorial com filtros sobre metadados — ponto onde pgvector tende a ter vantagem natural (planejador SQL maduro) e onde Qdrant/Weaviate competem com filtros nativos. Patel et al. (2024, ACORN) discutem precisamente esse cenário como subexplorado.
- **Cenário C** simula RAG em operação real: documentos novos chegam enquanto consultas são respondidas. Mede impacto de inserções sobre latência de consulta — métrica que ANN-Benchmarks ignora (assume índice estático).
- Os três cenários, juntos, sustentam a contribuição metodológica da IC (que vai além do que ANN-Benchmarks oferece).

## Consequência
- Etapa 3 (relatório parcial) cobre A e B em 100k e 500k.
- Etapa 4 (relatório final) cobre C em 1M e fecha A e B em 1M.
- Cada cenário tem seu próprio script de benchmark em `code/`.
- Métricas reportadas variam por cenário:
  - A: latência p50/p95/p99, QPS, recall@K, memória, disco.
  - B: idem A, mas com seletividade do filtro variando (1%, 10%, 50%, 100%).
  - C: latência p99 de consulta sob taxa de inserção variável (0, 10, 100, 1000 ins/s).

## Critério de revisão
Reabrir se algum dos sistemas não suportar nativamente o cenário B (filtros estruturados sobre vetores) — registrar como achado e adaptar protocolo. Cenário C requer suporte a carga concorrente confiável; se algum sistema travar, documentar como resultado.

## Backlinks
- [[papers/Patel-2024-ACORN]]
- [[papers/Aumuller-Bernhardsson-Faithfull-2020-ANN-Benchmarks]]
- [[referência/rag-retrieval-augmented-generation]]
- [[decisões/2026-04-28-tamanhos-100k-500k-1m]]
