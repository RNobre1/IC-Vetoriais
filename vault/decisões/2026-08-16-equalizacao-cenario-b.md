---
tipo: decisão
data: 2026-08-16
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [cenário-b, metodologia, filtros, hnsw, rigor]
---

# Equalizar o tratamento do atributo de filtro nos 3 SGBDs (Cenário B)

## Contexto

A execução da Etapa 3 (2026-07-09, [[../experimentos/2026-07-09-etapa3-cenarios-a-b]]) produziu, no Cenário B, um resultado que o relatório parcial interpretou como superioridade arquitetural: Qdrant e Weaviate com `recall@10 = 1,0000` nas seletividades baixas, contra 0,059 do pgvector em p=1%. A leitura registrada era "pre-filtering vence post-filtering".

A auditoria de 2026-08-16 mostrou que essa leitura não se sustenta como estava. Dois problemas independentes:

**1. O recall 1,0000 mede busca exata, não ANN.** Onde o recall aparece como 1,0000, ele é *idêntico nos cinco valores de `ef_search`*. Recall que não responde a `ef_search` não pode vir de percurso do grafo HNSW. Ambos os sistemas trocam para varredura exata quando o subconjunto elegível é pequeno:

- Weaviate — `flatSearchCutoff`, default **40000** objetos ([doc](https://docs.weaviate.io/weaviate/concepts/filtering));
- Qdrant — `full_scan_threshold`, default **10000 KB** ([doc](https://qdrant.tech/documentation/concepts/indexing/)).

O limiar do Weaviate é absoluto, o que gera uma predição falseável: a *mesma* seletividade de 10% deve cair em lados opostos do corte em 100k (10.000 elegíveis) e em 500k (50.000 elegíveis). É exatamente o observado — recall plano em 1,0000 numa escala e crescente com `ef` na outra. A previsão acerta os 8 casos do Weaviate.

**2. Os três sistemas não estavam em pé de igualdade.** O `seletor` recebeu tratamento diferente em cada um:

| Sistema | Índice no atributo de filtro (julho/2026) |
|---|---|
| Qdrant | índice de payload `FLOAT` explícito |
| Weaviate | propriedade indexada por padrão (`indexFilterable`) |
| pgvector | **nenhum** — só o HNSW no vetor |

Comparar recall de filtragem entre um sistema com índice no predicado e outro sem é comparar configuração, não arquitetura.

## Opções consideradas

1. **Manter e documentar como limitação** — custo zero, mas o relatório final herdaria um resultado cuja causa é conhecida e evitável. O achado mais citável do Cenário B seria um artefato.
2. **Zerar só os limiares de full-scan** — elimina o artefato principal, mas mantém o pgvector sem índice no predicado; a assimetria de indexação continuaria contaminando a comparação.
3. **Equalizar por inteiro e re-executar** — índice dedicado em `seletor` nos três sistemas e limiar de busca exata zerado nos dois especializados, forçando HNSW em toda seletividade.

## Decisão

**Escolhida: opção 3.** Re-executar o Cenário B em 100k e 500k com `--equalizado`:

- pgvector: `CREATE INDEX ... USING btree (seletor)`;
- Qdrant: `full_scan_threshold=0`;
- Weaviate: `flatSearchCutoff=0`.

A execução de julho **não é descartada**: vira a condição de controle *"cada sistema no seu default"*, que é uma pergunta legítima e diferente — e é o que um usuário encontraria ao instalar cada sistema sem ajuste. As duas condições passam a coexistir, distinguidas pelo campo `equalizado` no JSON de saída e por prefixo de recurso próprio (`bench_b_eq`).

O flag é único e não três independentes: meia equalização produz um terceiro regime, distinto tanto do default quanto do equalizado, e ninguém saberia dizer qual está lendo num JSON antigo.

## Justificativa

Sem equalizar, o Cenário B responde "qual sistema tem o default mais conveniente para subconjuntos pequenos?" — não "qual arquitetura de busca vetorial com filtro é melhor?", que é a pergunta do projeto. O `full_scan_threshold=0` é o caminho indicado pela própria documentação do Weaviate para forçar o índice vetorial (*"To force a vector index search, set `flatSearchCutoff: 0`"*).

Manter as duas condições também é mais informativo que substituir uma pela outra: a diferença entre elas quantifica exatamente quanto o fallback para busca exata contribui, que é um resultado de interesse prático real.

## Consequência

- Os números do Cenário B no relatório parcial precisam ser reescritos, e a interpretação "pre-filtering vs post-filtering" precisa ser qualificada — vide [[../lições/2026-08-16-recall-1-0-era-fallback-full-scan]].
- Toda leitura de `recall = 1,0` exato passa a exigir a verificação "o recall varia com `ef_search`?" antes de virar afirmação no texto.
- Os seeders passam a expor os limiares (`full_scan_threshold`, `flat_search_cutoff`, `indexar_seletor`), com defaults que preservam o comportamento de julho.
- O Cenário C (Etapa 4) nasce já equalizado.

## Critério de revisão

Reabrir se o re-run equalizado mostrar que a diferença entre as duas condições é desprezível (< 2 pontos percentuais de recall em todas as seletividades) — nesse caso a equalização não paga o custo de execução e o default volta a ser a condição única reportada.

## Backlinks

- [[2026-05-19-cenario-b-seletividade-gt-filtrado]]
- [[../experimentos/2026-07-09-etapa3-cenarios-a-b]]
- [[../lições/2026-08-16-recall-1-0-era-fallback-full-scan]]
- [[../papers/patel2024acorn]]
