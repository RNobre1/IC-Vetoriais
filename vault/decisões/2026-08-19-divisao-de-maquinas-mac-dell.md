---
tipo: decisão
data: 2026-08-19
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [metodologia, hardware, reprodutibilidade, fluxo-de-trabalho]
---

# Separar máquina de medição (Dell) de máquina de análise (Mac)

## Contexto

Em 2026-08-19 o trabalho passou a acontecer em duas máquinas:

| Máquina | Sistema | CPU | Memória |
|---|---|---|---|
| Dell G15 5530 | Fedora Linux | Intel i5-13450HX (10c/16t, x86-64) | 16 GiB DDR5 |
| MacBook Air M4 | macOS | Apple M4 (ARM64) | — |

Os dois ficam com o mesmo repositório sincronizado. Isso cria um risco que não existia enquanto havia uma máquina só: **um número medido no Mac pode entrar em tabela do relatório sem que ninguém perceba a troca de hardware**.

O relatório parcial declara explicitamente, em [[../../docx/relatorio_parcial/secoes/05-metodologia]] §4.3 e nas Limitações do §5.5, que os experimentos foram conduzidos em um único hardware. Misturar as duas arquiteturas sem declarar invalidaria essa afirmação — e a diferença não é pequena: x86-64 contra ARM64, hierarquia de cache distinta, memória unificada, e o Docker no macOS roda dentro de uma VM, com penalidade de I/O que não existe no Fedora.

Há ainda um segundo risco, este já materializado uma vez neste projeto: duas frentes de trabalho editando os mesmos `.tex` e as mesmas notas do vault produziram um fork silencioso ([[../lições/2026-08-16-fork-silencioso-do-relatorio]]), que quase levou uma referência duplicada para a entrega.

## Opções consideradas

1. **Rodar tudo no Mac a partir de agora** — máquina mais nova e mais rápida.
   - Prós: uma máquina só, sem sincronização.
   - Contras: descarta a comparabilidade com todos os dados de 100k e 500k já medidos; obriga a refazer a Etapa 3 inteira antes de qualquer avanço; e o Docker sob VM no macOS introduz uma variável de I/O que o trabalho não controla.
2. **Deixar as duas máquinas medirem, anotando qual mediu o quê** — flexível.
   - Prós: aproveita as duas.
   - Contras: cada tabela passaria a ter uma coluna de hardware, e comparações entre linhas medidas em máquinas diferentes deixariam de ter significado. Na prática, dobra o custo de toda medição futura ou torna metade dos dados inútil.
3. **Papéis assimétricos: Dell mede, Mac analisa** — separar produção de dado de produção de interpretação.
   - Prós: preserva a homogeneidade de hardware afirmada no relatório; centraliza num lugar só a edição de relatório e vault, que é onde o conflito dói; aproveita o Mac para o trabalho que não depende de hardware (código, testes com dublês, análise, redação).
   - Contras: exige `git pull` disciplinado e um protocolo escrito para a máquina executora.

## Decisão

**Escolhida: opção 3.**

| Máquina | Papel | Faz | Não faz |
|---|---|---|---|
| MacBook Air M4 | **principal** | escreve código e testes, analisa resultados, edita relatório e vault, decide metodologia, gera o PDF | não roda benchmark que produza número para tabela do relatório |
| Dell G15 / Fedora | **executor de medição** | roda benchmark, commita os JSONs brutos, faz push, relata anomalias de execução | não interpreta, não edita relatório, não edita vault, não muda metodologia, não refatora código de benchmark |

O protocolo operacional do executor está em [[../../docs/runbook-medicao-dell.md]].

## Justificativa

O critério que separa as duas máquinas é simples e verificável: **a atividade depende do hardware?**

- Depende: latência, QPS, tempo de indexação, footprint. Vai para o Dell.
- Não depende: código, teste unitário com dublê, análise de JSON, redação, decisão metodológica, compilação do LaTeX. Fica no Mac.

Sobre o conflito de edição, a assimetria resolve pela raiz em vez de por convenção: dado bruto é commutativo — dois JSONs de execuções diferentes convivem em qualquer ordem de merge. Interpretação não é: duas versões do mesmo parágrafo do §5.2 exigem alguém para decidir qual vale, e foi exatamente esse "alguém" que faltou em julho.

A comparação Fedora × macOS continua desejável, mas como **experimento próprio e declarado** — variável de estudo, não efeito colateral de troca de máquina.

## Consequência

- Todo número que entra em tabela do relatório sai do Dell, até que exista uma decisão específica em contrário.
- O Mac pode rodar benchmark para **depurar código** (validar que a instrumentação grava o que deve), nunca para produzir número reportável. Resultado de depuração não é commitado em `code/results/`.
- Instrumentação nova nasce no Mac com TDD, chega ao Dell por `git pull`. O Dell nunca escreve código de produção.
- A comparação de arquitetura entra como candidata à Etapa 4/5, com ADR próprio, protocolo de igualdade de configuração e declaração de que o Docker no macOS roda sob VM.

## Critério de revisão

Reabrir se: (a) o Dell ficar indisponível, caso em que a Etapa 4 inteira migra para o Mac e **todos** os dados anteriores precisam ser re-medidos lá para continuarem comparáveis; (b) a comparação de arquitetura virar objetivo declarado, caso em que as duas máquinas passam a medir sob protocolo próprio; (c) o Cluster HPC do IEG/UFOPA se tornar viável, o que introduz uma terceira máquina e exige revisar esta divisão por inteiro.

## Backlinks

- [[2026-08-16-equalizacao-cenario-b]]
- [[../lições/2026-08-16-fork-silencioso-do-relatorio]]
- [[../sessões/2026-08-19]]
