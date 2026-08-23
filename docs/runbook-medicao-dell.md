# Runbook — execução de medições na máquina de referência

Procedimento operacional para produzir os dados de desempenho do projeto. Complementa `docs/metodologia.md`.

## Por que existe

O projeto passou a ser conduzido em duas máquinas com papéis distintos:

| Máquina | Papel | Responsabilidades |
|---|---|---|
| Dell G15 5530 / Fedora Linux (x86-64) | **máquina de referência** | executar benchmarks, versionar os JSONs brutos |
| MacBook Air M4 / macOS (ARM64) | **máquina de trabalho** | código, testes, análise, redação do relatório e do vault |

Todo número que entra em tabela do relatório é medido na máquina de referência. O relatório afirma, na Seção de Materiais e Métodos e nas Limitações, que os experimentos foram conduzidos em um único hardware; medir parte dos pontos em outra arquitetura invalidaria essa afirmação. A diferença entre as duas não é marginal — arquiteturas de instrução distintas, hierarquia de cache distinta, e no macOS o Docker executa dentro de uma máquina virtual, com penalidade de I/O ausente no Fedora.

A comparação entre as duas arquiteturas é desejável, mas como experimento próprio e declarado, com registro de decisão dedicado.

## Escopo da máquina de referência

**Faz:** sincronizar o repositório, preparar o ambiente, executar as medições, versionar os JSONs gerados, relatar anomalias factuais de execução (contêiner reiniciando, memória estourando, uso de swap, throttling térmico).

**Não faz:** interpretar resultados, editar o relatório em `docx/`, editar notas do vault, alterar parâmetros de índice, seletividades ou escalas, refatorar código de benchmark, reformatar arquivos.

O motivo da separação é operacional, não hierárquico. Dado bruto é commutativo: dois JSONs de execuções distintas convivem em qualquer ordem de merge. Interpretação não é: duas versões do mesmo parágrafo exigem alguém para decidir qual vale. Em julho de 2026 a ausência desse ponto único de decisão produziu um fork do relatório que quase levou uma referência duplicada para a entrega.

## Pré-condições

1. Repositório sincronizado com `main`.

   ```bash
   git checkout main && git pull
   ```

2. A instrumentação exigida pela medição precisa existir no `main`. Para a medição de footprint e tempo de indexação:

   ```bash
   grep -q "footprint" code/lib/reporting.py && echo OK || echo "instrumentação ausente"
   ```

   Se ausente, interromper. A instrumentação é escrita na máquina de trabalho, com testes, e chega por `git pull`. Não improvisar medição paralela nem reativar os scripts históricos de `code/experimentos/`, que nunca passaram por teste nem por lint e imprimiam apenas no console.

3. Ambiente isolado — apenas os três SGBDs alvo no ar.

   ```bash
   cd code
   make ui-down
   docker compose ps
   ```

   O Verba compartilha a instância do Weaviate e contamina a medição. Derrubar também qualquer outro contêiner pesado.

4. **Linha de base limpa — obrigatório antes de cada sessão de medição.**

   ```bash
   make reset-medicao
   ```

   O alvo é **destrutivo**: zera os volumes dos três SGBDs e sobe os contêineres de novo, esperando os três ficarem `healthy`. Não toca em `code/results/` nem no cache de embeddings de `data/`.

   O motivo é medido, não teórico. Os três sistemas acumulam as coleções de todas as execuções anteriores, e o Weaviate mantém o grafo HNSW de cada uma residente em memória. Numa tentativa de rodar as seis medições em sequência sem reset, ao fim da segunda escala o Weaviate estava com **6,1 GiB** residentes contra 65 MiB do Qdrant; o host de 16 GiB ficou com 334 MiB livres, entrou em 4,7 GiB de swap, e o backend do PostgreSQL foi derrubado no meio do `CREATE INDEX ... USING hnsw`. Sem o reset, a medição não só quebra: as que sobrevivem medem o histórico do contêiner e são cronometradas com a máquina em swap.

   Depois do reset, conferir que os três partiram do mesmo patamar:

   ```bash
   docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}'
   ```

   Esperado: dezenas de MiB em cada um. Centenas de MiB ou mais significa que o reset não surtiu efeito.

   Conferir também que o contêiner do PostgreSQL subiu com a memória compartilhada ampliada:

   ```bash
   docker exec ic-pgvector df -h /dev/shm
   ```

   Esperado: **1,0G**. Se aparecer 64M, o `shm_size` do compose não foi aplicado — não medir. O Docker monta `/dev/shm` com 64 MB por default, e a construção paralela do índice HNSW pede um segmento de 61 MB alocado ali (`dynamic_shared_memory_type = posix`, dimensionado por `maintenance_work_mem`). Com o default, o build rodava com 2,7% de folga e derrubava o servidor de forma intermitente, com `untracked child process ... exited with exit code 2` no log. Detalhes em `vault/decisões/2026-08-22-medicao-de-footprint-e-tempo-de-indexacao.md`.

5. Suíte unitária verde antes de medir.

   ```bash
   make up
   make test-unit
   ```

## Execução

Escalas e varrimento padrão de `ef_search` (`16,32,64,128,256`):

```bash
make bench-A N=100000 Q=1000 K=10
make bench-A N=500000 Q=1000 K=10
make bench-B N=100000 Q=1000 K=10
make bench-B N=100000 Q=1000 K=10 EQ=1
make bench-B N=500000 Q=1000 K=10
make bench-B N=500000 Q=1000 K=10 EQ=1
```

Regras de execução:

- **Um `make reset-medicao` antes de cada comando da lista acima**, não só no começo da sessão. As seis execuções criam coleções que ficam residentes, e a última rodaria em condição diferente da primeira.
- Acompanhar a memória do host durante a execução (`free -h`). Se o swap começar a crescer, **interromper**: latência medida sob swap não é dado, e as execuções afetadas precisam ser descartadas, inclusive as que terminarem sem erro.
- Sequencial, nunca em paralelo. A máquina fica reservada para a medição — sem navegador, sem compilação, sem outra carga.
- Ordens de grandeza de referência da última execução completa: o seed de 500 mil no pgvector leva cerca de 21 minutos; o Cenário B equalizado nas duas escalas levou 1h12min.
- `EQ=1` ativa a condição equalizada (índice dedicado no atributo de filtro e limiares de varredura exata no mínimo), conforme o registro de decisão de 2026-08-16.
- Falha no meio da execução: preservar o log completo, relatar, e não tentar consertar o código. Seguir para o próximo comando apenas se o anterior tiver gravado o JSON.

## Versionamento dos dados

Commitar exclusivamente os JSONs novos:

```bash
git status --short
git add code/results/*.json
git commit -m "chore(results): mede footprint e tempo de indexação em 100k e 500k"
git push
```

Se o `git status` mostrar qualquer arquivo que não seja JSON de resultado, não commitar — relatar antes.

Convenções de commit do projeto: mensagem em PT-BR, no imperativo, seguindo Conventional Commits, autoria única do bolsista.

## Relatório de execução

Ao final, registrar em texto (sem editar arquivos do repositório): comandos executados e quais falharam, tempo de parede de cada um, JSONs gerados com nome e tamanho, hash do commit e resultado do push, e anomalias observadas em descrição factual.

A análise dos números, a atualização do relatório e as notas do vault acontecem na máquina de trabalho, a partir dos JSONs versionados.

## Ponto de atenção — tempo de indexação

Tempo de indexação não é comparável ingenuamente entre os três sistemas. O pgvector constrói o índice depois da carga, em operação única e bloqueante (`CREATE INDEX ... USING hnsw`); Qdrant e Weaviate constroem de forma incremental e assíncrona, em paralelo com a inserção. Medir "tempo até o último insert retornar" favoreceria artificialmente os dois últimos. O relógio precisa parar quando o índice está de fato utilizável: no Qdrant, quando a coleção atinge o estado `green`; no Weaviate, quando a fila de indexação drena. Essa definição precisa estar registrada antes de o número entrar em tabela.
