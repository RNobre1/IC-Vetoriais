---
tipo: decisão
data: 2026-05-05
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [infraestrutura, docker, versões, reprodutibilidade]
---

# Versões das imagens Docker dos 3 SGBDs

## Contexto
Etapa 2 — Dia 1. Para reprodutibilidade, é obrigatório fixar as versões das imagens Docker dos três SGBDs avaliados ([[2026-04-28-sistemas-avaliados]]). Tags rolling (`:latest`, `:stable`) tornam o experimento não-reproduzível e impedem comparação ao longo do tempo, contrariando a metodologia adotada ([[../referência/metodologia-benchmarking-ann]]).

## Opções consideradas
1. **Tags rolling** (`:latest`)
   - Prós: sempre atualizado.
   - Contras: experimentos podem mudar de comportamento entre execuções sem qualquer alteração de código. Inadmissível para benchmarking científico.
2. **Tags semânticas estáveis** (escolhida)
   - Prós: imutáveis para fins práticos; legíveis no `docker-compose.yml`; alinham com convenção de versionamento do upstream.
   - Contras: é preciso atualizar manualmente quando há motivo (segurança, feature relevante para o estudo).
3. **Pin por digest SHA256** (`image@sha256:...`)
   - Prós: imutabilidade absoluta — mesma imagem sempre.
   - Contras: ilegível, custo de manutenção alto, ganho marginal sobre tags semânticas para o escopo de uma IC.

## Decisão
**Escolhidas:** tags semânticas estáveis em `code/docker-compose.yml`:

- **`pgvector/pgvector:pg16`** — pgvector compilado sobre PostgreSQL 16 (LTS).
- **`qdrant/qdrant:v1.12.0`** — Qdrant 1.12 (release estável; pinada antes do primeiro `up`).
- **`semitechnologies/weaviate:1.27.0`** — Weaviate 1.27 (release estável; pinada antes do primeiro `up`).

## Justificativa
- **PostgreSQL 16** é o LTS atual de uso amplo em produção. pgvector tem suporte estável nessa versão, sem regressões conhecidas que afetem o estudo.
- **Qdrant v1.12** e **Weaviate 1.27** são releases estáveis com suporte completo a HNSW (parâmetros M, efConstruction, efSearch — [[2026-04-28-índice-hnsw-em-todos]]) e a filtros estruturados nativos (necessários para o **Cenário B** — [[2026-04-28-cenarios-A-B-C]]).
- Tags semânticas oferecem o equilíbrio adequado entre reprodutibilidade e legibilidade para o escopo desta IC.

## Consequência
- Cada nota em `vault/experimentos/` deve registrar as 3 tags efetivamente usadas no momento da execução; esta ADR fixa o **baseline**, mas experimentos individuais podem testar versões diferentes pontualmente, **desde que documentado** na nota do experimento.
- Atualização das versões requer **nova ADR** descrevendo motivação e quais comportamentos podem mudar.
- Pull inicial das imagens consome ~2 GB de download (executado uma única vez por máquina).
- O `tag` exato sai do `docker-compose.yml`; verificadores de reprodutibilidade externos (e.g. orientador replicando) devem usar exatamente o `docker-compose.yml` versionado.

## Critério de revisão
Reabrir se: (a) bug específico de uma versão afetar experimentos, (b) o orientador requisitar versão específica, (c) for descoberto comportamento materialmente diferente em uma versão mais nova que impacte os resultados, ou (d) uma versão sair de suporte de segurança crítico.

## Backlinks
- [[2026-04-28-sistemas-avaliados]]
- [[2026-04-28-índice-hnsw-em-todos]]
- [[2026-04-28-cenarios-A-B-C]]
- [[../referência/bancos-de-dados-vetoriais]]
- [[../referência/metodologia-benchmarking-ann]]
