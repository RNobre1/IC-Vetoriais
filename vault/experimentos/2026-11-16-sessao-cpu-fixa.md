---
tipo: experimento
data: 2026-11-16
sistema: "pgvector, Qdrant, Weaviate"
cenário: "A, B (padrão e equalizado) e C"
dataset: "MS MARCO passages"
dataset_tamanho_n: [100000, 500000, 1000000]
tags: [sessão-final, escala-1m, cenario-c, recursos, reprodutibilidade, cpu-fixa, etapa-4]
status: vigente
---

# Experimento: sessão de medição final com a frequência da CPU fixa

## Objetivo

Produzir, numa única sessão, todos os valores do relatório final (Cenários A e B nas três escalas, Cenário C em 1M, custo de recursos por fase, cinco repetições no A), agora com a frequência da CPU fixa na base. Substitui [[2026-11-16-sessao-final]], cujos valores de velocidade foram contaminados pelo turbo dinâmico ([[../decisões/2026-11-16-frequencia-da-cpu-fixada]]).

## Configuração

- Sistemas e imagens: `pgvector/pgvector:0.8.2-pg18-bookworm`, `qdrant/qdrant:v1.17.1`, `semitechnologies/weaviate:1.37.2`.
- Hardware: Dell G15 5530, Fedora 44, kernel 7.1.5, na tomada, suspensão inibida. CPU fixa por `ic-cpu-fixa fixar`: turbo desligado, `min/max_perf_pct=100`, governor `performance`, tuned parado. P-cores a 2.400 MHz (12 threads), E-cores a 1.800 MHz (4). Perfil de plataforma `balanced`; RAPL 200/191/242 W.
- Fundo: GNOME Software e LocalSearch parados e mascarados durante a sessão; religados no fim.
- Embeddings: MiniLM-L6-v2, 384 dimensões, mesma base de [[../decisões/2026-11-16-procedencia-dos-embeddings-da-sessao-final]].
- HNSW: M = 16, ef_construction = 200, cosseno; ef_search ∈ {16, 32, 64, 128, 256}.
- Consultas: 1.000 held-out por escala, cliente único sequencial, 50 de aquecimento por bloco; Cenário A com 5 repetições.
- Protocolo: [[../decisões/2026-11-15-protocolo-da-sessao-final]], sem mudança; Cenário C: [[../decisões/2026-11-15-desenho-do-cenario-c]].

## Comando executado

```bash
cd code
systemd-run --user --unit=ic-sessao-cpu-fixa --collect make sessao SESSAO_ID=2026-11-16-cpu-fixa
```

Commit do código medido: `5e1a16e`. Os commits seguintes até a análise só acrescentaram comentários de marcação nos seeders e em `buscadores.py` (trechos do relatório), sem mudar comportamento. Dados: `code/results/cenario_*_2026-11-16T1[4-9]*.json`, `…T2*.json` e `code/results/sessoes/2026-11-16-cpu-fixa/` (commit `a19e501`).

## Execução

| Bloco | Duração | Swap-out do bloco |
|---|---|---|
| Ponte (A 100k, protocolo anterior) | 248 s | 0 |
| 100k pgvector / Qdrant / Weaviate | 342 / 431 / 1.405 s | 0 / 0 / 0 |
| 1M Qdrant / Weaviate / pgvector | 2.435 / 8.830 / 5.152 s | 0 / 811 MiB / 2,5 GiB |
| 500k Weaviate / pgvector / Qdrant | 4.204 / 2.343 / 1.091 s | 1 MiB / 10 MiB / 5 MiB |

Sessão de 11h31 a 18h54 de 16/11/2026 (7 h 23 min), dez blocos, nenhuma nova tentativa. Sem turbo, os blocos levaram cerca de 1,5 vez o tempo da sessão anterior.

## Verificações do hospedeiro

Saída completa em `code/results/sessoes/2026-11-16-cpu-fixa/verificacao_hospedeiro.txt`.

- Estado da CPU conferido no início e no fim dos 9 blocos de sistema: `no_turbo=1`, `perf 100/100`, `performance` em todos.
- Sonda de uma thread: 0,2411 a 0,2589 s (mediana 0,2438; desvio máximo 6,2%, nos fins de bloco logo após carga pesada; inícios de bloco dentro de 4,6%). Na sessão anterior: 0,128 a 0,262 s.
- `cpu_mhz_medio` do monitor nunca passou de 2.251 MHz; `throttle_total` ficou em 636 do início ao fim (na sessão anterior subiu de 685.026 para 1.833.583).
- `dnf-makecache` rodou duas vezes (11h52, 1 s, dentro do B do Weaviate em 100k; 15h02, 2 s, dentro do B equalizado do Weaviate em 1M), cobrindo 0,1% e 0,0% das fases, com +0,76 e +0,51 núcleo além da linha de base e PSI de E/S zero. Aceitas pela regra D10c.
- Controle do B padrão do Weaviate: atendido nos 10 pontos (|Δ| máximo 0,0037).

## Resultados

Valores nas tabelas geradas em `docx/relatorio_parcial/gerado/` (`make tabelas`) e interpretados no §5 do relatório final. Destaques:

- Índice em 1M: pgvector 4.171,5 s (69,5 min, 2,3 núcleos em média), Qdrant 420,8 s, Weaviate 298,9 s.
- Cenário A, ponto de recall ≥ 0,99: Weaviate o mais rápido nas três escalas (471,2 / 323,3 / 320,6 QPS); pgvector segundo em 100k (302,5) e último em 500k e 1M (185,1 em 1M).
- Amplitude da mediana de latência entre repetições: 1% a 48%, acima de 26% só em 2 dos 45 pontos (sessão anterior: 4% a 74%).
- Cenário B equalizado, p = 1%, 1M: pgvector 0,0692, Weaviate 0,4554, Qdrant 0,9994. Weaviate p = 100%: mediana de 614,32 ms.
- Cenário C, 1M: Qdrant e Weaviate sustentaram 1.000 ins/s; pgvector 80. Latência sobe com a taxa nos três (mediana e cauda); recall estável; visibilidade 100%; contagem final exata.
- Reprodutibilidade contra 23/08 (ef = 64): recall a menos de 0,0034; QPS com razão de 0,59 a 1,81.

## Observações

- A queda de latência sob escrita no Qdrant e no Weaviate vista na sessão anterior não se repete: com a frequência fixa, a mediana sobe com a taxa de escrita nos três sistemas. Era efeito do turbo.
- Concordância com a sessão anterior (verificação pedida pelo contraponto; fora do relatório): recall do Cenário A com diferença mediana de 0,001 e máxima de 0,0098 (pgvector 500k, ef = 16); B equalizado até 0,0152 (Weaviate 1%, 100k) — variação entre construções independentes do grafo, maior em ef baixo. Disco do pgvector idêntico; Weaviate até 11%; Qdrant não comparável. Memória do Weaviate em 1M: 3,9 GiB de RSS Δ (antes 4,5).
- O RSS Δ do pgvector em 1M (1.951,6 MiB) inclui páginas de arquivo ativas logo após o índice; a memória anônima nas consultas fica em dezenas de MiB.
- O índice do Qdrant ficou 44% mais lento sem turbo, o do Weaviate 27% e o do pgvector 23%; a razão pgvector/Weaviate em 1M quase não mudou (14,4 → 14,0).

## Próximos passos

- Replicação na máquina de trabalho (ARM64/macOS), com protocolo próprio.
- Sensibilidade a `maintenance_work_mem`, `max_parallel_maintenance_workers` e à varredura iterativa do pgvector.
- Sessão com turbo ligado e núcleos dedicados, para medir quanto da distância entre os sistemas depende do hospedeiro.

## Backlinks

- [[2026-11-16-sessao-final]]
- [[../decisões/2026-11-16-frequencia-da-cpu-fixada]]
- [[../decisões/2026-11-15-protocolo-da-sessao-final]]
- [[../lições/2026-11-16-frequencia-da-cpu-nao-controlada]]
- [[../sessões/2026-11-16]]
