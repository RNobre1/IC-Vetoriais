---
tipo: sessão
data: 2026-08-23
maquina: Dell G15 5530 / Fedora Linux (máquina de referência)
tags: [execução, footprint, indexação, etapa-4]
---

# Registro de execução — medição de footprint e tempo de indexação

Relatório de execução da máquina de referência, conforme [[../../docs/runbook-medicao-dell]]. Contém fatos de execução, não análise: a interpretação dos números e a tabela do §5.2 são trabalho da máquina de trabalho, a partir dos JSONs versionados.

## Ambiente

| Item | Valor | Verificação |
|---|---|---|
| Imagens | `pgvector/pgvector:0.8.2-pg18-bookworm`, `qdrant/qdrant:v1.17.1`, `semitechnologies/weaviate:1.37.2` | `docker compose ps` |
| `maintenance_work_mem` | 65536 kB (default da imagem) | gravado em `recursos.configuracao` nos 6 arquivos do pgvector |
| `io_method` | `worker` (default do PG18) | `pg_settings` |
| PID 1 dos contêineres | `docker-init` | `cat /proc/1/comm` |
| `/dev/shm` do pgvector | 1 GB | `df -h /dev/shm` |

As versões seguem as fixadas em [[../decisões/2026-05-06-bump-versoes-sgbds]]. Nenhum parâmetro de servidor foi sobrescrito.

## Execuções

Reset de volumes antes de cada comando. Total de parede: 10.108 s (2 h 48 min).

| # | Comando | Duração | Swap-out total | Pico por ciclo | `/dev/shm` pico |
|---|---|---|---|---|---|
| 1 | `bench-A N=100000` | 181 s | 0 MB | 0 MB | 63.752 KB |
| 2 | `bench-A N=500000` | 1.611 s | 912 MB | 186 MB | 63.752 KB |
| 3 | `bench-B N=100000` | 692 s | 0 MB | 0 MB | 63.752 KB |
| 4 | `bench-B N=100000 EQ=1` | 692 s | 0 MB | 0 MB | 63.752 KB |
| 5 | `bench-B N=500000` | 3.374 s | 694 MB | 249 MB | 63.752 KB |
| 6 | `bench-B N=500000 EQ=1` | 3.432 s | 209 MB | 51 MB | 63.752 KB |

18 JSONs gravados, todos com bloco `recursos` completo. Zero ocorrências de `untracked child process` no log do PostgreSQL durante a sessão.

## Anomalias observadas

**Pressão de memória nas execuções 2, 5 e 6.** Registraram swap-out de 912, 694 e 209 MB. As demais registraram zero. Verificação feita durante a execução 5: `vmstat` mostrava `so = 0` em todas as amostras, e os processos com páginas em swap eram do ambiente gráfico (`gnome-software`, `dnf5daemon`, um `MainThread` com 1,6 GB) — **nenhum dos três SGBDs**. Os contêineres somavam 2,7 GiB residentes.

**Não foi medido em qual fase o swap-out ocorreu**, carga ou medição. Fica como ressalva declarada; afirmar que foi inofensivo seria dedução.

**Conjunto de arquivos descartado.** Três JSONs de Cenário A 100k, gerados às 14:07:16 UTC sob `maintenance_work_mem` de 2 GB, foram identificados pelo campo `recursos.configuracao` e removidos antes do commit. Mesmo build medindo 28 s naquela configuração contra 82 s no default.

## Tentativas anteriores, todas descartadas

Nenhum JSON das tentativas abaixo foi commitado.

| Tentativa | Motivo do descarte |
|---|---|
| 2026-08-22, primeira | Host entrou em swap por acúmulo de coleções entre execuções; execuções bem-sucedidas descartadas junto |
| 2026-08-22, segunda | Queda do PostgreSQL; critério de watchdog estava errado (swap ocupado em vez de taxa) |
| 2026-08-23, manhã | Sucessivas quedas do PostgreSQL, causa ainda desconhecida |
| 2026-08-23, meio-dia | Medido sob `maintenance_work_mem` de 2 GB, depois revertido |

A causa das quedas está em [[../decisões/2026-08-22-medicao-de-footprint-e-tempo-de-indexacao]], seção "Por que o PostgreSQL caía": o postmaster rodava como PID 1 e adotava órfãos do namespace, e o healthcheck `pg_isready` morto por timeout sob carga era recolhido como filho que quebrou. Corrigido com `init: true`.

Os erros de método que alongaram a investigação estão em [[../lições/2026-08-23-correlacao-tratada-como-causa-provada]].

## Backlinks

- [[../decisões/2026-08-22-medicao-de-footprint-e-tempo-de-indexacao]]
- [[../decisões/2026-08-19-divisao-de-maquinas-mac-dell]]
- [[../lições/2026-08-23-correlacao-tratada-como-causa-provada]]
