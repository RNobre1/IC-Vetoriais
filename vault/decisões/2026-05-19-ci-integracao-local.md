---
tipo: decisão
data: 2026-05-19
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [ci, github-actions, testes, integração, escopo]
---

# CI roda só unit+lint; testes de integração permanecem locais

## Contexto
O CI mínimo do Dia 1 (`.github/workflows/test.yml`) roda `ruff` + `pytest tests/unit` em push/PR para `main`. O plano da Etapa 2 deixou em aberto, para avaliar no Dia 4, se o workflow deveria ser ampliado para rodar os testes de **integração** (seeders, smokes de Cenário A/B) subindo os 3 SGBDs via `services:` do GitHub Actions.

## Opções consideradas
1. **Ampliar o CI com `services:` (pgvector + Qdrant + Weaviate)** — integração roda na nuvem a cada PR.
   - Prós: pega regressão de integração sem máquina local.
   - Contras: runners gratuitos limitados (tempo/RAM); 3 SGBDs + embeddings reais estouram o orçamento de minutos; Weaviate exige gRPC (porta extra) e healthchecks frágeis em `services:`; download do MS MARCO (~3 GB) inviável no runner; manutenção do workflow compete com tempo de pesquisa.
2. **Manter CI = unit+lint; integração local sob demanda** — `make test-integration` roda no notebook-alvo com `make up`.
   - Prós: CI rápido e estável (guarda lint + 131 testes unitários puros); integração validada localmente com hardware real (mesmo do experimento); zero custo de runner.
   - Contras: regressão de integração só aparece quando o bolsista roda localmente — mitigado porque todo cenário tem smoke local obrigatório antes de commit (disciplina já em prática nesta etapa).

## Decisão
**Escolhida:** Opção 2. O CI permanece `ruff check` + `ruff format --check` + `pytest tests/unit`. Os testes de integração (`pytest -m integration`) rodam **localmente** via `make test-integration`/smokes, exigindo `make up`.

## Justificativa
O projeto é uma IC em notebook único; o valor do CI aqui é guardar lint e a lógica pura (ground truth, métricas, orquestração, parsing) — 131 testes determinísticos sem Docker. A integração depende de dados grandes (MS MARCO) e de 3 SGBDs simultâneos, fora do envelope de um runner gratuito. A rede de segurança de integração é o **smoke obrigatório antes de cada commit de cenário** (praticado em toda a Etapa 2, registrado nas lições de smoke). Custo/benefício não justifica fragilizar o pipeline.

## Consequência
- `.github/workflows/test.yml` permanece como está (sem `services:`).
- `README.md` documenta que integração é local (`make up && make test-integration`).
- Disciplina firme: nenhum cenário é commitado sem smoke local verde.

## Critério de revisão
Reabrir se: (a) o orientador requisitar CI de integração; (b) o projeto migrar para o Cluster HPC do IEG (Etapa 4) com runner próprio; (c) surgir regressão de integração que o smoke manual não pegou (sinal de que a disciplina manual é insuficiente).

## Backlinks
- [[../../docs/tasks/etapa-2-preparacao-ambiente]]
- [[2026-05-05-versoes-imagens-docker]]
- [[2026-05-10-smoke-cli-cenario-a-make-or-e-colisao-nome]]
