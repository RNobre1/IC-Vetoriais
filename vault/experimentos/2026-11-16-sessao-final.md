---
tipo: experimento
data: 2026-11-16
sistema: "pgvector, Qdrant, Weaviate"
cenário: "A, B (padrão e equalizado) e C"
dataset: "MS MARCO passages"
dataset_tamanho_n: [100000, 500000, 1000000]
tags: [sessão-final, escala-1m, cenario-c, recursos, reprodutibilidade, etapa-4]
status: anterior
vigente_em: "[[2026-11-16-sessao-cpu-fixa]]"
---

# Experimento: sessão de medição final (100k, 500k e 1M; Cenários A, B e C)

> **Substituída em 16/11/2026** pela sessão `2026-11-16-cpu-fixa` ([[2026-11-16-sessao-cpu-fixa]]). Durante esta sessão, um gerenciador de energia (auto-cpufreq) ligava e desligava o turbo conforme a carga, e a velocidade de uma *thread* variou cerca de 2× entre blocos. Latência, QPS e tempo de índice daqui não entram no relatório; recall, memória e disco continuam como dado datado. Decisão: [[../decisões/2026-11-16-frequencia-da-cpu-fixada]].

## Objetivo

Produzir, numa única sessão, todos os valores do relatório final: Cenários A e B nas três escalas, Cenário C em 1M, com custo de recursos por fase e repetição no Cenário A.

## Configuração

- Sistemas e imagens: `pgvector/pgvector:0.8.2-pg18-bookworm`, `qdrant/qdrant:v1.17.1`, `semitechnologies/weaviate:1.37.2` (sem mudança desde [[../decisões/2026-05-06-bump-versoes-sgbds]]).
- Hardware: Dell G15 5530, Fedora 44, kernel 7.1.5, governor `performance`, na tomada, suspensão inibida.
- Embeddings: MiniLM-L6-v2, 384 dimensões; base de 1M gerada na máquina de trabalho e verificada antes da medição ([[../decisões/2026-11-16-procedencia-dos-embeddings-da-sessao-final]]); 100k e 500k como prefixos do mesmo arquivo.
- HNSW: M = 16, ef_construction = 200, cosseno; ef_search ∈ {16, 32, 64, 128, 256}.
- Consultas: 1.000 held-out por escala, cliente único sequencial, 50 de aquecimento por bloco; Cenário A com 5 repetições.
- Protocolo: [[../decisões/2026-11-15-protocolo-da-sessao-final]]; Cenário C: [[../decisões/2026-11-15-desenho-do-cenario-c]].

## Comando executado

```bash
cd code
systemd-run --user --unit=ic-sessao-final --collect make sessao SESSAO_ID=2026-11-16-final
```

Commit do código medido: `e97b303`. Dados: `code/results/cenario_*_2026-11-16T*.json` e `code/results/sessoes/2026-11-16-final/` (commit `3c7b6b7`).

## Execução

| Bloco | Duração | Swap-out do bloco |
|---|---|---|
| Ponte (A 100k, protocolo anterior) | 161 s | 0 |
| 100k pgvector / Qdrant / Weaviate | 216 / 356 / 978 s | 0 / 1 MB / 22 MB |
| 1M Qdrant / Weaviate / pgvector | 1.829 / 5.379 / 4.256 s | 576 MB / 665 MB / 2,4 GB |
| 500k Weaviate / pgvector / Qdrant | 2.471 / 1.550 / 761 s | 5 MB / 64 MB / 0 |

Sessão de 02h39 a 07h40 de 16/11/2026, dez blocos, nenhuma nova tentativa. O swap concentrou-se em cargas e na preparação de dados; nas fases de medição, PSI de memória zero ou perto de zero, com um pico de 8,96% no Cenário A do pgvector em 500k.

## Resultados

Os valores estão nas tabelas geradas em `docx/relatorio_parcial/gerado/` (alvo `make tabelas`) e interpretados no §5 do relatório final. Destaques:

- Tempo de indexação em 1M: pgvector 3.393,6 s, Qdrant 291,7 s, Weaviate 235,8 s; o pgvector usou 1,8 núcleo em média na carga.
- Cenário A, ponto de recall ≥ 0,99: pgvector o mais rápido em 100k; o mais lento em 500k e 1M.
- Cenário B equalizado, p = 1%, 1M: pgvector 0,0694, Weaviate 0,4614, Qdrant 0,9989.
- Cenário C, 1M: Qdrant e Weaviate sustentaram 1.000 ins/s; pgvector, cerca de 97. Recall estável em todas as janelas; visibilidade 100%; contagem final exata nos três.
- Reprodutibilidade contra 23/08: recall a menos de 0,002; QPS com razão de 0,67 a 1,70.

## Observações

- **Controle do B padrão do Weaviate:** passou em 9 de 10 pontos; falhou em 500k, ef = 16 (|Δ| = 0,0121). Execução complementar logo após a sessão (`sessoes/2026-11-16-final/complementar/`), fora das tabelas: um terceiro grafo deu 0,7592, entre os dois valores — variância entre construções em ef baixo. As oito células omitidas em 500k (p = 50% e 100%, ef 16/32/128/256) ficaram a 0,0004–0,0040 do equalizado, cada seletividade num grafo à parte. Em 1M as células omitidas não foram medidas.
- **Latência cai sob escrita no Qdrant e no Weaviate** no Cenário C, junto com a subida da frequência média da CPU (1.961 → 2.933 MHz e 2.083 → 3.540 MHz). Hipótese de escalonamento de frequência, não testada com frequência fixa.
- **Disco do Qdrant** não proporcional e diferente de agosto em 500k (1.668,6 contra 808,8 MiB); a medida por diretório depende do estado dos segmentos.
- A amplitude da mediana de latência entre as cinco repetições chegou a 74%.

## Próximos passos

- Replicação na máquina de trabalho (ARM64/macOS), com protocolo próprio.
- Sensibilidade a `maintenance_work_mem` e à varredura iterativa do pgvector.
- Frequência de CPU fixada para testar a hipótese do Cenário C.

## Backlinks

- [[2026-08-23-footprint-e-tempo-de-indexacao]]
- [[../decisões/2026-11-15-protocolo-da-sessao-final]]
- [[../decisões/2026-11-15-desenho-do-cenario-c]]
- [[../decisões/2026-11-16-procedencia-dos-embeddings-da-sessao-final]]
- [[../sessões/2026-11-16]]
