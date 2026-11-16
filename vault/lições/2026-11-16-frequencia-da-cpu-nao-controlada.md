---
tipo: lição-aprendida
data: 2026-11-16
contexto: Sessão de medição final de 16/11/2026 (madrugada), descartada e refeita à tarde com a frequência da CPU fixa. Vide [[../decisões/2026-11-16-frequencia-da-cpu-fixada]].
tags: [hospedeiro, cpu, turbo, medição, reprodutibilidade]
---

# Um gerenciador de energia não controlado decidiu a ordem dos sistemas

## Situação

A sessão da madrugada de 16/11 terminou sem erro, e o relatório foi escrito sobre ela. A principal conclusão de velocidade era uma "inversão": o pgvector mais rápido em 100 mil vetores e o mais lento em 500 mil e 1 milhão. Ao revisar a confiança nos resultados, apareceu no hospedeiro um daemon que ninguém tinha considerado, o auto-cpufreq, que ligava e desligava o turbo conforme a carga.

Os dados já mostravam o efeito; só não tinham sido lidos com essa pergunta. A sonda fixa de CPU deu 0,128 s no primeiro bloco e 0,24 a 0,26 s nos outros. A frequência média de cada fase acompanhava a carga do próprio sistema medido: quem usava mais CPU ganhava turbo e parecia mais rápido. O contador de throttle térmico subiu mais de um milhão de eventos. Com a frequência fixa, a inversão desapareceu, e a queda de latência sob escrita no Cenário C também.

## Causa

O ambiente registrava o governor da CPU, que estava em `performance`, e isso foi tomado como frequência controlada. O governor não diz nada sobre o turbo. A sonda existia justamente para pegar mudança de velocidade do hospedeiro, mas o critério de leitura dela não foi fixado antes, e o 2× do primeiro bloco não foi examinado até a revisão.

## Regra

- **Antes de medir, controlar a frequência, e não só registrá-la:** turbo desligado e P-state preso (`ic-cpu-fixa fixar`), com o executor recusando bloco se o estado mudar. Procurar gerenciadores de energia (`pgrep -fa 'cpufreq|tlp|powertop'`) e timers dentro da janela.
- **Sonda com critério fixado antes da sessão:** com a CPU fixa, a sonda variou até 6% entre blocos (os fins de bloco, logo após carga pesada, são os mais lentos); variação acima de 10% é sinal de alarme, não ruído. Ler a sonda antes de abrir os resultados.
- **Desconfiar de resultado que depende da carga do próprio sistema medido.** Se quem usa mais CPU é sistematicamente mais rápido, o hospedeiro pode estar premiando a carga.

## Backlinks

- [[../decisões/2026-11-16-frequencia-da-cpu-fixada]]
- [[../experimentos/2026-11-16-sessao-cpu-fixa]]
- [[../experimentos/2026-11-16-sessao-final]]
