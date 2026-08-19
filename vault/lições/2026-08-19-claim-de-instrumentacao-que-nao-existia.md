---
tipo: lição
data: 2026-08-19
tags: [rigor, relatório, verificação, tempo-verbal]
---

# Frase em tempo verbal passado descrevendo trabalho que era só plano

## O que aconteceu

O §5.2 do relatório parcial (Geração e indexação dos embeddings) fechava assim:

> "A instrumentação **passou a gravar** essas medidas junto às curvas de desempenho, e os valores serão apresentados no relatório final, obtidos em execução dedicada."

A frase é falsa. Nem `benchmarks/run_cenario_a.py` nem `benchmarks/run_cenario_b.py` medem ou persistem tempo de indexação e footprint. `lib/reporting.py` grava apenas latências, QPS e recall. O único código que mediu essas grandezas foram os scripts históricos em `code/experimentos/`, e a saída deles ia para o console — que é exatamente o problema que o parágrafo anterior declara.

O parágrafo inteiro existe para assumir uma lacuna com honestidade: a métrica está no plano (§4.4), foi medida na Etapa 3, mas não foi persistida em arquivo e por isso não é reportada. A última frase, escrita no passado, transformava um trabalho previsto em fato consumado e contaminava justamente o parágrafo que servia de prova de rigor.

Descoberta ao responder uma pergunta do bolsista sobre por que o uso de recursos não aparece nas tabelas. A verificação foi trivial — `grep -rn footprint --include="*.py"` — e mostrou ocorrências apenas em `experimentos/`.

## Causa raiz

Escrever, no mesmo parágrafo, o estado atual e a intenção futura, e deixar o tempo verbal decidir qual é qual. "Passou a gravar" e "vai passar a gravar" são uma sílaba de diferença no texto e a diferença inteira em termos de verdade.

O agravante: a frase foi escrita durante uma sessão em que a instrumentação **estava** sendo discutida como próximo passo. A intenção era real; só não tinha virado código.

## Regra para o futuro

**Toda frase do relatório que afirma algo sobre o estado do código precisa de um comando que a confirme, e o comando roda antes do commit.** Não é conferência de estilo — é o mesmo padrão que o projeto já aplica a número sem fonte.

Na prática, para cada afirmação desse tipo:

| Afirmação no texto | Comando que a verifica |
|---|---|
| "a instrumentação grava X" | `grep -rn "X" --include="*.py" code/` |
| "os resultados estão versionados" | `git ls-files code/results \| wc -l` |
| "N testes passam" | `make test` |
| "o pipeline roda lint e testes" | ler o workflow do CI, não a lembrança dele |

E, na redação: **descrição do presente e plano de futuro em frases separadas**, com o plano sempre no futuro explícito ("será estendida", "serão apresentados"). Frase que mistura os dois tempos é onde o claim falso se esconde.

## Correção aplicada

Reescrita para "A instrumentação **será estendida** para persistir essas medidas junto às curvas de desempenho, e os valores serão apresentados no relatório final, obtidos em execução dedicada." Commit `29205e7`.

A instrumentação em si virou trabalho planejado com protocolo próprio, em [[../../docs/runbook-medicao-dell.md]].

## Backlinks

- [[2026-08-16-fork-silencioso-do-relatorio]]
- [[../decisões/2026-08-19-divisao-de-maquinas-mac-dell]]
- [[../sessões/2026-08-19]]
