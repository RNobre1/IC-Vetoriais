---
tipo: lição-aprendida
data: 2026-08-16
contexto: Auditoria dos resultados da Etapa 3 antes de fechar o relatório parcial. Os números do Cenário B haviam sido interpretados como vantagem arquitetural de pre-filtering; a auditoria mostrou que boa parte do efeito é fallback para busca exata. Vide [[../decisões/2026-08-16-equalizacao-cenario-b]] e [[../experimentos/2026-07-09-etapa3-cenarios-a-b]].
tags: [cenário-b, qdrant, weaviate, hnsw, filtros, recall, rigor, benchmarking]
---

# `recall@10 = 1,0` no Cenário B media o fallback para busca exata, não a qualidade do ANN

## Situação

Os resultados do Cenário B (2026-07-09) mostravam Qdrant e Weaviate com `recall@10 = 1,0000` nas seletividades baixas, contra 0,059 do pgvector em p=1%. A redação do relatório parcial converteu isso em conclusão arquitetural:

> "a degradação do recall do pgvector em seletividades baixas confirma a limitação da estratégia de post-filtering (...) frente à abordagem de pre-filtering dos bancos vetoriais especializados"

A conclusão é atraente, alinha com a hipótese do projeto e estava prestes a ir para o orientador. Ela não sobrevive a uma checagem simples.

## O sinal que denunciou

`recall = 1,0000` aparecia **idêntico nos cinco valores de `ef_search`** (16, 32, 64, 128, 256). Esse é o ponto: `ef_search` controla a largura da busca no grafo HNSW. Se o grafo estivesse sendo percorrido, aumentar `ef` teria que mudar o recall. Recall perfeitamente insensível a `ef_search` só acontece quando o grafo **não é percorrido**.

O teste diagnóstico é barato e deveria ser rotina:

```python
# Para cada (sistema, seletividade): o recall responde a ef_search?
plano = max(recalls) - min(recalls) < 1e-9   # se True, não é ANN
```

## Causa

Os dois sistemas especializados trocam automaticamente para varredura exata quando o subconjunto elegível é pequeno — é otimização deliberada e documentada, não bug:

| Sistema | Parâmetro | Default | Doc |
|---|---|---|---|
| Weaviate | `flatSearchCutoff` | **40000 objetos** | [Filtering](https://docs.weaviate.io/weaviate/concepts/filtering) |
| Qdrant | `full_scan_threshold` | **10000 KB** | [Indexing](https://qdrant.tech/documentation/concepts/indexing/) |

O limiar do Weaviate é **absoluto**, não percentual — e isso gera uma predição falseável que confirma o mecanismo. A mesma seletividade de 10% cai em lados opostos do corte conforme a escala:

| N | p | Elegíveis | vs 40.000 | Recall observado |
|---|---|---|---|---|
| 100k | 10% | 10.000 | abaixo | 1,0000 constante (exata) |
| 500k | 10% | 50.000 | acima | 0,765 → 0,970 (HNSW) |

A previsão acerta os 8 casos do Weaviate. Mesma seletividade percentual, comportamento oposto, previsto pelo valor absoluto do corte.

## O que eu tinha afirmado errado

A primeira leitura da auditoria generalizou demais: "Qdrant e Weaviate nem usaram ANN no Cenário B". Falso. O fallback vale apenas onde o recall é plano — 6 das 24 séries. Em p=50% e p=100% o Weaviate percorre o grafo normalmente (recall vai de 0,844 a 0,991 com `ef`). O que acontece ali é outro fenômeno: a latência fica insensível a `ef` porque o **custo do filtro domina** a busca, não porque falte ANN.

Registrar isto explicitamente porque o erro é instrutivo: uma hipótese que explica *parte* dos dados tende a ser esticada para explicar o resto. A separação entre "provado" e "deduzido" precisa ser refeita a cada ponto, não uma vez por hipótese.

## Regra para o futuro

1. **`recall = 1,0` exato é suspeita, não resultado.** Busca aproximada raramente acerta tudo. Antes de escrever qualquer conclusão sobre recall, verificar se ele responde a `ef_search`.
2. **Comparar defaults ≠ comparar arquiteturas.** Cada SGBD embute heurísticas de plano (limiar de full-scan, escolha de índice). Sem equalizar, o benchmark mede a conveniência do default, que é uma pergunta legítima mas **outra** pergunta.
3. **Verificar simetria de indexação do atributo de filtro** antes de atribuir diferença a arquitetura. Em julho o Qdrant tinha índice de payload em `seletor`, o Weaviate indexava por padrão, e o pgvector não tinha índice nenhum.
4. **Quando o mecanismo suspeito tiver parâmetro documentado, derivar uma predição quantitativa e testá-la contra os dados que já existem.** Custa minutos e transforma hipótese plausível em evidência.

## Consequência

- ADR [[../decisões/2026-08-16-equalizacao-cenario-b]] — Cenário B re-executado com `--equalizado`, mantendo a execução default como condição de controle.
- Seeders passam a expor `full_scan_threshold`, `flat_search_cutoff` e `indexar_seletor`.
- Contraprova local em [[../experimentos/2026-08-16-contraprova-full-scan]].

## Backlinks

- [[../decisões/2026-08-16-equalizacao-cenario-b]]
- [[../decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]
- [[../experimentos/2026-07-09-etapa3-cenarios-a-b]]
- [[../papers/patel2024acorn]]
- [[../referência/hnsw]]
