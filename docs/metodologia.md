# Metodologia do projeto

Documento de referência do projeto de Iniciação Científica **"Comparação de Desempenho de Soluções de Bancos de Dados Vetoriais para Busca Semântica: uma análise entre pgvector e Bancos de Dados Especializados"**.

A fonte canônica do texto entregável é o projeto LaTeX em `docx/relatorio_parcial/`. Este documento registra as decisões que governam o código e os experimentos, para quem for ler o repositório sem o relatório em mãos.

## Identidade

- **Bolsista:** Rafael Nobre de Souza
- **Orientador:** Prof. Dr. Celson Pantoja Lima (UFOPA/IEG)
- **Instituição:** Universidade Federal do Oeste do Pará — Instituto de Engenharia e Geociências, Santarém-PA
- **Curso:** Bacharelado em Ciência da Computação

## Objetivo

Comparar experimentalmente PostgreSQL+pgvector contra bancos vetoriais especializados (Qdrant, Weaviate) em cenários de busca semântica e RAG. Métricas: latência (p50/p95/p99), throughput (QPS), recall@K contra busca exata, footprint de memória e disco, tempo de indexação.

## Estrutura do repositório

```
.
├── vault/     # notas de pesquisa em Markdown: fichamentos, decisões (ADR),
│              # experimentos, lições aprendidas, logs de sessão
├── code/      # docker-compose dos 3 SGBDs, pipeline de embeddings, benchmarks
├── data/      # datasets baixados (não versionado — volume e licença)
├── docs/      # este documento, planos de tarefa, relatórios de pesquisa
└── docx/      # entregáveis: projeto LaTeX do relatório + arquivos legados
```

Os papéis são separados de propósito: `vault/` é onde mora o raciocínio (backlinks entre notas são parte do método), `code/` é onde os experimentos rodam, `docx/` é o que se entrega.

## Decisões metodológicas firmes

Cada uma tem uma nota datada em `vault/decisões/`, no formato ADR (contexto, opções, decisão, justificativa, consequência, critério de revisão). Não são revisitadas sem motivo técnico forte.

| Decisão | Escolha |
|---|---|
| Sistemas avaliados | PostgreSQL+pgvector, Qdrant, Weaviate |
| Índice | HNSW nos três, com M=16 e ef_construction=200 — diferenças observadas refletem implementação e arquitetura, não algoritmo |
| Modelo de embedding | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensões), em CPU |
| Dataset | Subset determinístico de MS MARCO Passages (8.841.823 passages disponíveis) |
| Escalas | 100k, 500k e 1M embeddings |
| Cenários | A (busca pura), B (busca com filtros de metadados), C (carga mista RAG) |
| Ground truth | Busca exata via FAISS; no Cenário B, restrita ao subconjunto que satisfaz o filtro |
| Forma de reportar | Curvas recall × QPS, no espírito do ANN-Benchmarks — nunca números pontuais |
| Orçamento bibliográfico | 14 referências no parcial, ~20 no final |

### Equalização do Cenário B

Comparar busca vetorial com filtro exige que os três sistemas tratem o atributo de filtro da mesma forma. Qdrant e Weaviate trocam automaticamente HNSW por varredura exata quando o subconjunto elegível é pequeno (`full_scan_threshold` e `flatSearchCutoff`), o que produz `recall = 1,0` que mede o fallback e não a qualidade da busca aproximada. O Cenário B é executado em duas condições:

- **default** — cada sistema como vem de fábrica; responde "qual é o comportamento que o usuário encontra sem ajuste?";
- **equalizado** (`--equalizado`) — índice dedicado no atributo de filtro nos três e limiar de busca exata no mínimo, forçando HNSW em toda seletividade.

## Cronograma (Jan–Dez 2026)

A tabela canônica é a do relatório (`docx/relatorio_parcial/secoes/08-cronograma.tex`). As datas reais de execução ficam nas notas de `vault/sessões/` e `vault/experimentos/` — planejamento e execução são registros distintos e não devem ser confundidos.

| Etapa | Período | Conteúdo |
|---|---|---|
| 1 | Jan–Fev | Revisão bibliográfica e fechamento da metodologia |
| 2 | Mar–Abr | Docker Compose dos 3 SGBDs, pipeline de embeddings, scripts de benchmark |
| 3 | Mai–Jun | Experimentos fase 1: cenários A e B em 100k e 500k |
| — | **fim de Jul** | **Entrega do relatório parcial** (fecha Etapas 1–3) |
| 4 | Jul–Set | Experimentos fase 2: escala de 1M e cenário C de carga mista |
| 5 | Out–Dez | Análise e redação final |
| — | **Dez** | **Entrega do relatório final** (fecha Etapas 4–5) |

## Hardware

Notebook Dell G15 5530, Fedora Linux. Intel i5-13450HX (10c/16t, até 4,6 GHz), 16 GiB DDR5 4800 MHz, NVMe Kingston 1 TB, NVIDIA RTX 3050 6 GB. Os embeddings são gerados em CPU por decisão metodológica (reprodutibilidade em estações sem GPU).

Possível extensão para o Cluster HPC do IEG/UFOPA na etapa final, condicionada a viabilidade técnica e disponibilidade de acesso.

Desde 19/08/2026 o trabalho é conduzido em duas máquinas com papéis distintos: o Dell acima é a **máquina de referência** e produz todo número que entra em tabela do relatório; um MacBook Air M4 (ARM64, Docker sob VM) é a **máquina de trabalho** e cuida de código, testes, análise e redação. A separação preserva a homogeneidade de hardware afirmada no relatório. O procedimento operacional está em `docs/runbook-medicao-dell.md`; a comparação entre as duas arquiteturas, se realizada, será experimento próprio e declarado.

### Provisionamento dos contêineres

A partir de 23/08/2026 os três serviços sobem com `init: true`, e o do PostgreSQL também com `shm_size: 1gb`. As duas mudanças são de **provisionamento**, não de configuração do banco: nenhum parâmetro de índice (`m`, `ef_construction`), de memória de trabalho (`maintenance_work_mem`), de paralelismo ou de método de I/O foi alterado, e as imagens seguem as fixadas em maio de 2026.

O motivo do `init: true` é uma interação entre o contêiner e o healthcheck, não um defeito do SGBD. Sem um init, o postmaster ocupa o PID 1 do contêiner e, nessa posição, adota e recolhe todo processo órfão do namespace de PIDs — não apenas os filhos que ele mesmo criou. Sob carga pesada de escrita o `pg_isready` do healthcheck ultrapassa seu timeout de 3 s (os `fsync` de checkpoint medidos chegaram a 13 s), o Docker o mata, o órfão é reparentado ao PID 1, e o postmaster trata o PID desconhecido como filho que quebrou, derrubando o cluster: `untracked child process ... exited with exit code 2` — e 2 é justamente o código que o `pg_isready` retorna para "sem resposta". Medido em cargas de 500 mil linhas: 5 quedas em 27 cargas sem `init`, 0 em 15 com `init` e o healthcheck ligado. O defeito não é do pgvector — uma tabela `bytea` de mesmo volume quebrou na mesma taxa.

O `shm_size: 1gb` é folga de capacidade, e **não** foi a causa da queda. O Docker monta `/dev/shm` com 64 MB por default, e a construção paralela do índice HNSW aloca ali um segmento dimensionado por `maintenance_work_mem`: medidos 63.999.392 bytes do segmento mais 1.275.088 dos demais, contra um teto de 67.108.864 — 2,7% de folga. Essa margem estreita foi uma das hipóteses investigadas e foi **descartada por intervenção**: com `/dev/shm` ampliado para 1 GB e depois 3 GB, as quedas continuaram. O parâmetro permanece porque uma alocação insuficiente derruba o servidor em vez de degradar o índice em silêncio, e porque ou a alocação cabe — e o resultado é idêntico — ou o servidor cai.

**Efeito sobre a comparabilidade dos resultados.** Nenhuma das duas mudanças toca o caminho de código que constrói ou consulta o índice. A verificação empírica é consistente com isso: no Cenário A com `ef_search = 64`, o recall@10 medido no ambiente novo reproduz o de julho na terceira casa decimal em 500 mil vetores (pgvector 0,9745 contra 0,9753; Qdrant 0,9879 contra 0,9874; Weaviate 0,9620 contra 0,9592) e na quarta em 100 mil (0,9872 contra 0,9872; 0,9980 contra 0,9975; 0,9734 contra 0,9728). As latências, ao contrário do recall, não reproduzem com essa estabilidade — ver `vault/experimentos/2026-08-23-footprint-e-tempo-de-indexacao.md`.

**Limitação de registro.** O bloco `ambiente` dos JSONs de resultado identifica o sistema e a condição de equalização, mas não o provisionamento do contêiner. Portanto a distinção entre execuções anteriores e posteriores a esta data é dada pela data no nome do arquivo e por este documento, não pelo conteúdo do JSON. Registrar ambiente e máquina no próprio arquivo é trabalho previsto, necessário antes que resultados de máquinas diferentes coexistam no diretório.

Detalhamento em `vault/decisões/2026-08-22-medicao-de-footprint-e-tempo-de-indexacao.md` e `vault/lições/2026-08-23-correlacao-tratada-como-causa-provada.md`.

## Prática de desenvolvimento

- **TDD é inegociável**: nenhum código de produção nasce sem teste que falhe antes. A suíte cobre funções puras de métricas, ground truth, seeders e cenários de benchmark.
- **Fonte única**: quando um mesmo fato precisa existir em mais de um lugar, cria-se a fonte e derivam-se os demais, em vez de atualizar ponto a ponto.
- **Causa provada antes de conserto**: diante de defeito, investiga-se até a causa raiz antes de propor correção. Hipótese escrita, menor teste que a derrube.
- **Ambiente limpo antes de medir**: `make ui-down` e confirmação de que só os 3 SGBDs alvo estão de pé.
- **Commits pequenos e atômicos**, mensagens em PT-BR no imperativo.

## Reprodução

```bash
cd code
make deps           # venv + dependências pinadas
make up             # sobe os 3 SGBDs
make test-unit      # suíte unitária (sem Docker)
make test-integration
make bench-A N=100000 Q=1000 K=10 EF=16,32,64,128,256 WARMUP=50
make bench-B N=100000 Q=1000 K=10 EF=16,32,64,128,256 WARMUP=50 SEL=0.01,0.1,0.5,1.0 EQ=1
```

Os resultados saem em `code/results/` como JSON, versionados no repositório — são o dado que sustenta os números do relatório.
