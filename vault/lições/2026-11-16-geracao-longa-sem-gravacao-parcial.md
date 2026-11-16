---
tipo: lição-aprendida
data: 2026-11-16
contexto: Preparação da sessão de medição final. A geração dos embeddings de 1 milhão de passagens rodava na máquina de referência quando ela foi desligada, e todo o trabalho se perdeu. Vide [[../decisões/2026-11-16-procedencia-dos-embeddings-da-sessao-final]].
tags: [embeddings, cache, retomada, mps, preparação]
---

# Geração de horas sem gravação parcial se perde inteira num desligamento

## Situação

Em 15/11/2026, a geração dos embeddings de 1.081.000 passagens foi iniciada às 11h25 na CPU da máquina de referência, a cerca de 100 passagens por segundo. `pipeline/embeddings.py` chama `encode` uma vez sobre a lista inteira e só grava o `.npy` no fim. A máquina foi desligada às 13h15, com perto de 1 hora e 50 minutos de trabalho feito e nenhum byte em disco. Refazer custaria cerca de três horas e empurraria a sessão de medição para fora da janela da madrugada.

A geração foi refeita na GPU da máquina de trabalho, com verificação de equivalência antes do uso. Ali apareceu um segundo problema: o backend MPS do PyTorch acumula memória do driver entre chamadas de `encode`, mesmo com `torch.mps.empty_cache()`. Medido: 6,5 GiB após 5 mil textos, 12,9 GiB após 20 mil. Um `encode` único sobre 1 milhão falhou por falta de memória; blocos de 50 mil no mesmo processo também. O que resolveu foi um processo por bloco de 20 mil, porque o fim do processo devolve a memória.

## Causa

Trabalho longo e caro tratado como operação atômica: ou termina inteiro, ou não deixa nada. Em uma máquina que não é exclusiva, "termina inteiro" é uma aposta. No MPS, a mesma suposição de que a memória volta entre chamadas não vale.

## Regra

- Geração ou cálculo que leve mais de alguns minutos grava resultado parcial em blocos e retoma do último bloco gravado. O padrão que funcionou aqui: um processo por bloco de 20 mil textos, cada bloco gravado em seu próprio arquivo, o laço pulando blocos já existentes e a concatenação feita só no fim. `pipeline/embeddings.py` ainda não faz isso; incorporar o padrão é trabalho pendente.
- Antes de deixar um processo longo sozinho numa máquina compartilhada, combinar com quem a usa que ela não será desligada, ou que o processo tolera o desligamento.
- No MPS, medir a memória do driver (`torch.mps.driver_allocated_memory()`) ao longo de algumas chamadas antes de lançar um job longo; se crescer, isolar por processo.
