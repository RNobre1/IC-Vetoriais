---
tipo: decisão
data: 2026-05-05
status: aceita
tags: [metodologia, benchmarking, infraestrutura, weaviate, verba]
relacionadas:
  - 2026-04-28-sistemas-avaliados
  - 2026-05-06-bump-versoes-sgbds
---

# ADR — Isolamento de ferramentas de UI vs ambiente de benchmark

## Contexto

Em 2026-05-05, ao discutir como inspecionar visualmente os 3 SGBDs (pgvector, Qdrant, Weaviate), surgiu a necessidade de uma GUI para o Weaviate (Qdrant tem dashboard nativo em `:6333/dashboard`; Postgres+pgvector usa DBeaver desktop). A opção escolhida para Weaviate foi o **Verba** (oficial Weaviate Inc., OSS) — rodando como container Docker.

Verba é útil tanto como explorador de coleções/objetos quanto como demo do cenário C (RAG) na Etapa 4. Porém: roda como container extra, com o próprio runtime Python e ~400 MB de RAM idle, e faz polling/HTTP cíclico contra Weaviate.

## Problema metodológico

Toda métrica de benchmark é sensível a ruído de ambiente. Aumüller, Bernhardsson & Faithfull (2020), em *ANN-Benchmarks: A benchmarking tool for approximate nearest neighbor algorithms* (Information Systems, vol. 87), são taxativos: **a máquina sob medição deve ter o mínimo absoluto rodando além do alvo**. Containers paralelos competem por:

- CPU (escalonamento e cache de instruções).
- IO de disco (mesmo containers idle gravam logs).
- Banda de memória (cache L3 contention).
- Rede local (Verba faz polling HTTP em Weaviate).

Em workstation de 16 GiB RAM + 10c/16t (ver `CLAUDE.md` → Hardware), com 3 SGBDs já carregados em paralelo, +400 MB de Verba pode mover p99 de latência em ordem de 5-15% — ruído suficiente pra contaminar comparações.

## Decisão

**Ferramentas de UI/inspeção (Verba e futuras) ficam num compose separado: `code/docker-compose.ui.yml`.** Targets `make ui-up` / `make ui-down` / `make ui-logs` no Makefile principal sobem/descem só essa parte. O compose principal `docker-compose.yml` permanece com os 3 SGBDs alvo da medição e mais nada.

**Regra de execução:** antes de qualquer benchmark (qualquer cenário, qualquer escala), executar `make ui-down` para garantir que nenhuma UI esteja rodando. Confirmação opcional via `docker compose ps` — só `ic-pgvector`, `ic-qdrant`, `ic-weaviate` devem aparecer.

## Opções consideradas

1. **Verba dentro do compose principal.** Rejeitada — viola o princípio de ambiente limpo durante medição, e exigiria lembrar de parar manualmente toda vez.
2. **Verba como container ad-hoc fora do compose.** Funcional, mas perde DNS interna (precisaria `host.docker.internal` ou `network_mode: host`) e bagunça reprodutibilidade. Compose é a ferramenta certa.
3. **Sem GUI, só Python REPL.** Pragmático, sem peso. Foi a recomendação inicial. Rejeitada quando o bolsista pediu UI explicitamente — mas continua sendo o fallback se Verba der problema.

## Consequências

- **Positivas:**
  - Ambiente de benchmark limpo por construção. Adicionar UIs futuras (e.g., pgAdmin, Adminer) só requer estender `docker-compose.ui.yml`.
  - Documenta-se a separação visualmente (dois arquivos de compose).
  - Compose merge é mecanismo Docker padrão, sem hack.
- **Negativas / custo:**
  - Bolsista precisa lembrar de `make ui-down` antes de medir. Mitigação: alvo de benchmark futuro pode chamar `ui-down` como pré-requisito.
  - Targets de Makefile crescem (de 11 para 14). Aceitável.

## Aplicação no código

- `code/docker-compose.ui.yml` — definição do serviço Verba.
- `code/Makefile` — variáveis `COMPOSE` / `COMPOSE_UI`, targets `ui-up`, `ui-down`, `ui-logs`.
- `code/.env.example` — `VERBA_PORT=8000` e chaves opcionais de LLM (comentadas).

## Backlinks

- [[../lições/2026-05-05-erro-recomendacao-weaviate-cloud-console]] — contexto de por que Verba é a solução para Weaviate self-hosted.
- [[2026-05-06-bump-versoes-sgbds]] — supersede a ADR original de versões; a imagem Weaviate atual (`1.37.2`) continua expondo gRPC em 50051. Verba conecta via REST (8080).
- [[2026-04-28-sistemas-avaliados]] — Weaviate é um dos 3 sistemas comparados.

## Referência metodológica

Aumüller, M.; Bernhardsson, E.; Faithfull, A. **ANN-Benchmarks: A benchmarking tool for approximate nearest neighbor algorithms.** *Information Systems*, vol. 87, p. 101374, 2020.
