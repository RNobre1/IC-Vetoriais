---
tipo: lição
data: 2026-08-23
tags: [depuração, método, rigor, infraestrutura]
---

# Correlação tratada como causa provada, e o custo disso

## O que aconteceu

Em 2026-08-22 o backend do PostgreSQL caiu durante um `CREATE INDEX ... USING hnsw`. No mesmo instante o host estava com 334 MiB de memória livre e 4,7 GiB de swap, por acúmulo de coleções do Weaviate entre execuções.

Registrei a exaustão de memória como **causa** da queda — em [[../decisões/2026-08-22-medicao-de-footprint-e-tempo-de-indexacao]] e na mensagem de commit `cb50edc`. Não era. Em 2026-08-23 a mesma queda se repetiu com **10 GiB disponíveis, swap sem crescimento e `oom_kill` em zero** no cgroup do contêiner e no host.

A segunda hipótese foi a margem de `/dev/shm`: o Docker o monta com 64 MB, o PostgreSQL aloca ali a memória compartilhada dos workers paralelos, e a construção paralela do HNSW pede um segmento dimensionado por `maintenance_work_mem`. O build rodava com **2,7% de folga**, o que explicaria a intermitência.

**Essa também não era a causa**, e o erro de método foi o mesmo da primeira: mecanismo plausível aceito sem intervenção que o isolasse. Ampliado o `/dev/shm` para 1 GB e depois 3 GB, as quedas continuaram. A causa provada está na seção "O desfecho", ao final — e é o healthcheck do contêiner. Este parágrafo fica registrado como hipótese derrubada, não como diagnóstico: a lição perde o sentido se o próprio texto reincidir no defeito que descreve.

## Por que o erro passou

Havia duas anomalias reais no mesmo intervalo: acúmulo de memória entre execuções (verdadeiro, medido) e a queda do PostgreSQL (verdadeira, observada). Uni as duas numa cadeia causal porque eram simultâneas e porque uma explicação de memória é plausível para um processo morrendo.

O que faltou foi o passo mais barato de todos: **procurar o mecanismo antes de escrever a conclusão**. A mensagem `untracked child process ... exited with exit code 2` estava no log desde a primeira ocorrência e aponta para *worker paralelo*, não para OOM. `oom_kill 0` também já estava disponível e contradizia a tese. Eu tinha lido os dois e não os confrontei com a afirmação que estava escrevendo.

## O custo

Consertei o que não era o problema. O reset de volumes e o watchdog de memória resolveram uma anomalia legítima, mas não a queda — que voltou na execução seguinte. Somando o retrabalho, as duas tentativas de reprodução mal direcionadas e uma execução saudável que interrompi por causa de um critério de watchdog também errado, foram algumas horas.

## Regra para as próximas

1. **Nomear o mecanismo antes de nomear a causa.** "Ficou sem memória" não é mecanismo; "o postmaster como PID 1 recolhe o `pg_isready` morto por timeout e o confunde com filho que quebrou" é. E mecanismo bem formado ainda pode estar errado — a margem de `/dev/shm` era um mecanismo completo e mesmo assim não era a causa. Sem mecanismo, o que se tem é palpite; com mecanismo e sem intervenção, o que se tem é hipótese, e o texto precisa dizer "hipótese".
2. **Confrontar a conclusão com os contadores que a negariam**, e citá-los. Aqui: `memory.events` do cgroup, `journalctl -k`, e a mensagem literal do log do servidor. Todos os três estavam à mão.
3. **Sintoma intermitente não se explica por causa monotônica.** Se o sistema falha às vezes com o mesmo comando, a explicação tem de conter algo que varia perto de um limite. "Memória foi acabando" explica falha crescente, não alternância.
4. **Confirmar por intervenção de uma variável, e com amostra.** Foi o que fechou este caso: mudar só o `init` do contêiner e reexecutar o comando que falhava, 15 vezes sem queda contra 5 quedas em 27 sem ele. Observação passiva já tinha falhado duas vezes por não alcançar a fase sob teste — e intervenção com amostra de um (o `shm_size`) falhou por outro motivo, tratado na regra 7.
5. **Retificar no lugar onde a afirmação errada está**, não só na conversa. O ADR carrega uma nota de retificação explícita; a versão anterior está no histórico do git.

## O desfecho, e o erro que custou o dia

A causa raiz não era nenhuma das três hipóteses que persegui. Era o **healthcheck do contêiner**: o postmaster roda como PID 1, adota os órfãos do namespace, e o `pg_isready` morto por timeout sob carga volta como "filho desconhecido que quebrou". O código de saída 2 da mensagem é literalmente o código que o `pg_isready` usa para "sem resposta" — estava escrito no log desde a primeira ocorrência.

O erro de método que produziu as ~10 horas não foi nenhum diagnóstico individual. Foi **nunca ter construído uma reprodução rápida**. Cada tentativa minha era um ciclo de 20 a 40 minutos, o que tornava impossível bissecar e convidava ao chute. Quando finalmente escrevi a reprodução mínima — psycopg puro, carga de 500 mil, nada mais rodando — ela levou **6 segundos** e falhou na terceira tentativa. A partir daí, três hipóteses foram derrubadas e a causa isolada em menos de uma hora.

**Regra 6, e a mais importante de todas: antes de formular a segunda hipótese, construa a reprodução mais rápida possível.** O tempo gasto nisso se paga na primeira bissecção. Sem ela, cada hipótese custa uma execução inteira e a tentação de "só testar mais uma coisa" vence.

**Regra 7: sintoma intermitente exige contagem, não anedota.** Duas vezes tratei sucesso isolado como confirmação — `shm_size` com n=1, `io_method` com 12/12 que virou falha na tentativa seguinte. Com taxa de falha de ~18%, doze sucessos seguidos têm 10% de chance de acontecer por acaso. Confirmação de conserto para defeito intermitente precisa de amostra que torne a sorte implausível: 25 cargas limpas contra 18% dão 0,7%.

## Aplicação imediata

Duas coisas que passaram a ser medidas por causa disto, e que antes eram invisíveis: o pico de `/dev/shm` por execução, e a taxa de swap-out (em vez de swap ocupado, que só cresce e serve mal como critério).

## Backlinks

- [[../decisões/2026-08-22-medicao-de-footprint-e-tempo-de-indexacao]]
- [[2026-08-19-claim-de-instrumentacao-que-nao-existia]]
