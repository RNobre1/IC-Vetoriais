---
tipo: experimento
data: 2026-08-16
sistema: "Qdrant, Weaviate"
cenário: "B (busca com filtro) — contraprova de mecanismo"
dataset: "MS MARCO passages"
dataset_tamanho_n: 100000
tags: [contraprova, cenário-b, full-scan, flat-search-cutoff, hnsw, rigor]
---

# Experimento: o `recall = 1,0` do Cenário B é fallback para busca exata?

## Objetivo

Decidir, no hardware do projeto, se o `recall@10 = 1,0000` observado em Qdrant e Weaviate nas seletividades baixas da Etapa 3 vem do fallback documentado para varredura exata, e não da qualidade da busca aproximada com filtro.

## Hipótese e predição falseável

**Hipótese:** os dois sistemas trocam HNSW por varredura exata quando o subconjunto elegível é pequeno — `full_scan_threshold` (Qdrant, default 10000 KB) e `flatSearchCutoff` (Weaviate, default 40000 objetos).

**Predição:** zerando esses limiares, o recall deve **deixar de ser exatamente 1,0000** e voltar a crescer com `ef_search`. Se permanecer plano em 1,0, a hipótese está errada.

O critério é a *forma* da curva, não o valor absoluto: recall que não responde a `ef_search` não pode vir de percurso de grafo.

## Configuração

- Sistemas: Qdrant `v1.17.1`, Weaviate `1.37.2` (pgvector fora — não tem o mecanismo sob teste)
- N = 100.000; 200 queries *held-out*; K = 10; warmup = 20
- `ef_search` ∈ {16, 256} — só os extremos bastam para detectar curva plana
- Seletividades p ∈ {0,01; 0,10} → 1.000 e 10.000 elegíveis, ambas abaixo do corte de 40.000 do Weaviate
- Duas condições por sistema: limiar **default do servidor** e limiar **mínimo**

## Comando executado

```bash
./.venv/bin/python -m experimentos.contraprova_full_scan
```

## Resultados

| Sistema | Condição | p | recall ef=16 | recall ef=256 | Veredito |
|---|---|---|---|---|---|
| Qdrant | default | 1% | 1,0000 | 1,0000 | plano → **exata** |
| Qdrant | default | 10% | 1,0000 | 1,0000 | plano → **exata** |
| Qdrant | mínimo | 1% | 0,9970 | 1,0000 | cresce → HNSW |
| Qdrant | mínimo | 10% | **0,8755** | 1,0000 | cresce → HNSW |
| Weaviate | default | 1% | 1,0000 | 1,0000 | plano → **exata** |
| Weaviate | default | 10% | 1,0000 | 1,0000 | plano → **exata** |
| Weaviate | mínimo | 1% | **0,4005** | 0,7455 | cresce → HNSW |
| Weaviate | mínimo | 10% | 0,7830 | 0,9760 | cresce → HNSW |

**Predição confirmada nos 4 pares.** Com o limiar no default, recall plano em 1,0000; com o limiar no mínimo, o recall despenca e volta a responder a `ef_search`.

## Observações

1. **O resultado é mais forte que o previsto.** Esperava-se degradação; o que apareceu foi colapso. O Weaviate com filtro de 1% e `ef = 16` entrega **recall 0,4005** — menos da metade dos vizinhos corretos. Em `ef = 256` ainda fica em 0,7455. O sistema que o rascunho do relatório apontava como melhor em filtros restritivos é, quando obrigado a fazer busca aproximada, o pior dos três nesse regime.

2. **O Qdrant sustenta bem.** Mesmo forçado a HNSW, entrega 0,9970 em p=1% já com `ef = 16`. A vantagem do Qdrant em busca filtrada é real e sobrevive à contraprova — ao contrário da do Weaviate.

3. **O Qdrant rejeita `full_scan_threshold = 0`** com HTTP 422 (*"must be 10 or larger"*), ao contrário do Weaviate, cuja documentação recomenda `flatSearchCutoff: 0`. A primeira execução morreu exatamente aí. O mínimo aceito, 10 KB, equivale a ~7 vetores de 384 dimensões — na prática, HNSW sempre. Constante `FULL_SCAN_MINIMO` em `seeders/qdrant_seeder.py`, com teste de regressão.

4. **A latência do Weaviate não é explicada pelo modo de busca.** Em p=1%, os p50 são praticamente iguais nas duas condições (75,7 ms no default contra 73,3 ms com HNSW forçado). O custo dominante é a avaliação do filtro, não a busca — o que também explica por que, no Cenário B da Etapa 3, a latência crescia linearmente com o número de elegíveis e ignorava `ef_search`.

## Próximos passos

- [x] Registrar a lição — [[../lições/2026-08-16-recall-1-0-era-fallback-full-scan]]
- [ ] Re-run equalizado completo do Cenário B (100k e 500k, 3 sistemas, 5 valores de `ef`, 1.000 queries) — [[../decisões/2026-08-16-equalizacao-cenario-b]]
- [ ] Reescrever a subseção do Cenário B no relatório com as duas condições

## Backlinks

- [[../decisões/2026-08-16-equalizacao-cenario-b]]
- [[../lições/2026-08-16-recall-1-0-era-fallback-full-scan]]
- [[2026-07-09-etapa3-cenarios-a-b]]
- [[../papers/patel2024acorn]]
