"""Agregação e cálculo de custos de recursos por fase da sessão experimental.

Cruza o log periódico do monitor (CSV a 1 Hz com memória, swap, CPU e pressão PSI)
com os marcos de fase (`marcos.jsonl`) para medir o consumo de cada passo.

Apenas passos de medição ou seed relevantes entram na tabela de custo:
`FASES_RELEVANTES = ("seed_a", "seed_b", "seed_b_eq", "A", "B", "B_eq", "C")`.
Passos operacionais auxiliares (`bloco`, `reiniciar`, `limpar`, `C_total`, `C_recall`,
`dados`, `btree`, `drop_btree`, `conectar`) são excluídos da tabela.

Se houver tentativas repetidas para o mesmo par (n, sistema, passo), utiliza-se
a ocorrência mais recente da fase.

Tolera células vazias no CSV geradas quando o serviço é recriado ou não expõe
certos contadores. Para contadores de CPU de contêineres que reiniciam, calcula a taxa
somando os trechos monotônicos válidos. Fases com menos de 2 amostras de CPU válidas
resultam em CPU `None` (exibida como "---").

A função `linhas_custo` formata essas grandezas no padrão tabular do relatório.
"""

from __future__ import annotations

import contextlib
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
from lib.footprint import CONTAINER_POR_SISTEMA

FASES_RELEVANTES = ("seed_a", "seed_b", "seed_b_eq", "A", "B", "B_eq", "C")

MAPA_SISTEMAS = {
    "pgvector": "pgvector",
    "qdrant": "Qdrant",
    "weaviate": "Weaviate",
}
SISTEMAS_ORDEM = ("pgvector", "Qdrant", "Weaviate")

ORDEM_FASES = ("seed_a", "seed_b", "seed_b_eq", "A", "B", "B_eq", "C")
MAPA_FASES = {
    "seed_a": "seed A",
    "seed_b": "seed B",
    "seed_b_eq": "seed B eq.",
    "A": "A",
    "a": "A",
    "B": "B",
    "b": "B",
    "B_eq": "B eq.",
    "b_eq": "B eq.",
    "C": "C",
    "c": "C",
}


def _ordem_fase_key(passo: str) -> int:
    p = passo
    for idx, f in enumerate(ORDEM_FASES):
        if f.lower() == p.lower():
            return idx
    return 99


def _ordem_sistema_key(sis: str) -> int:
    s_disp = MAPA_SISTEMAS.get(sis.lower(), sis)
    if s_disp in SISTEMAS_ORDEM:
        return SISTEMAS_ORDEM.index(s_disp)
    return 99


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
    swap_in_paginas: int | None = None
    swap_in_mib: float | None = None
    pico_psi_mem_full: float | None = None
    mem_disponivel_min_mib: float | None = None


def carregar_amostras_monitor(
    monitor_csv: str | Path | Sequence[str | Path] | None,
) -> list[dict[str, Any]]:
    """Carrega e ordena cronologicamente as amostras de monitor CSV."""
    if not monitor_csv:
        return []
    caminhos: list[Path] = []
    if isinstance(monitor_csv, str | Path):
        caminhos.append(Path(monitor_csv))
    else:
        caminhos.extend(Path(c) for c in monitor_csv)

    amostras: list[dict[str, Any]] = []
    for p in caminhos:
        if not p.is_file():
            continue
        with p.open(encoding="utf-8") as f:
            leitor = csv.DictReader(f)
            for linha in leitor:
                ts_str = linha.get("ts_utc")
                if not ts_str:
                    continue
                linha["_dt"] = normalizar_timestamp(ts_str)
                amostras.append(linha)
    amostras.sort(key=lambda r: r["_dt"])
    return amostras


def _tempo_segundos(r: dict[str, Any]) -> float:
    """Obtém tempo em segundos da amostra (preferencialmente t_mono_s)."""
    t_mono = r.get("t_mono_s")
    if t_mono is not None and str(t_mono).strip():
        with contextlib.suppress(ValueError):
            return float(t_mono)
    return r["_dt"].timestamp()


def _calcular_cpu_nucleos(linhas_validas: Sequence[dict[str, Any]], col_cpu: str) -> float | None:
    """Calcula CPU média em núcleos somando trechos monotônicos válidos.

    Se o contador reiniciar (valor menor que o anterior, contêiner recriado),
    divide em trechos contínuos monotônicos crescentes.
    Fases com menos de 2 amostras válidas retornam None.
    """
    pontos: list[tuple[float, float]] = []
    for r in linhas_validas:
        v = r.get(col_cpu)
        if v is not None and str(v).strip():
            try:
                usec = float(v)
                t = _tempo_segundos(r)
                pontos.append((t, usec))
            except ValueError:
                continue

    if len(pontos) < 2:
        return None

    # Agrupa em trechos monotônicos crescentes de usec
    dcpu_total = 0.0
    dt_total = 0.0
    t_inicio_trecho, usec_inicio_trecho = pontos[0]
    t_fim_trecho, usec_fim_trecho = pontos[0]

    for t, usec in pontos[1:]:
        if usec >= usec_fim_trecho:
            t_fim_trecho = t
            usec_fim_trecho = usec
        else:
            # Quebra de monotonicidade (repartição / reinício de contêiner)
            dt_trecho = t_fim_trecho - t_inicio_trecho
            if dt_trecho > 0:
                dcpu_total += max(0.0, usec_fim_trecho - usec_inicio_trecho)
                dt_total += dt_trecho
            t_inicio_trecho = t_fim_trecho = t
            usec_inicio_trecho = usec_fim_trecho = usec

    # Fecha último trecho
    dt_trecho = t_fim_trecho - t_inicio_trecho
    if dt_trecho > 0:
        dcpu_total += max(0.0, usec_fim_trecho - usec_inicio_trecho)
        dt_total += dt_trecho

    if dt_total <= 0:
        return None

    return dcpu_total / (dt_total * 1e6)


def calcular_custo(
    monitor_csv: str | Path | Sequence[str | Path] | Sequence[dict[str, Any]],
    marcos: str | Path | Sequence[dict[str, Any]],
    *,
    somente_relevantes: bool = True,
    amostras: Sequence[dict[str, Any]] | None = None,
) -> list[MetricaCustoFase]:
    """Cruza CSV(s) do monitor com marcos para derivar métricas de custo por fase.

    Args:
        monitor_csv: Caminho ou lista de caminhos para os CSVs do monitor,
            ou lista pré-carregada de amostras.
        marcos: Caminho para marcos.jsonl ou lista de dicionários.
        somente_relevantes: Se True, filtra apenas passos em FASES_RELEVANTES.
        amostras: Amostras já carregadas e indexadas com `_dt`.
    """
    marcos_lista: list[dict[str, Any]] = []
    if isinstance(marcos, str | Path):
        p_marcos = Path(marcos)
        if p_marcos.is_dir():
            p_marcos = p_marcos / "marcos.jsonl"
        for linha in p_marcos.read_text(encoding="utf-8").splitlines():
            s = linha.strip()
            if s:
                with contextlib.suppress(json.JSONDecodeError):
                    marcos_lista.append(json.loads(s))
    else:
        marcos_lista = list(marcos)

    # Identifica intervalos [t_inicio, t_fim] para cada (n, sistema, passo)
    inicios: dict[tuple[int, str, str], datetime] = {}
    intervalos_por_chave: dict[tuple[int, str, str], tuple[datetime, datetime]] = {}

    for m in marcos_lista:
        n = m.get("n")
        sis = m.get("sistema")
        passo = m.get("passo")
        evento = m.get("evento")
        ts_raw = m.get("ts_utc")

        if not n or not sis or not passo or not evento or not ts_raw:
            continue

        if somente_relevantes and passo not in FASES_RELEVANTES:
            continue

        ts = normalizar_timestamp(ts_raw)
        chave = (int(n), sis.lower(), passo)

        if evento == "inicio":
            inicios[chave] = ts
        elif evento == "fim" and chave in inicios:
            t0 = inicios.pop(chave)
            # Se já existir, a ocorrência posterior sobrescreve (tentativa mais recente)
            intervalos_por_chave[chave] = (t0, ts)

    # Resolve amostras
    amostras_lista: list[dict[str, Any]] = []
    if amostras is not None:
        amostras_lista = list(amostras)
    elif (
        isinstance(monitor_csv, Sequence)
        and len(monitor_csv) > 0
        and isinstance(monitor_csv[0], dict)
    ):
        amostras_lista = list(monitor_csv)  # type: ignore
    else:
        amostras_lista = carregar_amostras_monitor(monitor_csv)  # type: ignore

    resultados: list[MetricaCustoFase] = []

    # Mantém ordenação estável por n, sistema, passo
    for (n, sis, passo), (t0, t1) in sorted(intervalos_por_chave.items()):
        linhas_fase = [r for r in amostras_lista if t0 <= r["_dt"] <= t1]
        if not linhas_fase:
            # Fase sem nenhuma amostra registrada
            resultados.append(
                MetricaCustoFase(
                    n=n,
                    sistema=sis,
                    passo=passo,
                    pico_mem_mib=None,
                    pico_anon_mib=None,
                    cpu_nucleos=None,
                    swap_out_paginas=None,
                    swap_out_mib=None,
                    swap_in_paginas=None,
                    swap_in_mib=None,
                    pico_psi_mem_full=None,
                    mem_disponivel_min_mib=None,
                )
            )
            continue

        c = CONTAINER_POR_SISTEMA.get(sis, sis)
        col_mem = f"{c}_mem_current_b"
        col_anon = f"{c}_anon_b"
        col_cpu = f"{c}_cpu_usec"

        pico_mem = None
        mem_vals: list[float] = []
        for r in linhas_fase:
            v = r.get(col_mem)
            if v is not None and str(v).strip():
                with contextlib.suppress(ValueError):
                    mem_vals.append(float(v))
        if mem_vals:
            pico_mem = max(mem_vals) / 1048576.0

        pico_anon = None
        anon_vals: list[float] = []
        for r in linhas_fase:
            v = r.get(col_anon)
            if v is not None and str(v).strip():
                with contextlib.suppress(ValueError):
                    anon_vals.append(float(v))
        if anon_vals:
            pico_anon = max(anon_vals) / 1048576.0

        cpu_nucleos = _calcular_cpu_nucleos(linhas_fase, col_cpu)

        swap_paginas = None
        swap_mib = None
        swap_vals: list[int] = []
        for r in linhas_fase:
            v = r.get("pswpout")
            if v is not None and str(v).strip():
                with contextlib.suppress(ValueError):
                    swap_vals.append(int(v))
        if len(swap_vals) >= 2:
            dswap = max(0, swap_vals[-1] - swap_vals[0])
            swap_paginas = dswap
            swap_mib = (dswap * 4096.0) / 1048576.0

        swap_in_paginas = None
        swap_in_mib = None
        swap_in_vals: list[int] = []
        for r in linhas_fase:
            v = r.get("pswpin")
            if v is not None and str(v).strip():
                with contextlib.suppress(ValueError):
                    swap_in_vals.append(int(v))
        if len(swap_in_vals) >= 2:
            dswap_in = max(0, swap_in_vals[-1] - swap_in_vals[0])
            swap_in_paginas = dswap_in
            swap_in_mib = (dswap_in * 4096.0) / 1048576.0

        pico_psi = None
        psi_vals: list[float] = []
        for r in linhas_fase:
            v = r.get("psi_mem_full_avg10")
            if v is not None and str(v).strip():
                with contextlib.suppress(ValueError):
                    psi_vals.append(float(v))
        if psi_vals:
            pico_psi = max(psi_vals)

        mem_disp_min = None
        disp_vals: list[float] = []
        for r in linhas_fase:
            v = r.get("mem_available_kb")
            if v is not None and str(v).strip():
                with contextlib.suppress(ValueError):
                    disp_vals.append(float(v))
        if disp_vals:
            mem_disp_min = min(disp_vals) / 1024.0

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
                swap_in_paginas=swap_in_paginas,
                swap_in_mib=swap_in_mib,
                pico_psi_mem_full=pico_psi,
                mem_disponivel_min_mib=mem_disp_min,
            )
        )

    return resultados


def linhas_custo(
    metricas: Sequence[MetricaCustoFase],
    *,
    escala: int | None = None,
    incluir_escala: bool = True,
) -> str:
    r"""Gera linhas LaTeX para a tabela de custo de recursos.

    Args:
        metricas: Amostras agregadas de custo por fase.
        escala: Se informado, filtra apenas as métricas desta escala.
        incluir_escala: Se True, inclui a primeira coluna com multirow da escala
            (formato da tabela consolidada tab_custo.tex com \cline{2-9}).
            Se False, omite a coluna de escala e começa diretamente no multirow
            do sistema (formato por escala tab_custo_<n>.tex com \hline).
    """
    linhas: list[str] = []
    por_escala: dict[int, list[MetricaCustoFase]] = defaultdict(list)
    for m in metricas:
        if escala is None or m.n == escala:
            por_escala[m.n].append(m)

    for n in sorted(por_escala.keys()):
        rotulo_escala = formato_escala(n)
        itens_escala = por_escala[n]

        # Agrupa por sistema
        por_sistema: dict[str, list[MetricaCustoFase]] = defaultdict(list)
        for m in itens_escala:
            por_sistema[m.sistema].append(m)

        sistemas_ordenados = sorted(por_sistema.keys(), key=_ordem_sistema_key)

        # Ordena as fases dentro de cada sistema
        sistemas_com_fases: list[tuple[str, list[MetricaCustoFase]]] = []
        total_linhas_escala = 0
        for sis in sistemas_ordenados:
            fases = sorted(por_sistema[sis], key=lambda m: _ordem_fase_key(m.passo))
            sistemas_com_fases.append((sis, fases))
            total_linhas_escala += len(fases)

        if total_linhas_escala == 0:
            continue

        primeira_linha_escala = True

        for idx_sis, (sis, fases) in enumerate(sistemas_com_fases):
            nome_sis_disp = MAPA_SISTEMAS.get(sis.lower(), sis)
            k_sis = len(fases)
            primeira_linha_sistema = True

            for m in fases:
                passo_tex = MAPA_FASES.get(m.passo, m.passo.replace("_", r"\_"))
                p_mem = num(m.pico_mem_mib, 1)
                p_anon = num(m.pico_anon_mib, 1)
                cpu = num(m.cpu_nucleos, 1)
                sw = num(m.swap_out_mib, 1)
                sw_in = num(m.swap_in_mib, 1)
                psi_mem = num(m.pico_psi_mem_full, 2)

                cols_dados = (
                    f"{passo_tex} & {p_mem} & {p_anon} & {cpu} & {sw} & {sw_in} & {psi_mem} \\\\"
                )

                if incluir_escala:
                    if primeira_linha_escala:
                        linhas.append(
                            f"\\multirow{{{total_linhas_escala}}}{{*}}{{{rotulo_escala}}}\n"
                            f" & \\multirow{{{k_sis}}}{{*}}{{{nome_sis_disp}}} & {cols_dados}"
                        )
                        primeira_linha_escala = False
                        primeira_linha_sistema = False
                    elif primeira_linha_sistema:
                        linhas.append(
                            f" & \\multirow{{{k_sis}}}{{*}}{{{nome_sis_disp}}} & {cols_dados}"
                        )
                        primeira_linha_sistema = False
                    else:
                        linhas.append(f" & & {cols_dados}")
                else:
                    if primeira_linha_sistema:
                        linhas.append(
                            f"\\multirow{{{k_sis}}}{{*}}{{{nome_sis_disp}}} & {cols_dados}"
                        )
                        primeira_linha_sistema = False
                    else:
                        linhas.append(f" & {cols_dados}")

            if incluir_escala:
                if idx_sis < len(sistemas_com_fases) - 1:
                    linhas.append(r"\cline{2-9}")
                else:
                    linhas.append(r"\hline")
            else:
                linhas.append(r"\hline")

    return "\n".join(linhas) + "\n"
