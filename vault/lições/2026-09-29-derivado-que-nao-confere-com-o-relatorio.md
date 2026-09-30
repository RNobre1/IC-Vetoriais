---
tipo: lição-aprendida
data: 2026-09-29
contexto: Revisão da versão final do resumo da XIII Jornada Acadêmica a partir dos pareceres dos avaliadores. A conferência contra o relatório parcial vigente achou uma frase do texto enviado sem apoio no relatório, afirmações novas que perdiam ressalvas e medições erradas na documentação do derivado. Vide [[../sessões/2026-09-29]].
tags: [jornada, derivado, fonte-única, regra-2a, relatório, ressalvas]
---

# Resumo derivado do relatório afirmou o que o relatório não afirma

## Situação

O resumo da Jornada (`docx/jornada_academica_2026/main.tex`) é derivado do relatório parcial, que por sua vez interpreta a sessão de medição de 23/08. Na revisão pedida pelos avaliadores, a conferência contra o relatório vigente achou três problemas de origem.

**Frase enviada sem apoio no relatório.** O texto enviado em set/2026 dizia que, neutralizado o fallback para varredura exata, "a diferença arquitetural permanece, porém de magnitude muito menor". `git log -S` mostra que a frase nasceu no próprio commit do resumo: nenhuma versão do relatório a contém. Os dados a contradizem para o Qdrant: com filtro de 1%, 100 mil vetores e ef = 64, a distância até o pgvector é de 0,94 antes e depois da equalização (1,0000 e 0,9996 contra 0,0595 e 0,0592). Só no Weaviate ela cai, de 0,94 para 0,51. As Considerações Parciais do relatório dizem o contrário: "há diferença arquitetural real na busca vetorial com filtro".

**Afirmações novas que perdiam a ressalva.** A primeira redação da revisão partiu dos JSONs e da nota de experimento, não do texto do relatório, e três afirmações saíram sem a ressalva que o relatório carrega:

| Afirmação da primeira redação | Ressalva que faltava (relatório, §5) |
|---|---|
| construir o índice no pgvector leva 21 min, contra menos de 3 nos especializados | `maintenance_work_mem` no padrão de 64 MB: a comparação é *default* contra *default*, não capacidade |
| no pgvector, `ef_search` define quantas consultas por segundo o servidor atende | QPS de cliente único é o inverso da latência média, não throughput de saturação |
| a memória do Weaviate cresce com a base e passa a dimensionar o servidor | o RSS não ordena os sistemas; a leitura defensável é qualitativa |

**Medição errada na documentação do derivado.** O README do resumo registrava "Documento: 2 páginas" e diagramação com corpo em 10 pt. O `.docx` exportado tem 3 páginas, e o XML do modelo tem corpo em 12 pt (`sz=24`), entrelinha simples e recuo de 1,27 cm. A réplica em LaTeX usada para contar páginas foi montada sobre a medição errada, e por isso subestimava o tamanho.

## Causa

O número vive no JSON; a ressalva vive no texto do relatório. Quem deriva a partir do número, ou da memória do que o relatório diz, leva o número e perde a ressalva. E resumir também é derivar: comprimir a conclusão do relatório em meia frase produziu uma afirmação que ele não faz.

No caso das páginas, a conferência foi feita num artefato substituto (a réplica) em vez do próprio entregável, e o substituto nunca foi validado contra o original.

## Regra para o futuro

1. **Hierarquia:** sessão de medição vigente → relatório → derivado. O valor reportado é o da sessão vigente. Execuções anteriores continuam sendo dado — reprodutibilidade, tendência, o que mudou —, citadas com data, nunca no lugar do valor vigente.
2. **Antes de escrever ou revisar um derivado**, ler a seção correspondente do relatório atual e conferir cada afirmação: com o mesmo sentido e com a ressalva junto.
3. **Afirmação que não está no relatório** só entra rastreada a um JSON da sessão vigente, e fica registrada no README do derivado.
4. **Revisão de texto já enviado** classifica cada mudança contra a versão enviada — mantida, reformulada, qualificada, detalhada ou corrigida. Correção vai ao autor como decisão, com a evidência.
5. **Contagem de páginas** de derivado em `.docx` sai do PDF exportado do próprio `.docx` (`make pdf-entrega`), nunca de réplica.
6. **Nota de experimento declara `status`** (`vigente` ou `anterior`) no frontmatter, para que quem a abra saiba se ela traz o valor atual ou um dado de comparação.
