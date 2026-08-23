---
tipo: experimento
data: 2026-08-23
sistema: "pgvector, Qdrant, Weaviate"
cenário: "A e B"
dataset: "MS MARCO passages"
dataset_tamanho_n: [100000, 500000]
tags: [footprint, indexação, recursos, etapa-4, reprodutibilidade]
---

# Experimento: footprint de disco e memória, tempo de indexação, e o que se aprende comparando duas execuções

## Objetivo

Fechar a lacuna do §4.4 do relatório parcial: medir e **persistir** disco, memória e tempo de indexação dos três SGBDs, em condição comparável, nas escalas de 100 mil e 500 mil vetores.

Um segundo objetivo surgiu na análise e não estava previsto: como a sessão reexecutou os Cenários A e B por inteiro, ela produziu uma **réplica independente** das curvas de julho e agosto. A comparação entre as duas execuções é resultado por si só, e está na seção "Reprodutibilidade".

## Configuração

- Sistemas: pgvector 0.8.2 (PostgreSQL 18), Qdrant 1.17.1, Weaviate 1.37.2 — imagens fixadas em [[../decisões/2026-05-06-bump-versoes-sgbds]], inalteradas.
- Hardware: Dell G15 5530, Fedora Linux (máquina de referência, conforme [[../decisões/2026-08-19-divisao-de-maquinas-mac-dell]]).
- Dataset: MS MARCO passages, subset determinístico dos N primeiros por `passage_id`.
- Modelo: `all-MiniLM-L6-v2`, 384 dimensões, normalizado em L2.
- HNSW: `M = 16`, `ef_construction = 200`, `ef_search ∈ {16, 32, 64, 128, 256}`.
- Provisionamento novo: `init: true` nos três serviços, `shm_size: 1gb` no PostgreSQL. Nenhum parâmetro de servidor sobrescrito — `maintenance_work_mem` e `io_method` nos defaults da imagem.
- Volumes zerados antes de cada uma das seis execuções.
- Concorrência: cliente único, sequencial (como em todas as execuções anteriores).

## Comando executado

```bash
make reset-medicao && make bench-A N=100000
make reset-medicao && make bench-A N=500000
make reset-medicao && make bench-B N=100000
make reset-medicao && make bench-B N=100000 EQ=1
make reset-medicao && make bench-B N=500000
make reset-medicao && make bench-B N=500000 EQ=1
```

18 arquivos em `code/results/`, sufixo `2026-08-23T*`. Tempo de parede total: 10.108 s (2 h 48 min).

## Resultados — recursos (Cenário A)

| Base | Sistema | Disco (MiB) | B/vetor | Heap / Índices (MiB) | RSS Δ (MiB) | Tempo até índice utilizável (s) | Carga (s) |
|---|---|---|---|---|---|---|---|
| 100k | pgvector | 353,7 | 3.709 | 156,2 / 197,4 | 130,9 | 81,9 | — |
| 100k | Qdrant | 307,9 | 3.229 | — | 127,9 | 26,3 | 18,3 |
| 100k | Weaviate | 274,3 | 2.877 | — | 617,2 | 16,9 | 16,9 |
| 500k | pgvector | 1.768,4 | 3.709 | 781,2 / 986,9 | 132,2 | 1.271,9 | — |
| 500k | Qdrant | 808,8 | 1.696 | — | 170,7 | 159,3 | 137,2 |
| 500k | Weaviate | 1.162,3 | 2.438 | — | 2.612,6 | 105,8 | 105,7 |

Referência: o vetor bruto de 384 dimensões em float32 ocupa 1.536 B, ou 146,5 MiB em 100 mil e 732,4 MiB em 500 mil.

Três leituras, com o que cada uma sustenta:

**Disco.** Razão sobre o dado bruto em 500 mil: pgvector 2,41×, Weaviate 1,59×, Qdrant 1,10×. No pgvector a decomposição está disponível e o índice HNSW (986,9 MiB) é **maior que a tabela que indexa** (781,2 MiB), porque guarda cópia própria de cada vetor. O Qdrant é o único cujo custo por vetor cai com a escala (3.229 → 1.696 B), sinal de componente não proporcional ao dado — os arquivos pré-alocados e o WAL que o `du` do diretório também conta. Essa decomposição **não foi feita**.

**Memória.** A coluna não ordena os três, e o motivo é mecânico: o Weaviate mantém o grafo no próprio heap e aparece inteiro no RSS; o Qdrant usa `mmap`; o PostgreSQL lê pelo `shared_buffers` de 128 MB e pelo page cache do hospedeiro, que não é RSS de processo algum. O que se sustenta é qualitativo: o Weaviate é o único que mantém o índice residente no processo, e ali o custo é uma ordem de grandeza acima dos demais.

**Tempo de indexação.** É a maior diferença de toda a comparação, e cresce com a escala: pgvector/Qdrant vai de 3,1× para 8,0×, e pgvector/Weaviate de 4,8× para 12,0×. No Qdrant a indexação em background responde por 14% do total (159,3 − 137,2 s). No Weaviate a fila drena em milissegundos, o que indica indexação **sincrônica** durante a importação nesta configuração — a espera pela fila, introduzida nesta sessão, custa nada aqui, mas é a única garantia de que o índice está completo.

## Reprodutibilidade entre execuções — o resultado não previsto

A sessão reexecutou o Cenário A completo (mesma configuração de julho) e o Cenário B nas duas condições (mesma configuração de 16/08). Comparando ponto a ponto:

| Grandeza | Comportamento entre execuções |
|---|---|
| recall@10, Cenário A | reproduz: desvio máximo 0,0113 em 30 pontos; em `ef ≥ 64`, ≤ 0,0028 |
| recall@10, Cenário B | reproduz: desvio máximo 0,0323 em 120 pontos, e ele cai em `ef = 16`, o ponto mais ruidoso |
| p50, p99, QPS | **não reproduz**: até 3,3× de diferença no mesmo ponto de operação |

O caso mais claro é pgvector, 100 mil, `ef = 16`: em julho, p50 de 1,20 ms, p99 de 28,59 ms e 417,8 QPS; nesta execução, p50 de 0,63 ms, p99 de **2,26 ms** e 1.369,4 QPS — com recall idêntico (0,9074 contra 0,9085).

Isso tem consequência direta sobre o §5.4 do relatório, que trata o p99 de 28,59 ms como ponto isolado e propõe aquecimento insuficiente como hipótese. A réplica **não reproduz o valor**, o que reforça a leitura de artefato ambiental e enfraquece a de característica do sistema. Mas não confirma a hipótese específica do aquecimento: o número de buscas de aquecimento foi o mesmo (50) nas duas execuções, e a variável que mudou foi o estado do hospedeiro, não o protocolo. A hipótese continua **não testada**; o que se aprendeu é que o valor não é reprodutível.

E aparece um novo ponto do mesmo tipo, em outro lugar: Weaviate, 500 mil, `ef = 64`, p99 de 33,38 ms nesta execução contra 1,82 ms em julho. Isso desfaz qualquer tentação de tratar a cauda como propriedade de um sistema específico.

**Leitura que se sustenta:** neste arnês de medição — cliente único, sequencial, 1.000 consultas por ponto, uma execução por configuração — o recall é reprodutível e a latência de cauda não é. Reportar p99 de execução única como característica do sistema não é defensável; para isso seria preciso repetir a execução e reportar dispersão. Isso é limitação do arnês, não dos sistemas, e reforça a razão de fundo da metodologia dos ANN-Benchmarks: a curva é o resultado, o ponto não é.

## Observações

**Pressão de memória em três execuções.** Swap-out de 912, 694 e 209 MB, todas na escala de 500 mil; as outras três em zero. Verificação durante uma delas: os processos com páginas em swap eram do ambiente gráfico (`gnome-software`, `dnf5daemon`), não os SGBDs, e `vmstat` mostrava `so = 0` nas amostras. **Não foi determinada a fase** em que o swap-out ocorreu. Fica como ressalva declarada. Note que o critério do próprio ADR — "latência medida sob pressão de memória não é dado" — foi aplicado com rigor menor aqui que na rodada de 22/08, que foi descartada inteira; a diferença é de magnitude (4,7 GiB de swap contra centenas de MB) e de quem estava em swap, mas a fronteira não está quantificada.

**Três arquivos descartados por evidência interna.** Medidos sob `maintenance_work_mem` de 2 GB e identificados pelo campo `recursos.configuracao`, removidos antes do commit. O campo cumpriu exatamente a função para a qual foi criado.

**O dado colateral que fica em aberto.** O mesmo build de índice de 100 mil levou 28 s com `maintenance_work_mem` de 2 GB e 82 s no default de 64 MB — 2,9×. O número vem da medição descartada e **não está em arquivo versionado**, motivo pelo qual não entrou no relatório como valor. O que entrou é a ressalva qualitativa: o tempo do pgvector reflete um default herdado da imagem, enquanto Qdrant e Weaviate constroem com defaults dimensionados para a tarefa. Quantificar isso é experimento próprio, barato (100 mil, dois valores do parâmetro) e recomendado antes do relatório final.

**`green` do Qdrant.** Entre 0,16% e 3,74% dos vetores permanecem fora do HNSW por efeito do `indexing_threshold` de 10.000 KB. Qualifica recall e latência, não só footprint. Efeito quantitativo **não medido**. Detalhe em [[../decisões/2026-08-22-medicao-de-footprint-e-tempo-de-indexacao]].

**O bloco `ambiente` dos pontos não identifica máquina nem provisionamento** — só `sistema` e `equalizado`. Enquanto houver uma máquina só, a data no nome do arquivo desambigua. A partir do experimento de portabilidade, não desambigua mais, e o campo tem de existir **antes** do primeiro arquivo da segunda máquina.

## Desdobramento no relatório

Decidido em 23/08: as quatro tabelas de latência e recall migraram para esta execução, que passa a ser a **única** fonte dos números do relatório. Antes, as Tabelas 4 e 5 comparavam as duas condições do Cenário B com cinco semanas de distância entre elas — a condição padrão vinha de 09/07 e a equalizada de 16/08 —, o que é exatamente o eixo daquelas tabelas. Os 100 números das quatro tabelas foram conferidos por script contra os JSONs.

Três conclusões do texto mudaram com a migração, e vale registrar porque nenhuma delas é cosmética:

1. **O limiar de recall 0,99 no Cenário A** deixa de ser "os três com `ef ≥ 128`" e passa a diferir por sistema: 64 no Qdrant, 128 no pgvector e 256 no Weaviate em 100 mil; 128 no Qdrant e 256 nos outros dois em 500 mil. O Weaviate em 100 mil ficava em 0,9903 na execução de julho e em 0,9896 nesta — atravessou o limiar por 7 décimos de milésimo, o que é ilustração do próprio ponto sobre reportar curvas e não números pontuais.
2. **Nenhum sistema é o mais rápido nas duas escalas.** O texto antigo dizia que o Weaviate tinha as menores latências e o maior throughput; nesta execução, em 100 mil o pgvector tem a menor mediana (0,63 ms) e o maior throughput (1.369,4 QPS) no ponto inicial. Em 500 mil a posição volta ao Weaviate.
3. **O parágrafo da cauda foi reescrito** com a não-reprodutibilidade como resultado declarado, e a hipótese de aquecimento passou a constar explicitamente como não testada.

Também foi corrigido um claim falso encontrado na verificação, e ele já era falso nos dados antigos: o texto afirmava que a ordenação Qdrant > Weaviate > pgvector se repetia nos cinco valores de `ef_search` sob seletividade restritiva. Em `p = 10%` e `ef = 256` o pgvector passa o Weaviate, nas duas escalas e nas duas execuções.

## Próximos passos

- Acrescentar máquina e arquitetura ao bloco `ambiente`, antes do experimento de portabilidade.
- Experimento próprio de sensibilidade do tempo de indexação do pgvector a `maintenance_work_mem`. Decidido em 23/08 **não** fazer agora: fica a ressalva qualitativa no relatório.
- Repetir cada configuração e reportar dispersão de latência, em vez de valor único, na segunda fase. Passou a ser requisito declarado no §5.5.

## Backlinks

- [[../decisões/2026-08-22-medicao-de-footprint-e-tempo-de-indexacao]]
- [[../decisões/2026-08-19-divisao-de-maquinas-mac-dell]]
- [[../sessões/2026-08-23-execucao-medicao-footprint]]
- [[../lições/2026-08-23-correlacao-tratada-como-causa-provada]]
- [[2026-08-16-cenario-b-equalizado]]
- [[2026-07-09-etapa3-cenarios-a-b]]
