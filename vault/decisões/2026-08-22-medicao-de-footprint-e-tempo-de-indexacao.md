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

`docker stats --no-stream`, mesmo instrumento nos três contêineres, medido **duas vezes**: uma linha de base logo antes do seed e o valor final logo após o índice ficar utilizável. O que entra na comparação é o **delta**.

A primeira versão desta decisão registrava só o valor absoluto, com a ressalva de que ele não era atribuível ao dado medido. A tentativa de execução completa mostrou que a ressalva era fraca demais para o tamanho do problema. Ao final de duas escalas, o Weaviate estava com **6,1 GiB residentes** enquanto o Qdrant reportava 65 MiB — não porque um gaste cem vezes mais que o outro, mas porque o Weaviate mantém em RAM o grafo de **todas** as classes já criadas na instância (eram oito, de `bencha200` a `benchbeq500000`), ao passo que o Qdrant usa mmap e devolve ao sistema. Comparar os absolutos mediria o histórico do contêiner, não o custo do conjunto de dados.

Com 16 GiB no host, o efeito não ficou só na interpretação: sobraram 334 MiB de memória livre e o sistema entrou em 4,7 GiB de swap. Latência medida nesse estado não é dado.

> **Retificação (2026-08-23).** A primeira versão deste documento atribuía a essa exaustão a queda do backend do PostgreSQL durante um `CREATE INDEX ... USING hnsw`, observada no mesmo período. **A atribuição estava errada.** A queda se repetiu depois com 10 GiB disponíveis, swap sem crescimento e `oom_kill` em zero tanto no cgroup do contêiner quanto no host. Havia correlação temporal, e ela foi tratada como causa provada. A causa real está na seção "Memória compartilhada do contêiner", abaixo. O que permanece válido desta seção é o acúmulo de memória entre execuções, que foi medido e é o que justifica o reset — não a queda do PostgreSQL.

Duas consequências fixadas aqui:

1. **Toda sessão de medição começa de volumes zerados**, via `make reset-medicao`. Sem isso, cada execução herda a memória e o disco de todas as anteriores, e as medidas deixam de significar o mesmo entre a primeira e a última.
2. **Latência medida sob pressão de memória não é dado.** A rodada que expôs o problema foi descartada inteira, inclusive as duas execuções que haviam terminado com sucesso, porque rodaram enquanto o consumo crescia.

Mesmo com a linha de base, o delta continua **não** sendo "o custo de RAM do índice": inclui alocações de runtime do servidor durante a carga. É a melhor aproximação disponível com instrumento uniforme, e deve ser lido como ordem de grandeza.

### Memória compartilhada do contêiner (`/dev/shm`)

O backend do PostgreSQL caiu duas vezes durante `CREATE INDEX ... USING hnsw`, em 100 mil e em 500 mil, com a mensagem `server closed the connection unexpectedly` no cliente e `untracked child process ... exited with exit code 2` seguido de `reinitializing` no servidor. Não é erro de SQL: é um *worker* paralelo morrendo e derrubando o cluster.

A causa é de provisionamento do contêiner. O Docker monta `/dev/shm` com **64 MB** por default, e o PostgreSQL aloca ali a memória compartilhada dinâmica dos workers paralelos (`dynamic_shared_memory_type = posix`). A construção paralela do índice HNSW pede um segmento dimensionado por `maintenance_work_mem`, que nesta imagem é 64 MB.

Medido durante um build de 500 mil vetores:

| Item | Bytes |
|---|---|
| Segmento do build paralelo do HNSW | 63.999.392 |
| Outros três segmentos do PostgreSQL | 1.275.088 |
| **Total ocupado** | **65.274.480 (63.752 KB)** |
| Teto antigo de `/dev/shm` | 67.108.864 (65.536 KB) |
| **Folga** | **1.784 KB — 2,7%** |

Isso explica as três coisas que o diagnóstico anterior não explicava:

- **Por que "sempre funcionou".** Funcionava com 2,7% de folga. Nunca houve margem; havia sorte.
- **Por que era intermitente.** Qualquer alocação adicional de poucos MB transborda. Duas falhas em cerca de dez builds no mesmo dia, com o mesmo comando alternando entre sucesso e queda.
- **Por que falhou também em 100 mil.** O segmento é dimensionado por `maintenance_work_mem`, não pelo número de vetores. Confirmado por medição: o pico de `/dev/shm` durante o `bench-B` de 100 mil foi de **63.752 KB**, idêntico ao da escala de 500 mil. As duas escalas operavam com a mesma folga de 2,7%, e a escala nunca foi a variável relevante.

**Decisão:** `shm_size: 1gb` no serviço do PostgreSQL, em `code/docker-compose.yml`. A confirmação foi por intervenção de uma variável só — o mesmo `bench-A N=500000` que havia falhado duas vezes completou com código 0, e o `pg_stat_activity` mostrou o `CREATE INDEX` ativo enquanto `/dev/shm` marcava 62,3 MB.

Isto **não** é mudança metodológica: não toca em `m`, `ef_construction`, `maintenance_work_mem`, dataset, cenários nem métricas. É a diferença entre o experimento poder rodar e não poder. Os valores de recall reproduziram os de julho na terceira casa decimal (0,9733 contra 0,9753 no pgvector; 0,9891 contra 0,9874 no Qdrant), o que indica que o ambiente novo não deslocou a medição.

A partir daqui, o pico de `/dev/shm` é registrado por execução no log da sessão de medição, para que a folga deixe de ser invisível.

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
- O contêiner do PostgreSQL passa a subir com `shm_size: 1gb`. Toda medição daqui em diante é feita nesse ambiente, e o pico de `/dev/shm` é registrado por execução.
- O tempo de indexação passa a ser reportado **sempre** com o critério ao lado, no texto e na tabela.

## Critério de revisão

Reabrir se: (a) o Qdrant ou o Weaviate passarem a expor bytes de disco por coleção em API, o que tornaria o `du` desnecessário; (b) a comparação de arquitetura Dell × Mac avançar, já que o Docker sob VM no macOS mede I/O de outro jeito e o `du` dentro do contêiner pode não refletir o disco do hospedeiro; (c) o footprint virar métrica de primeira ordem no relatório final, caso em que vale medir com o volume zerado antes de cada carga, eliminando resíduo de execuções anteriores.

## Backlinks

- [[2026-08-16-equalizacao-cenario-b]]
- [[2026-08-19-divisao-de-maquinas-mac-dell]]
- [[../lições/2026-08-19-claim-de-instrumentacao-que-nao-existia]]
- [[../referência/metodologia-benchmarking-ann]]
- [[../referência/busca-aproximada-vizinhos-proximos]]
