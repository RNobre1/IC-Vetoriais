---
tipo: decisão
data: 2026-11-16
status: aceita
tags: [protocolo, hospedeiro, cpu, sessão-final, reprodutibilidade]
---

# Decisão: frequência da CPU fixada e sessão final refeita

Registrada às 11h35 de 16/11/2026 (commit `fbdf21a`), antes de qualquer resultado da sessão nova (`2026-11-16-cpu-fixa`, iniciada às 11h31).

## Contexto

A sessão `2026-11-16-final` (02h39–07h40) rodou com um gerenciador de energia, o auto-cpufreq, que ligava e desligava o turbo da CPU conforme a carga do momento. A sonda fixa de CPU do início de cada bloco mostrou o efeito: 0,128 s no primeiro bloco (pgvector em 100k) e de 0,24 a 0,26 s nos demais, uma diferença de cerca de 2×. A frequência média de cada fase acompanhou a carga do próprio sistema medido. No Cenário A em 1M, o pgvector rodou a cerca de 1.540 MHz em média, o Qdrant a 2.350 e o Weaviate a 2.580; na carga de 1M, o pgvector ficou em 1.955 MHz e os outros dois acima de 3.400. Latência, QPS e tempo de construção do índice daquela sessão ficam confundidos com a frequência. Recall, memória e disco, não. A "inversão" de velocidade do Cenário A, com diferenças de 1,4× a 1,9×, cabe inteira nesse efeito.

O gerenciador foi removido do hospedeiro em 16/11, por decisão do Rafael, que também pediu para refazer o necessário e não citá-lo no relatório.

## Decisão

- **D10a: turbo desligado, frequência base fixa.** O comando root `/usr/local/sbin/ic-cpu-fixa fixar` desliga o turbo (`intel_pstate/no_turbo=1`), prende o P-state em 100% (`min_perf_pct=max_perf_pct=100`), põe o governor em `performance` em todas as CPUs e para o tuned; `restaurar` devolve o estado anterior. O executor (`run_sessao --exigir-cpu-fixa`) confere o estado no início e no fim de cada bloco e recusa o bloco se divergir. O hospedeiro é híbrido: 12 threads de P-core com base de 2.400 MHz e 4 E-cores com base de 1.800 MHz (`hospedeiro_extra.txt` da sessão). Perfil de plataforma `balanced`, na tomada; limites RAPL de 200, 191 e 242 W, que não são atingidos sem turbo.
  - Alternativa descartada: turbo ligado com governor `performance`. A frequência passaria a depender da temperatura e do número de núcleos ativos, que mudam com o sistema medido.
- **D10b: sessão inteira refeita**, mesmo protocolo de [[2026-11-15-protocolo-da-sessao-final]], sem nenhuma outra mudança. Continuam iguais escalas, ordem rotativa, cinco repetições no A, uma passagem no B, C em 1M, ponte em 100k e o critério do controle do Weaviate fixado em 15/11 (|Δ recall| ≤ 0,005 em p = 10%). A sessão `2026-11-16-final` passa a dado anterior e não se mistura nas tabelas.
- **D10c: fatores de fundo.** O GNOME Software e o indexador de arquivos foram parados e mascarados (só durante a sessão) e são religados no fim. O app de controle remoto do hospedeiro fica (cerca de 0,3 núcleo constante). O timer `dnf-makecache` não pode ser parado sem senha. Regra fixada agora, antes da análise:
  1. Cruzar os inícios e fins do `dnf-makecache` no journal (hora local) com as fases de medição dos marcos (UTC), convertendo para o mesmo relógio.
  2. Para cada execução que cair dentro de uma fase medida (A, B, B equalizado, C), calcular no CSV do monitor, **sobre o intervalo da própria execução**, a CPU do hospedeiro fora dos contêineres acima da linha de base da fase e o PSI de E/S.
  3. A mediana e o QPS de um ponto são aceitos se a execução cobrir menos de 10% da duração da fase e somar, em média, menos de 1 núcleo além da linha de base. Isso porque uma contaminação de menos de 10% das consultas só pode deslocar a mediana entre os percentis 45 e 55 da distribuição sem contaminação, e o cliente único usa 1 ou 2 threads de 16. O p99 de uma fase com sobreposição fica sinalizado, porque a cauda não tem essa proteção.
  4. Fora desses limites, o par (escala, sistema) é refeito se a janela permitir. Se não permitir, a fase fica marcada como afetada: o número permanece na tabela com nota e não é omitido.
- **D10d: relatório.** A sessão nova é a única fonte dos números. A metodologia descreve a condição controlada (frequência fixa na base, turbo desligado, conferida em cada bloco pelo estado do driver e pela sonda) sem citar o gerenciador removido, por instrução do Rafael. A comparação com agosto passa a valer só para recall, memória e disco, e o texto passa a dizer que a sessão de agosto não fixou a frequência da CPU, o que explica parte da diferença de latência entre sessões. A sessão descartada fica registrada aqui e em [[../experimentos/2026-11-16-sessao-final]].

## Contraponto

Revisão independente às 11h33, antes de qualquer resultado. D10a, D10b e D10c foram aprovados com as condições que estão incorporadas acima: base de P e E registrada, protocolo declarado intacto, regra registrada antes da análise, limiares justificados, média sobre o intervalo da rajada, PSI de E/S, relógios alinhados e fase marcada em vez de omitida.

Em D10d, o contraponto reprovou a omissão da sessão descartada no relatório e propôs uma frase sem o nome do gerenciador nem números ("uma sessão completa anterior foi descartada por controle insuficiente da frequência da CPU e refeita em condição controlada"). A instrução literal do Rafael de não citar o problema no texto prevalece. A transparência fica garantida por esta nota, que é pública no repositório, e a frase fica oferecida ao Rafael como opção. Também por condição do contraponto, a concordância de recall, memória e disco entre as duas sessões será anotada aqui como verificação.

## Consequência

- O relatório final e o pitch são reescritos com a sessão `2026-11-16-cpu-fixa`.
- Verificações depois da sessão: sondas estáveis (±5%), `cpu_mhz_medio` do monitor nunca acima de 2.400 MHz, `throttle_total` sem salto, nenhum bloco recusado pela checagem de CPU e a regra de D10c aplicada.

## Backlinks

- [[2026-11-15-protocolo-da-sessao-final]]
- [[2026-11-15-desenho-do-cenario-c]]
- [[../experimentos/2026-11-16-sessao-final]]
