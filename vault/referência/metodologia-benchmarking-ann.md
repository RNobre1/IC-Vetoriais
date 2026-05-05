---
tipo: referência
conceito: "Metodologia de benchmarking para SGBDs e ANN"
tags: [benchmark, metodologia, latencia, throughput, recall]
---

# Metodologia de benchmarking

## Definição
Conjunto de práticas para medir desempenho de sistemas de banco de dados de forma **rigorosa, reprodutível e comparável**. No contexto desta IC, combina dois tradições: benchmarking clássico de SGBD (TPC-* benchmarks, micro-benchmarks de latência/throughput) e benchmarking de ANN (curvas Pareto recall × QPS, popularizadas por ANN-Benchmarks).

## Componentes obrigatórios

### 1. Reprodutibilidade
- Versão exata de cada componente (banco, driver, modelo de embedding) **pinada** em `requirements.txt`/`docker-compose.yml`.
- Seeds determinísticos para sampling, particionamento, shuffle.
- Hardware documentado (CPU, RAM, disco, kernel, distro).
- Configuração inteira do sistema (parâmetros padrão vs. customizados, com justificativa para cada desvio).

### 2. Métricas
- **Latência:** medir distribuições, não médias. Reportar **p50, p95, p99** (e p99.9 quando relevante).
- **Throughput (QPS):** sob carga sustentada, com warmup descartado.
- **Recall@K:** contra ground truth de busca exata sobre o mesmo conjunto.
- **Recursos:** memória residente (RSS), espaço em disco, tempo de indexação inicial.
- **Estabilidade:** múltiplas execuções (≥3), reportar mediana com intervalo (min, max ou IQR).

### 3. Protocolo
- **Warmup:** descartar primeiras N consultas para estabilizar caches (page cache do SO, buffer pool do banco).
- **Isolamento:** um sistema por execução, sem ruído de outros containers/processos. CPU governor em "performance" no Linux.
- **Carga realista:** distribuição de queries representativa, **não loop sobre uma única query** (que ficaria toda em cache).
- **Saturação:** rampa de concorrência crescente até throughput estabilizar ou degradar; reportar o **ponto de joelho** (knee point).

### 4. Apresentação
- **Curvas Pareto, não números pontuais** (Aumüller, Bernhardsson, Faithfull, 2020).
- Gráficos com eixos rotulados, escalas claras, intervalos.
- Comparação justa: mesmo dataset, mesmo K, mesma carga concorrente, mesma versão de driver.

## Onde aparece neste estudo
Seção §3.6. Esta nota é o **manual operacional** dos experimentos das Etapas 3 e 4 ([[decisões/2026-04-28-cenarios-A-B-C]]). Cada experimento em [[experimentos/]] precisa explicitar todos os pontos da seção "Componentes obrigatórios".

## Papers canônicos
- [[papers/Aumuller-Bernhardsson-Faithfull-2020-ANN-Benchmarks]]
- [[papers/Aerospike-2025-DB-Benchmarking-Best-Practices]]

## Pegadinhas
- **Single-client benchmarks subestimam latência real.** O sistema precisa ser medido sob concorrência ≥ 8 clientes para revelar contenção e fila.
- **Cache quente vs. frio:** publicar latência apenas em cache quente é prática comum mas enganosa. Reportar ambos quando a diferença for grande.
- **Resultados de fabricante** (na documentação oficial dos VDBMSs) tendem a usar configurações ideais não realistas. Não citar como ponto de comparação sem replicação local.
- **Tail latency (p99) é crítico em RAG:** usuários percebem o pior caso, não a média. Em latências de p50=10ms e p99=200ms, o impacto operacional vem do p99.
- **Cluster vs. nó único:** muitos sistemas brilham em cluster e ficam medianos em nó único. Esta IC mede em **nó único** (notebook), o que favorece sistemas mais leves.
- **Coleta de métricas custa:** instrumentação intrusiva (e.g. perf, strace) pode adicionar 5–15% de overhead. Validar o overhead da própria medição antes de reportar.
