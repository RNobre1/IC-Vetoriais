---
tipo: decisão
data: 2026-08-22
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [metodologia, footprint, indexação, instrumentação, comparabilidade]
---

# O que é comparável em disco, memória e tempo de indexação entre os três SGBDs

## Contexto

O §4.4 do relatório parcial lista "uso de recursos: memória e espaço em disco; tempo de indexação" entre as métricas do trabalho. Nenhuma tabela reporta esses valores. O §5.2 assume a lacuna explicitamente: a instrumentação da Etapa 3 imprimiu os números apenas na saída de console, sem persistir em arquivo, o que os torna não verificáveis a posteriori — e a regra do projeto é que número sem fonte versionada não entra no texto.

Fechar a lacuna não é só gravar em arquivo. Os três sistemas contabilizam armazenamento e constroem índice de maneiras diferentes, e **número incomparável é pior que número ausente**: a lacuna declarada é honesta, enquanto uma tabela que compara grandezas distintas sob o mesmo rótulo induz o leitor ao erro sem deixar rastro.

A abordagem histórica está em `code/experimentos/etapa3_run_100k_500k.py` (`_medir_footprint`, linha 38). Ela aproveita menos do que parece:

| Sistema | O que a função histórica devolvia | Serve como footprint? |
|---|---|---|
| pgvector | `pg_total_relation_size`, `pg_relation_size`, `pg_indexes_size` | sim |
| Qdrant | `points_count`, `segments_count`, `status` | **não** — contagem de objetos |
| Weaviate | `total_objects` | **não** — contagem de objetos |

Ou seja: dois dos três nunca mediram disco. Não havia medição de memória nem de tempo de indexação, e toda a coleta vivia dentro de um `try/except` que reduzia falha a uma linha de log.

## Opções consideradas

1. **Reportar o que cada sistema declara sobre si mesmo** — catálogo do Postgres, API de coleção do Qdrant, agregação do Weaviate.
   - Prós: usa o instrumento nativo, sem depender do contêiner.
   - Contras: Qdrant e Weaviate simplesmente não expõem bytes de disco por coleção nas APIs usadas. Restariam contagens de objeto, que não são footprint. Seria a lacuna com outro nome.
2. **Medir o volume inteiro de cada contêiner, antes e depois da carga** — mesmo instrumento para os três, resultado por diferença.
   - Prós: instrumento uniforme por construção.
   - Contras: os volumes hospedam todas as coleções de execuções anteriores ao mesmo tempo (hoje ~7,8 GB por volume), e a remoção de coleção não devolve espaço de imediato nos três. A diferença capturaria compactação em background e WAL de vizinhos.
3. **Medir o objeto medido, com o instrumento mais preciso que cada sistema oferece, declarando qual foi** — catálogo no pgvector, diretório da coleção nos outros dois.
   - Prós: mede a mesma grandeza física nos três (bytes persistidos para aquele conjunto de dados); isola o objeto sob medição do resto do volume.
   - Contras: instrumentos diferentes exigem que o arquivo diga qual produziu cada valor, sob pena de virar exatamente o número incomparável que se quer evitar.

## Decisão

**Escolhida: opção 3.** Cada medida viaja no JSON acompanhada do instrumento que a produziu e do critério que a encerrou.

### Disco

| Sistema | Instrumento | O que entra na conta |
|---|---|---|
| pgvector | `pg_total_relation_size(tabela)` | heap + TOAST + todos os índices da tabela |
| Qdrant | `du -sk` no diretório da coleção | segmentos, grafo HNSW, payload, WAL da coleção |
| Weaviate | `du -sk` no diretório da classe | shard: objetos, grafo HNSW, índices invertidos |

**Blocos alocados, não tamanho aparente.** Esta é a decisão mais consequente do documento, e foi tomada contra evidência medida, não por preferência. `du -sb` é `--apparent-size`: soma o tamanho declarado dos arquivos. O Qdrant pré-aloca arquivos esparsos de 32 MiB para WAL e `payload_storage`, então o aparente descola brutalmente do disco de fato ocupado:

| Coleção | Aparente (`du -sb`) | Alocado (`du -sk`) | Inflação |
|---|---|---|---|
| `bench_a_200` (200 vetores) | 587.471.615 B | 1.306.624 B | **450×** |
| `bench_a_100000` | 626.003.482 B | 222.875.648 B | 2,8× |

Medido com `--apparent-size`, uma coleção de 200 vetores — cerca de 300 KB de dado — apareceria com 560 MB. Weaviate e pgvector não usam arquivos esparsos: no Weaviate a classe de 100 mil dá 319,71 MB aparentes contra 319,75 MB alocados, e no diretório de dados do Postgres a diferença entre os dois é de 0,0003%. O erro atingiria **apenas o Qdrant**, que é justamente o sistema com o maior footprint na comparação — o efeito seria sistemático, não ruído.

O aparente continua sendo gravado, em `aparente_bytes`, para que a pré-alocação fique visível em vez de escondida. Ele não entra em tabela do relatório.

`du -sk` é usado no lugar de `du --block-size=1` porque o `du` da imagem do Weaviate é BusyBox v1.37 e não aceita a opção longa. `-sk` é POSIX e funciona nas duas imagens; a resolução de 1 KiB é irrelevante para grandezas de centenas de MB.

### Memória

`docker stats --no-stream`, mesmo instrumento nos três contêineres. O valor é **medida pontual do contêiner no instante da coleta**, não a memória atribuível ao conjunto de dados: inclui estruturas de servidor, conexões e cache. Comparável entre os três porque o instrumento e o instante relativo (logo após o índice ficar utilizável) são os mesmos; **não** interpretável como "custo de RAM do índice".

### Tempo de indexação

O relógio para quando o índice está **utilizável**, não quando a última escrita é aceita. Sem isso a comparação seria falsa por construção: o pgvector constrói o índice em operação única e bloqueante depois da carga, enquanto Qdrant e Weaviate aceitam as escritas e constroem o grafo em background.

| Sistema | Critério registrado | Como é verificado |
|---|---|---|
| pgvector | `create_index_retornou` | `CREATE INDEX ... USING hnsw` é bloqueante; o retorno do seed já é a condição |
| Qdrant | `colecao_status_green` | consulta a coleção até sair de `yellow` |
| Weaviate | `fila_vetorial_drenada` | shards **daquela classe** com `vectorQueueLength = 0` e `vectorIndexingStatus = READY` |

Onde a construção é separável da carga, os dois tempos são gravados: `tempo_carga_s` (até a última escrita aceita) e `tempo_indice_utilizavel_s` (até o índice pronto). A diferença entre eles é o custo da indexação assíncrona, que uma medição ingênua deixaria invisível. No pgvector `tempo_carga_s` é `null` — declarar a ausência é mais honesto que repetir o total e sugerir uma decomposição que não foi medida.

**Apenas `tempo_indice_utilizavel_s` é comparável entre os três.**

### O que `green` significa no Qdrant — e o que não significa

Ao verificar a primeira medição desta rodada, o Qdrant reportou `status: green` e `optimizer_status: ok` com **96.512 de 100.000 vetores indexados**. A checagem inicial foi se a indexação ainda estava em curso; não estava. Coleções semeadas em 2026-07-09, com seis semanas de idade e nenhuma escrita desde então, mostram a mesma fração fora do índice:

| Coleção | Pontos | Indexados | Fora do HNSW |
|---|---|---|---|
| `bench_a_500000` (jul) | 500.000 | 497.664 | 2.336 (0,47%) |
| `bench_b_500000` (jul) | 500.000 | 499.200 | 800 (0,16%) |
| `bench_b_100000` (jul) | 100.000 | 98.048 | 1.952 (1,95%) |
| `bench_b_eq_100000` (ago) | 100.000 | 96.256 | 3.744 (3,74%) |
| `bench_a_100000` (esta rodada) | 100.000 | 96.512 | 3.488 (3,49%) |

O mecanismo está na configuração da coleção, não em suposição: `optimizer_config.indexing_threshold = 10000` (KB). Segmentos cujo volume de vetores fica abaixo desse limiar não recebem índice HNSW — com 384 dimensões em float32 (1.536 B por vetor), 10.000 KB equivalem a ~6.667 vetores, o que explica os resíduos observados. É estado estacionário por projeto, não construção pendente.

Duas consequências, e vale separar o que está provado do que não está:

- **Para o tempo de indexação, `green` continua sendo o critério correto**: é quando o Qdrant considera a otimização encerrada, e esperar além disso seria esperar por algo que nunca acontece.
- **Para recall e latência, é uma limitação a declarar**: entre 0,16% e 3,74% dos vetores são respondidos por varredura dentro do próprio segmento, não pelo grafo. É a mesma família de artefato do `full_scan_threshold` ([[2026-08-16-equalizacao-cenario-b]]), porém de magnitude muito menor e sem produzir `recall = 1,0000` — não invalida as curvas publicadas. **Não foi medido** qual o efeito quantitativo dessa fração sobre o recall reportado; afirmar que é desprezível seria dedução, não resultado.

O `indexing_threshold` **não foi alterado**: mexer nele mudaria a configuração usada em todas as execuções anteriores e quebraria a comparabilidade com os 28 JSONs já versionados. Fica como candidato a experimento próprio, com decisão dedicada.

## Justificativa

O critério que organiza tudo acima é único: *a grandeza medida é a mesma nos três?* Bytes que o SGBD passou a ocupar em disco para armazenar e indexar aquele conjunto de dados é a mesma grandeza, ainda que lida por instrumentos diferentes — o catálogo do Postgres soma o comprimento dos arquivos daquela relação, e `du -sk` soma os blocos daquele diretório. Contagem de pontos não é essa grandeza, e por isso o que existia não servia.

A escolha de gravar instrumento e critério junto do número decorre da mesma lógica que já governa o `equalizado` no bloco `ambiente`: duas medições com o mesmo rótulo e procedências diferentes são indistinguíveis no diretório, e a ambiguidade só aparece meses depois, na hora de escrever a tabela.

A separação entre carga e índice utilizável é o ponto que a literatura de ANN trata como armadilha conhecida: sistemas com construção assíncrona parecem indexar instantaneamente se o relógio parar no retorno da escrita. É o mesmo tipo de artefato de configuração que derrubou a conclusão original do Cenário B ([[2026-08-16-equalizacao-cenario-b]]) — número plausível, produzido por um mecanismo diferente do que o leitor supõe.

## Consequência

- O bloco `recursos` passa a existir no JSON da curva, ao lado de `pontos`. Quando não há medida, a chave não é criada: ausência nunca vira `null` nem zero.
- Os 28 JSONs versionados continuam válidos e reproduzíveis byte a byte pelo código atual — há teste que os regrava e compara com o original.
- O seeder do Weaviate passa a aguardar a fila de indexação drenar, como o do Qdrant já aguardava o `green`. Isso corrige, de passagem, um defeito silencioso: antes, o CLI podia medir latência e recall sobre um índice pela metade.
- Números de disco produzidos com `du -sb` (incluindo qualquer anotação anterior a esta data) não são comparáveis com os novos e não devem entrar em tabela.
- O tempo de indexação passa a ser reportado **sempre** com o critério ao lado, no texto e na tabela.

## Critério de revisão

Reabrir se: (a) o Qdrant ou o Weaviate passarem a expor bytes de disco por coleção em API, o que tornaria o `du` desnecessário; (b) a comparação de arquitetura Dell × Mac avançar, já que o Docker sob VM no macOS mede I/O de outro jeito e o `du` dentro do contêiner pode não refletir o disco do hospedeiro; (c) o footprint virar métrica de primeira ordem no relatório final, caso em que vale medir com o volume zerado antes de cada carga, eliminando resíduo de execuções anteriores.

## Backlinks

- [[2026-08-16-equalizacao-cenario-b]]
- [[2026-08-19-divisao-de-maquinas-mac-dell]]
- [[../lições/2026-08-19-claim-de-instrumentacao-que-nao-existia]]
- [[../referência/metodologia-benchmarking-ann]]
- [[../referência/busca-aproximada-vizinhos-proximos]]
