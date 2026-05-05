---
tipo: decisão
data: 2026-04-28
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [metodologia, ann, hnsw]
---

# Índice principal: HNSW nos três sistemas

## Contexto
A escolha do algoritmo de indexação é a variável mais sensível em benchmarks de bancos vetoriais. Sistemas diferentes oferecem famílias diferentes (HNSW, IVF, IVF-PQ, DiskANN, ScaNN). Para que a comparação entre pgvector, Qdrant e Weaviate seja interpretável, precisamos fixar a família do índice.

## Opções consideradas
1. **Cada sistema com seu padrão recomendado** (pgvector IVF-Flat ou HNSW; Qdrant HNSW; Weaviate HNSW)
   - Prós: reflete uso "out of the box".
   - Contras: a comparação mistura efeito de sistema com efeito de algoritmo. Inconclusivo.
2. **HNSW em todos** (escolhida)
   - Prós: isola o efeito de implementação. Diferenças observadas refletem arquitetura, código e parâmetros — não algoritmo.
   - Contras: pgvector com HNSW pode estar em desvantagem se a implementação for menos otimizada que as nativas. Esse próprio achado, se confirmado, é resultado relevante.
3. **Múltiplos índices por sistema**, comparando dentro e entre
   - Prós: cobertura completa.
   - Contras: explosão combinatória. Inviável em Mai–Dez com um bolsista.

## Decisão
**Escolhida:** opção 2 — HNSW como índice principal nos três sistemas.

## Justificativa
- HNSW é suportado nativamente por todos os três e é o índice mais usado na literatura recente para ANN em alta dimensionalidade (Malkov & Yashunin, 2018).
- Fixar o algoritmo isola a variável de interesse: a implementação do sistema.
- Aumüller, Bernhardsson e Faithfull (2020) mostram que HNSW é Pareto-dominante na fronteira recall × QPS para datasets densos similares ao alvo deste estudo.
- Parâmetros principais (M, efConstruction, efSearch) são comparáveis entre os três sistemas.

## Consequência
- Reportar parâmetros HNSW (M, efConstruction, efSearch) em cada experimento, em vault/experimentos/.
- A discussão de resultados precisa explicitar que **não estamos comparando HNSW com IVF**: estamos comparando três implementações de HNSW.
- Caso surja diferença grande de desempenho, parte da explicação está na implementação (linguagem, layout em memória, paralelismo) e não no algoritmo.

## Critério de revisão
Reabrir se: (a) algum dos três sistemas remover suporte a HNSW, ou (b) houver evidência de que a comparação só faz sentido com índices distintos (improvável dentro do escopo da IC).

## Backlinks
- [[papers/Malkov-Yashunin-2018-HNSW]]
- [[papers/Aumuller-Bernhardsson-Faithfull-2020-ANN-Benchmarks]]
- [[referência/busca-aproximada-vizinhos-proximos]]
- [[decisões/2026-04-28-sistemas-avaliados]]
