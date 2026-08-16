---
tipo: experimento
data: 2026-07-09
sistema: "pgvector, Qdrant, Weaviate"
cenário: "A (busca pura) e B (busca com filtro)"
dataset: "MS MARCO passages"
dataset_tamanho_n: 600000
tags: [etapa-3, cenário-a, cenário-b, 100k, 500k, hnsw, recall, qps]
---

# Experimento: Etapa 3 — Cenários A e B em 100k e 500k nos 3 SGBDs

> **Nota de proveniência.** Esta nota foi escrita em 2026-08-16, a partir dos JSONs em `code/results/` e dos scripts de execução. A execução ocorreu em 2026-07-09 e não foi registrada no dia. Tudo o que aparece como número aqui vem dos arquivos de resultado; o que veio do console daquele dia e não foi persistido está marcado como **não rastreável** e não deve ser citado no relatório.

## Objetivo

Produzir as curvas *recall* × QPS dos Cenários A e B nos três sistemas, em 100k e 500k embeddings, para fechar a Etapa 3 e sustentar a seção de resultados do relatório parcial.

## Configuração

- Sistemas: pgvector `0.8.2-pg18-bookworm`, Qdrant `v1.17.1`, Weaviate `1.37.2`
- Clientes: `psycopg 3.3.4` + `pgvector 0.4.2`, `qdrant-client 1.17.1`, `weaviate-client 4.21.0`
- Hardware: Dell G15 5530 — i5-13450HX (10c/16t), 16 GiB DDR5, NVMe 1 TB, Fedora
- Dataset: subset de MS MARCO passages; N = 100.000 e 500.000, mais 1.000 queries *held-out*
- Modelo: `all-MiniLM-L6-v2`, 384 dimensões, CPU
- HNSW: M = 16, `ef_construction` = 200, distância de cosseno nos três
- `ef_search` varrido em {16, 32, 64, 128, 256}; K = 10; warmup = 50
- Cenário B: seletividades p ∈ {0,01; 0,10; 0,50; 1,00}, predicado `seletor < p`
- *Ground truth*: FAISS exato; no Cenário B, top-K exato **dentro** do subconjunto filtrado

## Comando executado

Não foi usado o CLI canônico. A execução saiu de dois scripts avulsos, hoje preservados como registro em `code/experimentos/`:

```bash
python run_etapa3.py        # → experimentos/etapa3_run_100k_500k.py
python run_etapa3_final.py  # → experimentos/etapa3_run_500k_pos_fix.py
```

O segundo existe porque a carga de 500k no Qdrant estourou o timeout do `upsert(wait=True)`; o fix (`wait=False` + índice de payload com `timeout=120`) obrigou a retomar do Cenário A/Qdrant em diante. Vide [[../lições/2026-08-16-wait-false-sem-espera-de-indexacao]].

## Resultados — Cenário A (busca pura)

`recall@10` por `ef_search`, com p50 em ms e QPS:

| Sistema | N | ef=16 | ef=32 | ef=64 | ef=128 | ef=256 |
|---|---|---|---|---|---|---|
| pgvector | 100k | 0,9074 | 0,9597 | 0,9872 | 0,9976 | 0,9997 |
| Qdrant | 100k | 0,9659 | 0,9899 | 0,9975 | 0,9997 | 0,9999 |
| Weaviate | 100k | 0,8490 | 0,9276 | 0,9728 | 0,9903 | 0,9960 |
| pgvector | 500k | 0,8900 | 0,9444 | 0,9753 | 0,9900 | 0,9969 |
| Qdrant | 500k | 0,9444 | 0,9755 | 0,9874 | 0,9943 | 0,9987 |
| Weaviate | 500k | 0,8454 | 0,9179 | 0,9592 | 0,9782 | 0,9918 |

QPS de pico: Weaviate 1.157 (100k, ef=16) e 1.011 (500k, ef=32); pgvector 738 (100k, ef=32); Qdrant 430 (100k, ef=32).

Observações que se sustentam:

- **Weaviate domina throughput e latência absoluta** (p50 de 0,86 ms em 100k), ao custo do menor recall nos pontos iniciais.
- **Qdrant chega alto mais cedo** — 0,9659 já em ef=16 (100k) — com distribuição de latência bem concentrada (p99 ≈ p95).
- **pgvector escala pior**: em 500k, ef=256 custa p50 = 7,89 ms e derruba o QPS para 111, contra 282 do Qdrant e 431 do Weaviate.

## Resultados — Cenário B (busca com filtro)

Recorte em ef=64:

| Sistema | N | p=1% | p=10% | p=50% | p=100% |
|---|---|---|---|---|---|
| pgvector | 100k | 0,0593 | 0,6321 | 0,9788 | 0,9866 |
| Qdrant | 100k | 1,0000 | 1,0000 | 0,9692 | 0,9973 |
| Weaviate | 100k | 1,0000 | 1,0000 | 0,9843 | 0,9743 |
| pgvector | 500k | 0,0654 | 0,6200 | 0,9661 | 0,9732 |
| Qdrant | 500k | 1,0000 | 0,9960 | 0,9886 | 0,9933 |
| Weaviate | 500k | 1,0000 | 0,9166 | 0,9770 | 0,9630 |

**Estes números não comparam o que parecem comparar.** Vide [[../lições/2026-08-16-recall-1-0-era-fallback-full-scan]]:

1. Onde o recall é 1,0000 ele é *idêntico nos cinco `ef_search`* — é busca exata por fallback (`flatSearchCutoff` = 40000 no Weaviate; `full_scan_threshold` = 10000 KB no Qdrant), não qualidade de ANN filtrado.
2. O `seletor` recebeu tratamento desigual: índice de payload no Qdrant, indexação por padrão no Weaviate, **nenhum índice** no pgvector.

O que **sobrevive** como observação válida:

- A degradação do pgvector em p=1% (recall 0,059 em ef=64, subindo só até 0,265 em ef=256) é real e consistente nas duas escalas — comportamento de *post-filtering* sobre candidatos do HNSW.
- A latência do Weaviate no Cenário B cresce de forma aproximadamente linear com o número de elegíveis (100k: 1,7 ms → 32 ms; 500k: 5 ms → 158 ms) e é **insensível a `ef_search`**, indicando que o custo do filtro domina o da busca. Em p=100%/500k o Weaviate faz 5,4 QPS contra 974 no Cenário A — o mesmo sistema, a mesma base, com um filtro que aceita tudo.

## Não rastreável

Os tempos de geração de embeddings, tempos de *seed* e *footprint* de armazenamento foram impressos no console e **não persistidos** — o `etapa3_timings_remaining.json` previsto no script não existe em disco. Os valores que circularam no rascunho do relatório (812 s / 4.084 s de embeddings; seed de 97,6 s / 1.295,3 s no pgvector; 353,7 MB de footprint) não têm fonte verificável e foram retirados do texto. Precisam ser re-medidos com persistência antes de voltar.

## Observações

- `code/results/` estava no `.gitignore` — os dados brutos de todo o experimento nunca foram versionados. Corrigido em 2026-08-16.
- Anomalia de cold start: o **primeiro ponto medido de cada coleção** carrega latência muito acima dos demais (Weaviate 100k p=1% ef=16: p50 = 64,7 ms contra 1,7 ms em ef=32; pgvector 100k Cenário A ef=16: p99 = 28,6 ms contra 3,0 ms em ef=32). O warmup de 50 buscas não cobre o custo da primeira leitura do índice. O rascunho do relatório atribuía a cauda do pgvector a "contenção com o subsistema de transações do PostgreSQL" — explicação que não se sustenta, já que o efeito some nos pontos seguintes e não reaparece em 500k.

## Próximos passos

- [x] Contraprova do fallback de busca exata — [[2026-08-16-contraprova-full-scan]]
- [ ] Re-executar Cenário B com `--equalizado` nas duas escalas — [[../decisões/2026-08-16-equalizacao-cenario-b]]
- [ ] Re-medir tempos de seed e footprint com persistência em JSON
- [ ] Investigar o cold start e ajustar o protocolo de warmup (candidato a ADR)

## Backlinks

- [[../decisões/2026-08-16-equalizacao-cenario-b]]
- [[../decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]
- [[../decisões/2026-05-10-cenario-a-queries-warmup]]
- [[../lições/2026-08-16-recall-1-0-era-fallback-full-scan]]
- [[../lições/2026-08-16-wait-false-sem-espera-de-indexacao]]
- [[2026-05-10-validacao-embeddings-100-passages]]
