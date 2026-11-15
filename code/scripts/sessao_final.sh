#!/usr/bin/env bash
# Sessão de medição completa na máquina de referência.
#
# Roda, numa janela única, a ponte do protocolo anterior (Cenário A em 100k) e
# o executor `benchmarks.run_sessao` para cada escala e sistema, na ordem que o
# próprio executor define. Grava num diretório da sessão o ambiente, o
# progresso (retomável), os marcos de fase e o CSV do amostrador de recursos.
# Decisão: vault/decisões/2026-11-15-protocolo-da-sessao-final.md.
#
# Retomada: um par (escala, sistema) com "ok" em progresso.tsv é pulado. Um par
# que falha é tentado de novo uma vez; o executor recria o serviço no início,
# então a nova tentativa parte de linha de base limpa.
#
# Variáveis:
#   SESSAO_ID   nome do diretório da sessão (obrigatória)
#   ESCALAS     escalas, na ordem (padrão: "100000 1000000 500000")
#   C_EM        escalas com Cenário C (padrão: "1000000")
#   PONTE       1 roda o Cenário A em 100k pelo protocolo anterior (padrão: 1)
#   PONTE_ARGS  variáveis extras do make bench-A da ponte (ex.: "EF=16,64")
#   EXTRA       argumentos extras do run_sessao (o ensaio reduz a carga aqui)
#   RESULTS     diretório dos JSONs (padrão: results)
set -uo pipefail
cd "$(dirname "$0")/.."

SESSAO_ID=${SESSAO_ID:?defina SESSAO_ID}
ESCALAS=${ESCALAS:-"100000 1000000 500000"}
C_EM=${C_EM:-"1000000"}
PONTE=${PONTE:-1}
PONTE_ARGS=${PONTE_ARGS:-}
EXTRA=${EXTRA:-}
RESULTS=${RESULTS:-results}
PY=.venv/bin/python
[ -x "$PY" ] || { echo "ERRO: $PY não existe; rode 'make deps' antes da sessão." >&2; exit 1; }

DIR="$RESULTS/sessoes/$SESSAO_ID"
mkdir -p "$DIR"
PROG="$DIR/progresso.tsv"
MARCOS="$DIR/marcos.jsonl"
touch "$PROG"

log() { echo "[sessao $(date +%H:%M:%S)] $*"; }
pswpout() { awk '/^pswpout /{print $2}' /proc/vmstat; }
# A ponte roda pelos CLIs antigos, que não gravam marcos; sem estes, os JSONs
# dela cairiam fora da janela da sessão na análise.
marco_ponte() {
    $PY -c "from pathlib import Path; from benchmarks.run_sessao import registrar_marco as r; \
r(Path('$MARCOS'), n=100000, sistema='todos', passo='ponte', evento='$1')" >/dev/null
}

{
    date -u +%Y-%m-%dT%H:%M:%SZ
    echo "commit: $(git rev-parse HEAD)"
    git status --short
    uname -r
    echo "governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)"
    lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Core|MHz'
    zramctl 2>/dev/null
    swapon --show
    free -m
    docker version --format 'docker {{.Server.Version}}'
    docker inspect --format '{{.Name}} {{.Image}} {{.Config.Image}}' ic-pgvector ic-qdrant ic-weaviate
    echo "escalas: $ESCALAS | C em: $C_EM | ponte: $PONTE | extra: $EXTRA"
} >>"$DIR/ambiente.txt" 2>&1

make ui-down >/dev/null 2>&1 || true

$PY -m lib.monitor --saida "$DIR/monitor_$(date +%H%M%S).csv" --intervalo 1.0 \
    --containers ic-pgvector,ic-qdrant,ic-weaviate >>"$DIR/monitor.log" 2>&1 &
MON=$!
trap 'kill -TERM $MON 2>/dev/null; wait $MON 2>/dev/null' EXIT
log "monitor pid $MON"

if [ "$PONTE" = "1" ] && ! grep -q "^ponte	" "$PROG"; then
    log "ponte: reset + bench-A N=100000 (protocolo anterior)"
    make reset-medicao >>"$DIR/log_ponte.txt" 2>&1
    sw0=$(pswpout); t0=$(date +%s)
    marco_ponte inicio
    # shellcheck disable=SC2086
    make bench-A N=100000 $PONTE_ARGS >>"$DIR/log_ponte.txt" 2>&1
    rc=$?
    marco_ponte fim
    printf 'ponte\t100000\t%s\t1\t%s\t%s\n' "$([ $rc = 0 ] && echo ok || echo "falha$rc")" \
        "$(($(date +%s) - t0))" "$(($(pswpout) - sw0))" >>"$PROG"
    log "ponte rc=$rc"
fi

for N in $ESCALAS; do
    ORDEM=$($PY -c "from benchmarks.run_sessao import ordem_dos_sistemas as o; print(' '.join(o($N)))") \
        || { log "ERRO: não consegui obter a ordem dos sistemas"; exit 1; }
    # Teto por par: um passo travado não pode consumir a janela inteira.
    TETO=5400
    [ "$N" -ge 1000000 ] && TETO=10800
    feitos=0
    for S in $ORDEM; do grep -q "^$N	$S	ok" "$PROG" && feitos=$((feitos + 1)); done
    [ "$feitos" = 3 ] && continue
    log "escala $N: reset geral; ordem $ORDEM"
    make reset-medicao >>"$DIR/log_reset_$N.txt" 2>&1
    C=""
    case " $C_EM " in *" $N "*) C="--cenario-c" ;; esac
    for S in $ORDEM; do
        grep -q "^$N	$S	ok" "$PROG" && continue
        for tentativa in 1 2; do
            log "N=$N $S tentativa $tentativa"
            sw0=$(pswpout); t0=$(date +%s)
            LOGP="$DIR/log_${N}_${S}.txt"
            L0=$(wc -l <"$LOGP" 2>/dev/null || echo 0)
            # shellcheck disable=SC2086
            SESSAO_TENTATIVA=$tentativa timeout -k 60 "$TETO" \
                $PY -m benchmarks.run_sessao --n "$N" --sistema "$S" $C \
                --marcos "$MARCOS" --results-dir "$RESULTS" $EXTRA \
                >>"$LOGP" 2>&1
            rc=$?
            dur=$(($(date +%s) - t0)); dsw=$(($(pswpout) - sw0))
            printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$N" "$S" \
                "$([ $rc = 0 ] && echo ok || echo "falha$rc")" "$tentativa" "$dur" "$dsw" >>"$PROG"
            log "N=$N $S rc=$rc ${dur}s swap_out_paginas=$dsw"
            [ $rc = 0 ] && break
            tail -5 "$LOGP"
            # Falha depois de o C começar: os demais cenários do par já estão
            # gravados e o C é o último passo. Refazer o par repetiria o seed
            # (cerca de 1 h no pgvector em 1M) para recuperar só o C.
            if tail -n +"$((L0 + 1))" "$LOGP" | grep -q '"passo": "C_total", "evento": "inicio"'; then
                printf '%s\t%s\tfalhaC\t%s\t%s\t%s\n' "$N" "$S" "$tentativa" "$dur" "$dsw" >>"$PROG"
                log "N=$N $S: falha no Cenário C; sem nova tentativa do par"
                break
            fi
        done
    done
done
log "fim da sessão"
exit 0
