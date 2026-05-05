---
tipo: lição-aprendida
data: 2026-05-05
contexto: Recomendação de GUI para inspecionar Weaviate self-hosted
tags: [rigor-cientifico, recomendação, weaviate, ferramentas, validação]
---

# Lição — Recomendar tooling sem validar nas docs oficiais

## Situação

Em 2026-05-05, ao listar opções de GUI para os 3 SGBDs vetoriais do projeto, recomendei ao bolsista usar o **`console.weaviate.cloud`** apontando para a instância self-hosted em `localhost:8080`. Texto literal da recomendação:

> "Weaviate: usar https://console.weaviate.cloud/ apontando pra localhost:8080 (free, é só web app), OU escrever queries via Python que já temos."

O bolsista seguiu a recomendação, criou conta, abriu o console — e o dropdown "Select cluster" ficou vazio. Foi quando descobri que o `console.weaviate.cloud` **só conecta a clusters criados no Weaviate Cloud Service (WCS, hospedado por eles)**, não a instâncias self-hosted.

## Causa raiz

Confundi o **Weaviate Cloud Console** (web UI exclusiva do serviço pago WCS) com uma ferramenta genérica de administração. Não validei nas docs oficiais antes de recomendar. Assumi por analogia com Grafana Cloud / outras plataformas que aceitam endpoints custom — mas Weaviate Cloud Console é especificamente o painel do produto cloud deles.

Esse é o tipo de erro que o **rigor científico** (vide `feedback_rigor_cientifico.md` na memória global) precisa evitar: recomendação técnica entregue como fato sem validação. Em projeto científico, recomendar tooling errado custa tempo do bolsista (cria conta, configura, descobre que não funciona) e mina credibilidade das próximas recomendações.

## Correção

A solução real para GUI de Weaviate self-hosted, escolhida em 2026-05-05:

- **Verba** (oficial Weaviate Inc., OSS, container Docker) rodando isolado em `docker-compose.ui.yml`. Vide [[../decisões/2026-05-05-isolamento-ui-vs-benchmark]].
- Alternativas válidas para inspeção ad-hoc: GraphQL nativo em `/v1/graphql`, REST em `/v1/objects` e `/v1/schema`, ou Python REPL com `weaviate-client`.

## Regra para aplicação futura

**Antes de recomendar uma ferramenta como solução, validar nas docs oficiais que ela suporta o caso de uso específico (especialmente quando a recomendação é "X aceita endpoint Y").**

Sinais de risco:

- Recomendação por analogia ("é tipo o Grafana Cloud, mas pra Weaviate").
- Não conferi a doc oficial nesta sessão.
- A ferramenta é de um vendor que tem produto pago — confirmar se a feature está no plano free.
- O bolsista vai abrir conta / configurar antes de testar — se quebrar, perde tempo dele.

Quando em dúvida, **dizer "não tenho certeza, deixa eu confirmar"** antes de afirmar. Vale mais investir 30 segundos a mais de pesquisa do que retraçar a recomendação depois.

## Aplicação imediata

Esta lição é a primeira aplicação concreta da regra de rigor científico (`feedback_rigor_cientifico` na memória global) a uma falha de minha autoria, registrada em vault como artefato auditável.

## Backlinks

- [[../decisões/2026-05-05-isolamento-ui-vs-benchmark]] — solução adotada (Verba).
- [[2026-05-05-rigor-citacoes-abnt]] — outra lição da mesma sessão sobre rigor (citações).
- [[2026-05-05-armadilhas-dia-1-etapa-2]] — armadilhas técnicas do mesmo dia.
