---
tipo: decisão
data: 2026-11-15
status: aceita
autores: ["Rafael Nobre"]
tags: [metodologia, cenario-c, carga-mista, rag, recall, concorrência, etapa-4]
---

# Desenho do Cenário C: buscas sob inserção concorrente, com recall contra a verdade que cresce

Registrada **antes** da sessão de medição, com as definições das métricas, para que nenhuma delas seja escolhida depois de ver os números.

## Contexto

[[2026-04-28-cenarios-A-B-C]] definiu o Cenário C como carga mista — documentos novos chegando enquanto consultas são respondidas — e fixou a métrica principal: latência p99 de consulta sob taxa de inserção de 0, 10, 100 e 1.000 inserções por segundo, na escala de 1M. O código tinha só o esqueleto (`benchmarks/cenario_c.py`, Etapa 2), que recusava rodar. Faltava decidir como produzir a carga, como medir sem que o instrumento distorça o que mede, e o que fazer com o recall, que muda quando a coleção muda.

## Opções consideradas

1. **Só latência sob escrita**, como a ADR pedia
   - Prós: menos código.
   - Contras: uma latência sem recall mede quão rápido o sistema devolve uma resposta possivelmente errada; nos Cenários A e B, recall e latência sempre andaram juntos.
2. **Latência e recall contra a busca exata da base original**
   - Prós: verdade exata já calculada.
   - Contras: penaliza o sistema por devolver um vetor recém-inserido que é de fato vizinho mais próximo.
3. **Latência e recall contra a busca exata sobre a base mais os vetores já confirmados** (escolhida)
   - Prós: mede se a resposta está certa para o estado da coleção no momento da consulta, e se o que acabou de chegar já é encontrável.
   - Contras: exige registrar, para cada consulta, quantos vetores estavam confirmados.

## Decisão

**Escolhida:** opção 3. Definições:

- **Base**: a coleção do Cenário A em 1M (no pgvector, a mesma tabela dos outros cenários, sem o B-tree). Consultas: as mesmas 1.000 held-out do A. Inserções: os passages seguintes do MS MARCO na ordem de identificador, a partir de 1.001.000, com id igual à posição do passage.
- **Janelas**, na mesma coleção, sem pausa entre elas: 0, 10, 100, 1.000, 0 e 0 inserções/s. Cada uma tem 5 s de entrada (descartados) e 60 s medidos. A quinta janela, logo após a escrita, mede o estado acumulado — cerca de 72 mil vetores a mais e otimizadores possivelmente ainda trabalhando. A sexta roda depois de o sistema assentar (coleção `green` no Qdrant, fila de indexação vazia no Weaviate) e separa o efeito do crescimento do efeito do trabalho em segundo plano.
- **Produtor** em processo separado — no mesmo processo, o GIL do Python faria o trabalho do produtor aparecer como latência do consumidor. Lotes a cada 100 ms, de tamanho taxa × 0,1 s (1, 10 e 100 vetores). Agenda fixa: lote atrasado sai assim que possível, com o mesmo tamanho, e o atraso é registrado. Assim a **taxa sustentada** é medida, não imposta; as janelas são lidas pela taxa alcançada.
- **Confirmação** = retorno da escrita: commit da transação no pgvector, `upsert` com `wait=True` no Qdrant, `insert_many` síncrono no Weaviate. A durabilidade dessas confirmações **não é equalizada** (o commit do PostgreSQL inclui `fsync` do WAL), e isso acompanha qualquer comparação de taxa sustentada.
- **Consumidor** único e sequencial, como nos Cenários A e B, com `ef_search = 64`, ciclando as consultas.
- **Recall@10**: para cada consulta, a resposta é comparada com o top-10 exato sobre a base mais os vetores confirmados **no início** da consulta e, separadamente, **no fim**. Um vetor confirmado durante a consulta pode aparecer ou não. Reportam-se os dois limites, **recall inferior** e **recall superior** — média do pior e do melhor dos dois por consulta. Escolher só o melhor favoreceria o sistema mais lento, que passa mais tempo em voo.
- **Recall dos novos**: fração dos vizinhos verdadeiros (estado do início da consulta) que são vetores inseridos e foram devolvidos. O denominador é publicado sempre: nas taxas baixas ele é pequeno (650 vetores novos entre 1M).
- **Sonda de visibilidade**: depois de cada janela com escrita, fora da medição, os últimos 50 vetores confirmados são buscados pelo próprio vetor; mede-se a fração que volta entre os 10 primeiros.
- **Integridade**: ao fim, a contagem de vetores na coleção tem de ser igual à base mais as inserções confirmadas.
- **pgvector**: `CHECKPOINT` antes de cada janela e o estado de `pg_stat_checkpointer` antes e depois, porque um checkpoint dentro ou fora dos 60 s, com uma janela só por taxa, pode dominar o p99.
- **Comparação entre sistemas**: com `ef_search` fixo, o recall de partida difere entre os sistemas; a degradação é lida em relação à janela 0 do próprio sistema.

## Justificativa

O que diferencia o Cenário C do A é que a coleção muda durante a medição. Um recall calculado contra a coleção original mede a coleção errada, e um calculado contra a coleção final cobra do sistema vetores que ainda não existiam. A verdade exata no instante da consulta é a única que responde à pergunta de RAG: "o documento que acabou de chegar já é encontrado, e as respostas continuam certas?".

## Consequência

- `benchmarks/cenario_c.py` implementa as partes puras (agenda do produtor, verdade incremental, recall, resumos) com testes; `benchmarks/insersores.py`, a inserção por sistema; `benchmarks/run_sessao.py`, a integração.
- Cada taxa tem uma única janela de 60 s (n = 1 por taxa): leituras de diferença pequena entre janelas não se sustentam sem repetição.
- Fica fora: concorrência de vários consumidores, atualização e remoção de vetores, e taxas acima de 1.000/s.

## Critério de revisão

Reabrir se algum sistema não sustentar nem 10 inserções/s (a comparação deixaria de ser de carga mista), se a contagem final divergir das confirmações, ou se a sonda de visibilidade mostrar que confirmação não implica vetor buscável num sistema — caso em que o recall dos novos desse sistema precisa ser lido à luz dessa defasagem.

## Backlinks

- [[2026-04-28-cenarios-A-B-C]]
- [[2026-04-28-tamanhos-100k-500k-1m]]
- [[2026-05-10-cenario-a-queries-warmup]]
- [[2026-11-15-protocolo-da-sessao-final]]
- [[../referência/rag-retrieval-augmented-generation]]
