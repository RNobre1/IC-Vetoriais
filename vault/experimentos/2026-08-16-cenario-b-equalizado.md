---
tipo: experimento
data: 2026-08-16
sistema: "pgvector, Qdrant, Weaviate"
cenário: "B (busca com filtro) — condição equalizada"
dataset: "MS MARCO passages"
dataset_tamanho_n: 600000
tags: [etapa-3, cenário-b, equalizado, hnsw, filtros, recall]
---

# Experimento: Cenário B equalizado — 100k e 500k nos 3 SGBDs

## Objetivo

Medir a busca vetorial com filtro em condições comparáveis entre os três sistemas, eliminando as duas fontes de contaminação identificadas na auditoria: o *fallback* automático para varredura exata em Qdrant e Weaviate, e a assimetria de indexação do atributo de filtro. Vide [[../decisões/2026-08-16-equalizacao-cenario-b]].

## Configuração

Idêntica à execução de [[2026-07-09-etapa3-cenarios-a-b]] (mesmos vetores, mesmas queries, mesmo *ground truth* filtrado, M=16, ef_construction=200, K=10, 1.000 queries, warmup=50, `ef_search` ∈ {16,32,64,128,256}, p ∈ {0,01; 0,10; 0,50; 1,00}), com três mudanças:

| Sistema | Mudança |
|---|---|
| pgvector | `CREATE INDEX ... USING btree (seletor)` |
| Qdrant | `full_scan_threshold = 10` (mínimo aceito; o servidor rejeita 0) |
| Weaviate | `flatSearchCutoff = 0` |

Recursos com prefixo próprio (`bench_b_eq` / `BenchBEq`) e campo `equalizado` no JSON, para não colidir nem se confundir com a execução padrão.

## Comando executado

```bash
make bench-B N=100000 Q=1000 K=10 EF=16,32,64,128,256 WARMUP=50 SEL=0.01,0.1,0.5,1.0 EQ=1
make bench-B N=500000 Q=1000 K=10 EF=16,32,64,128,256 WARMUP=50 SEL=0.01,0.1,0.5,1.0 EQ=1
```

Duração total: 1h12min (14:39Z → 15:52Z).

## Resultados — recall@10 em ef=64, padrão × equalizado

| Sistema | p | 100k padrão | 100k equaliz. | 500k padrão | 500k equaliz. |
|---|---|---|---|---|---|
| pgvector | 1% | 0,0593 | 0,0591 | 0,0654 | 0,0659 |
| pgvector | 10% | 0,6321 | 0,6309 | 0,6200 | 0,6221 |
| pgvector | 50% | 0,9788 | 0,9788 | 0,9661 | 0,9671 |
| pgvector | 100% | 0,9866 | 0,9862 | 0,9732 | 0,9733 |
| Qdrant | 1% | **1,0000** | 1,0000 | **1,0000** | 0,9995 |
| Qdrant | 10% | **1,0000** | 0,9947 | 0,9960 | 0,9808 |
| Qdrant | 50% | 0,9692 | 0,9916 | 0,9886 | 0,9742 |
| Qdrant | 100% | 0,9973 | 0,9985 | 0,9933 | 0,9925 |
| Weaviate | 1% | **1,0000** | **0,5570** | **1,0000** | **0,5262** |
| Weaviate | 10% | **1,0000** | 0,9278 | 0,9166 | 0,9093 |
| Weaviate | 50% | 0,9843 | 0,9849 | 0,9770 | 0,9775 |
| Weaviate | 100% | 0,9743 | 0,9721 | 0,9630 | 0,9594 |

## Observações

### 1. A previsão do limiar absoluto acerta 8 de 8 séries do Weaviate

O `flatSearchCutoff` é absoluto (40.000 objetos), então a equalização deve mudar exatamente as séries com menos elegíveis que isso:

| N | p | Elegíveis | Previsão | Observado |
|---|---|---|---|---|
| 100k | 1% | 1.000 | muda | 1,0000 → 0,5570 ✓ |
| 100k | 10% | 10.000 | muda | 1,0000 → 0,9278 ✓ |
| 100k | 50% | 50.000 | não muda | 0,9843 → 0,9849 ✓ |
| 100k | 100% | 100.000 | não muda | 0,9743 → 0,9721 ✓ |
| 500k | 1% | 5.000 | muda | 1,0000 → 0,5262 ✓ |
| 500k | 10% | 50.000 | não muda | 0,9166 → 0,9093 ✓ |
| 500k | 50% | 250.000 | não muda | 0,9770 → 0,9775 ✓ |
| 500k | 100% | 500.000 | não muda | 0,9630 → 0,9594 ✓ |

O caso discriminante é p=10%: **muda** em 100k e **não muda** em 500k, mesma seletividade percentual. Só um limiar absoluto explica isso. O mecanismo está confirmado experimentalmente, não apenas por documentação.

### 2. O índice no atributo de filtro do pgvector não mudou nada

Hipótese inicial da auditoria: a ausência de índice em `seletor` no pgvector prejudicava a comparação. **Refutada.** Com B-tree, os valores ficam dentro do ruído em todas as 8 séries (maior diferença: 0,0654 → 0,0659). O gargalo do pgvector é a estratégia de *post-filtering* sobre os candidatos do grafo, não a avaliação do predicado. Registrar isso é mais útil que a suposição original — a assimetria existia, mas não era o fator.

### 3. O Qdrant piora levemente onde já usava HNSW

Em 500k, p=10% e p=50% — séries em que a condição padrão já apresentava recall variável com `ef` — o equalizado dá recall *menor* (0,9960 → 0,9808 e 0,9886 → 0,9742). Uma explicação compatível é que o Qdrant decide o modo de busca **por segmento**, de modo que a condição padrão resolveria parte dos segmentos por varredura exata mesmo com o total de elegíveis acima do limiar global. **Hipótese, não fato** — verificar exigiria instrumentar o plano de execução.

### 4. O custo de consulta do Weaviate sob filtro é independente do modo de busca

Em 500k, p=100%: 157,43 ms de mediana e 5,5 QPS na condição equalizada, contra valores da mesma ordem na padrão. O mesmo Weaviate, na mesma base, sem filtro (Cenário A), faz 0,89 ms e 974 QPS. A degradação não vem de qual busca é usada, e sim do custo de avaliar o predicado.

## Conclusão

Sob comparação equalizada, a ordenação em seletividade restritiva (p=1%) é **Qdrant ≫ Weaviate ≫ pgvector**, e não o empate perfeito entre os dois especializados que a execução padrão sugeria. A vantagem do Qdrant é real; a do Weaviate era artefato de configuração.

## Próximos passos

- [ ] Cenário C (Etapa 4) nasce já equalizado
- [ ] Instrumentar tempos de seed e footprint com persistência em JSON
- [ ] Investigar a hipótese de decisão por segmento no Qdrant (opcional, relatório final)

## Backlinks

- [[../decisões/2026-08-16-equalizacao-cenario-b]]
- [[2026-08-16-contraprova-full-scan]]
- [[2026-07-09-etapa3-cenarios-a-b]]
- [[../lições/2026-08-16-recall-1-0-era-fallback-full-scan]]
