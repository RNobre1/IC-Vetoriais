"""Agregação e cálculo de custos de recursos por fase da sessão experimental.

Cruza o log periódico do monitor (CSV a 1 Hz com memória, swap, CPU e pressão PSI)
com os marcos de fase (`marcos.jsonl`) para medir o consumo de cada passo:
- Picos de memória total (`mem_current`) e anônima (`anon`) do contêiner
- Utilização média de CPU em núcleos do contêiner
- Páginas de swap-out do host atribuídas ao intervalo da fase
- Pressão máxima de memória (PSI `full avg10`) e memória disponível mínima

A função `linhas_custo` formata essas grandezas no padrão tabular do relatório.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from analise.formato import formato_escala, num
from analise.sessao import normalizar_timestamp

CONTAINER_POR_SISTEMA = {
    "pgvector": "ic-pgvector",
    "qdrant": "ic-qdrant",
    "weaviate": "ic-weaviate",
}


@dataclass(frozen=True)
class MetricaCustoFase:
    """Métricas de custo de recursos agregadas em uma fase (passo)."""

    n: int
    sistema: str
    passo: str
    pico_mem_mib: float | None
    pico_anon_mib: float | None
    cpu_nucleos: float | None
    swap_out_paginas: int | None
    swap_out_mib: float | None
    pico_psi_mem_full: float | None
    mem_disponivel_min_mib: float | None


def calcular_custo(
    monitor_csv: str | Path,
    marcos: str | Path | Sequence[dict[str, Any]],
) -> list[MetricaCustoFase]:
    """Cruza CSV do monitor com marcos para derivar métricas de custo por fase."""
    marcos_lista: list[dict[str, Any]] = []
    if isinstance(marcos, str | Path):
        p_marcos = Path(marcos)
        if p_marcos.is_dir():
            p_marcos = p_marcos / "marcos.jsonl"
        for linha in p_marcos.read_text(encoding="utf-8").splitlines():
            s = linha.strip()
            if s:
                marcos_lista.append(json.loads(s))
    else:
        marcos_lista = list(marcos)

    # Identifica intervalos [t_inicio, t_fim] para cada (n, sistema, passo)
    inicios: dict[tuple[int, str, str], datetime] = {}
    intervalos: list[tuple[int, str, str, datetime, datetime]] = []

    for m in marcos_lista:
        n = m.get("n")
        sis = m.get("sistema")
        passo = m.get("passo")
        evento = m.get("evento")
        ts_raw = m.get("ts_utc")

        if not n or not sis or not passo or not evento or not ts_raw:
            continue

        ts = normalizar_timestamp(ts_raw)
        chave = (int(n), sis.lower(), passo)

        if evento == "inicio":
            inicios[chave] = ts
        elif evento == "fim" and chave in inicios:
            t0 = inicios.pop(chave)
            intervalos.append((int(n), sis.lower(), passo, t0, ts))

    # Lê amostras do monitor CSV
    p_csv = Path(monitor_csv)
    amostras: list[dict[str, Any]] = []
    with p_csv.open(encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            ts_str = linha.get("ts_utc")
            if not ts_str:
                continue
            linha["_dt"] = normalizar_timestamp(ts_str)
            amostras.append(linha)

    resultados: list[MetricaCustoFase] = []

    for n, sis, passo, t0, t1 in intervalos:
        # Amostras pertencentes ao intervalo
        linhas_fase = [r for r in amostras if t0 <= r["_dt"] <= t1]
        if not linhas_fase:
            continue

        c = CONTAINER_POR_SISTEMA.get(sis, sis)
        col_mem = f"{c}_mem_current_b"
        col_anon = f"{c}_anon_b"
        col_cpu = f"{c}_cpu_usec"

        pico_mem = None
        if col_mem in linhas_fase[0]:
            pico_mem = max(float(r[col_mem]) for r in linhas_fase if r.get(col_mem)) / 1048576.0

        pico_anon = None
        if col_anon in linhas_fase[0]:
            pico_anon = max(float(r[col_anon]) for r in linhas_fase if r.get(col_anon)) / 1048576.0

        cpu_nucleos = None
        if col_cpu in linhas_fase[0]:
            r0 = linhas_fase[0]
            r1 = linhas_fase[-1]
            if "t_mono_s" in r0 and r0["t_mono_s"] and r1["t_mono_s"]:
                dt = float(r1["t_mono_s"]) - float(r0["t_mono_s"])
            else:
                dt = (r1["_dt"] - r0["_dt"]).total_seconds()
            dcpu = float(r1[col_cpu]) - float(r0[col_cpu])
            cpu_nucleos = (dcpu / (dt * 1e6)) if dt > 0 else 0.0

        swap_paginas = None
        swap_mib = None
        if "pswpout" in linhas_fase[0]:
            r0 = linhas_fase[0]
            r1 = linhas_fase[-1]
            dswap = int(r1["pswpout"]) - int(r0["pswpout"])
            swap_paginas = dswap
            swap_mib = (dswap * 4096.0) / 1048576.0

        pico_psi = None
        if "psi_mem_full_avg10" in linhas_fase[0]:
            vals_psi = [
                float(r["psi_mem_full_avg10"]) for r in linhas_fase if r.get("psi_mem_full_avg10")
            ]
            if vals_psi:
                pico_psi = max(vals_psi)

        mem_disp_min = None
        if "mem_available_kb" in linhas_fase[0]:
            vals_disp = [
                float(r["mem_available_kb"]) for r in linhas_fase if r.get("mem_available_kb")
            ]
            if vals_disp:
                mem_disp_min = min(vals_disp) / 1024.0

        resultados.append(
            MetricaCustoFase(
                n=n,
                sistema=sis,
                passo=passo,
                pico_mem_mib=pico_mem,
                pico_anon_mib=pico_anon,
                cpu_nucleos=cpu_nucleos,
                swap_out_paginas=swap_paginas,
                swap_out_mib=swap_mib,
                pico_psi_mem_full=pico_psi,
                mem_disponivel_min_mib=mem_disp_min,
            )
        )

    return resultados


def linhas_custo(metricas: Sequence[MetricaCustoFase]) -> str:
    """Gera linhas LaTeX para a tabela de custo de recursos."""
    linhas: list[str] = []
    por_escala: dict[int, list[MetricaCustoFase]] = defaultdict(list)
    for m in metricas:
        por_escala[m.n].append(m)

    for n in sorted(por_escala.keys()):
        rotulo_escala = formato_escala(n)
        itens = por_escala[n]
        k = len(itens)

        for idx, m in enumerate(itens):
            passo_tex = m.passo.replace("_", r"\_")
            p_mem = num(m.pico_mem_mib, 1)
            p_anon = num(m.pico_anon_mib, 1)
            cpu = num(m.cpu_nucleos, 1)
            sw = num(m.swap_out_mib, 1)

            if idx == 0:
                linhas.append(
                    f"\\multirow{{{k}}}{{*}}{{{rotulo_escala}}}\n"
                    f" & {m.sistema} & {passo_tex} & {p_mem} & {p_anon} & {cpu} & {sw} \\\\"
                )
            else:
                linhas.append(
                    f" & {m.sistema} & {passo_tex} & {p_mem} & {p_anon} & {cpu} & {sw} \\\\"
                )
        linhas.append(r"\hline")

    return "\n".join(linhas) + "\n"
