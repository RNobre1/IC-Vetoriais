"""Geração das linhas LaTeX dos corpos das tabelas do relatório final.

Este módulo implementa funções puras que recebem a sessão (e parâmetros) e
devolvem exclusivamente o corpo das linhas do tabular (sem o encapsulamento
externo `\\begin{table}`, legendas ou rótulos, cuja autoria textual cabe ao
orquestrador do relatório).

Todas as tabelas seguem o padrão tipográfico e numérico do relatório parcial:
- `\\hline` delimitando blocos lógicos (sistemas ou escalas).
- `\\multirow{k}{*}{...}` no primeiro elemento do bloco.
- Formatação numérica em português (vírgula decimal, ponto de milhar).
- Valores ausentes marcados como "---".
"""

from __future__ import annotations

import contextlib
import statistics
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from analise.custo import carregar_amostras_monitor
from analise.formato import formato_escala, num
from analise.sessao import Sessao, normalizar_timestamp

SISTEMAS_ORDEM = ("pgvector", "Qdrant", "Weaviate")
SELETIVIDADES = (0.01, 0.10, 0.50, 1.00)
SELETIVIDADES_LABEL = {0.01: r"1\%", 0.10: r"10\%", 0.50: r"50\%", 1.00: r"100\%"}


def linhas_recursos(sessao: Sessao, escalas: Sequence[int]) -> str:
    """Gera linhas da tabela de recursos (disco, b/vetor, RSS delta, tempo de índice).

    Fonte: arquivo Cenário A de cada par (escala, sistema).
    """
    linhas: list[str] = []

    for n in escalas:
        rotulo_escala = formato_escala(n)
        sublinhas: list[tuple[str, str, str, str, str]] = []

        for sis in SISTEMAS_ORDEM:
            arq = sessao.obter("A", sis, n)
            disco_total = None
            rss_delta = None
            t_indice = None

            if arq and arq.recursos:
                rec = arq.recursos
                disco_total = rec.get("disco", {}).get("total_bytes")
                rss_delta = rec.get("memoria_rss_delta_bytes")
                t_indice = rec.get("tempo_indice_utilizavel_s")

            disco_mib = disco_total / (1024 * 1024) if disco_total is not None else None
            b_vetor = (disco_total / n) if (disco_total is not None and n > 0) else None
            rss_mib = rss_delta / (1024 * 1024) if rss_delta is not None else None

            s_disco = num(disco_mib, 1)
            s_b_vetor = num(b_vetor, 0)
            s_rss = num(rss_mib, 1)
            s_indice = num(t_indice, 1)

            sublinhas.append((sis, s_disco, s_b_vetor, s_rss, s_indice))

        k = len(sublinhas)
        for idx, (sis, d, b, r, ti) in enumerate(sublinhas):
            if idx == 0:
                linhas.append(
                    f"\\multirow{{{k}}}{{*}}{{{rotulo_escala}}}\n"
                    f" & {sis} & {d} & {b} & {r} & {ti} \\\\"
                )
            else:
                linhas.append(f" & {sis} & {d} & {b} & {r} & {ti} \\\\")
        linhas.append(r"\hline")

    return "\n".join(linhas) + "\n"


def linhas_cenario_a(sessao: Sessao, n: int) -> str:
    """Gera linhas do Cenário A: recall, percentis de latência, QPS e amplitude p50."""
    linhas: list[str] = []

    for sis in SISTEMAS_ORDEM:
        arq = sessao.obter("A", sis, n)
        if not arq or not arq.pontos:
            continue

        pontos = sorted(
            arq.pontos,
            key=lambda p: p.get("parametros", {}).get("ef_search", 0),
        )
        k = len(pontos)

        for idx, p in enumerate(pontos):
            ef = p.get("parametros", {}).get("ef_search", "---")
            m = p.get("metricas", {})
            rec = num(m.get("recall_at_k"), 4)
            p50 = num(m.get("p50"), 2)
            p95 = num(m.get("p95"), 2)
            p99 = num(m.get("p99"), 2)
            qps = num(m.get("qps"), 1)

            reps = m.get("repeticoes")
            if reps and len(reps) > 1:
                p50s = [r["p50"] for r in reps if "p50" in r]
                mediana = m.get("p50") or statistics.median(p50s)
                amp = ((max(p50s) - min(p50s)) / mediana) * 100 if mediana > 0 else 0
                s_amp = num(amp, 0)
            else:
                s_amp = "---"

            if idx == 0:
                linhas.append(
                    f"\\multirow{{{k}}}{{*}}{{{sis}}}\n"
                    f" & {ef} & {rec} & {p50} & {p95} & {p99} & {qps} & {s_amp} \\\\"
                )
            else:
                linhas.append(f" & {ef} & {rec} & {p50} & {p95} & {p99} & {qps} & {s_amp} \\\\")
        linhas.append(r"\hline")

    return "\n".join(linhas) + "\n"


def _recall_invariante_a_ef(pontos: list[dict], sel: float) -> bool:
    """Verdadeiro se a seletividade foi medida em 2+ ef e o recall é o mesmo em todos."""
    recalls = [
        p.get("metricas", {}).get("recall_at_k")
        for p in pontos
        if abs(p.get("parametros", {}).get("seletividade", 0) - sel) < 1e-5
    ]
    recalls = [r for r in recalls if r is not None]
    return len(recalls) > 1 and max(recalls) - min(recalls) < 1e-12


def linhas_cenario_b(sessao: Sessao, n: int, ef: int = 64) -> str:
    """Gera linhas do Cenário B (padrão vs equalizado) para ef fixado (default 64)."""
    linhas: list[str] = []

    for sis in SISTEMAS_ORDEM:
        arq_padrao = sessao.obter("B_padrao", sis, n)
        arq_eq = sessao.obter("B_eq", sis, n)

        if not arq_padrao and not arq_eq:
            continue

        sublinhas: list[tuple[str, str, str, str, str]] = []

        for sel in SELETIVIDADES:
            sel_label = SELETIVIDADES_LABEL.get(sel, f"{sel:g}")

            pt_p = (
                next(
                    (
                        p
                        for p in (arq_padrao.pontos if arq_padrao else [])
                        if abs(p.get("parametros", {}).get("seletividade", 0) - sel) < 1e-5
                        and p.get("parametros", {}).get("ef_search") == ef
                    ),
                    None,
                )
                if arq_padrao
                else None
            )

            pt_e = (
                next(
                    (
                        p
                        for p in (arq_eq.pontos if arq_eq else [])
                        if abs(p.get("parametros", {}).get("seletividade", 0) - sel) < 1e-5
                        and p.get("parametros", {}).get("ef_search") == ef
                    ),
                    None,
                )
                if arq_eq
                else None
            )

            r_p = num(pt_p.get("metricas", {}).get("recall_at_k"), 4) if pt_p else "---"
            if pt_p and _recall_invariante_a_ef(arq_padrao.pontos, sel):
                # Recall que não responde a ef_search não vem do percurso do
                # grafo: é o atalho de varredura exata da condição padrão.
                r_p = rf"\textbf{{{r_p}}}"

            if pt_e:
                m_e = pt_e.get("metricas", {})
                r_e = num(m_e.get("recall_at_k"), 4)
                p50_e = num(m_e.get("p50"), 2)
                qps_e = num(m_e.get("qps"), 1)
            else:
                r_e = p50_e = qps_e = "---"

            sublinhas.append((sel_label, r_p, r_e, p50_e, qps_e))

        k = len(sublinhas)
        for idx, (label, rp, re, p50e, qpse) in enumerate(sublinhas):
            if idx == 0:
                linhas.append(
                    f"\\multirow{{{k}}}{{*}}{{{sis}}}\n"
                    f" & {label} & {rp} & {re} & {p50e} & {qpse} \\\\"
                )
            else:
                linhas.append(f" & {label} & {rp} & {re} & {p50e} & {qpse} \\\\")
        linhas.append(r"\hline")

    return "\n".join(linhas) + "\n"


def linhas_cenario_c(sessao: Sessao, n: int) -> str:
    """Gera linhas do Cenário C por janela (taxas, latências, recall e visibilidade)."""
    linhas: list[str] = []

    for sis in SISTEMAS_ORDEM:
        arq = sessao.obter("C", sis, n)
        if not arq or not arq.pontos:
            continue

        pontos = sorted(
            arq.pontos,
            key=lambda p: p.get("parametros", {}).get("ordem_janela", 0),
        )
        k = len(pontos)

        for idx, p in enumerate(pontos):
            params = p.get("parametros", {})
            m = p.get("metricas", {})
            amb = p.get("ambiente", {})

            ordem = params.get("ordem_janela", idx)
            janela_num = ordem + 1
            # Rótulo de janela: se houver assentar_s ou for a janela 6 com assentar, marca com *
            tem_assentamento = amb.get("assentar_s") is not None
            janela_str = f"{janela_num}*" if tem_assentamento else str(janela_num)

            taxa_alvo = num(params.get("taxa_alvo"), 0)
            taxa_sust = num(m.get("taxa_sustentada"), 0)
            p50 = num(m.get("p50"), 2)
            p99 = num(m.get("p99"), 2)
            qps = num(m.get("qps"), 1)

            rec_inf_val = m.get("recall_inferior")
            rec_sup_val = m.get("recall_superior")

            if rec_inf_val is None or rec_sup_val is None:
                # Um dos lados ausente -> não é intervalo completo
                rec_inf_sup = "---"
            else:
                inf = num(rec_inf_val, 4)
                sup = num(rec_sup_val, 4)
                rec_inf_sup = inf if inf == sup else f"{inf}--{sup}"

            rec_novos = m.get("recall_novos")
            n_gt = m.get("n_gt_novos", 0) or 0
            if rec_novos is not None and n_gt > 0:
                den_k = n_gt / 1000.0
                rec_novos_str = f"{num(rec_novos, 4)} ({num(den_k, 1)}k)"
            else:
                rec_novos_str = "---"

            vis = amb.get("visibilidade_fracao")
            vis_str = num(vis * 100, 0) if vis is not None else "---"

            if idx == 0:
                linhas.append(
                    f"\\multirow{{{k}}}{{*}}{{{sis}}}\n"
                    f" & {janela_str} & {taxa_alvo} & {taxa_sust} & {p50} & {p99} & {qps} & {rec_inf_sup} & {rec_novos_str} & {vis_str} \\\\"
                )
            else:
                linhas.append(
                    f" & {janela_str} & {taxa_alvo} & {taxa_sust} & {p50} & {p99} & {qps} & {rec_inf_sup} & {rec_novos_str} & {vis_str} \\\\"
                )
        linhas.append(r"\hline")

    return "\n".join(linhas) + "\n"


def linhas_cenario_c_hospedeiro(
    sessao: Sessao,
    n: int,
    amostras_monitor: Sequence[dict[str, Any]] | str | Path | Sequence[str | Path] | None = None,
) -> str:
    r"""Gera linhas da tabela de monitoramento do hospedeiro no Cenário C por janela.

    Para cada sistema e janela do Cenário C (intervalo [ambiente.inicio_utc, ambiente.fim_utc]):
    - Frequência média da CPU do hospedeiro (MHz, 0 casas, média de cpu_mhz_medio)
    - Ocupação média da CPU do hospedeiro em % (Δcpu_host_ocupado / Δcpu_host_total × 100, 0 casas)
    - Pico de psi_cpu_some_avg10 (2 casas)

    Colunas: Jan., Taxa alvo, MHz médio, CPU host (%), PSI CPU pico. Célula sem amostra -> ---.
    """
    amostras: list[dict[str, Any]] = []
    if amostras_monitor:
        if isinstance(amostras_monitor, str | Path):
            amostras = carregar_amostras_monitor(amostras_monitor)
        elif isinstance(amostras_monitor, Sequence) and len(amostras_monitor) > 0:
            if isinstance(amostras_monitor[0], dict):
                amostras = list(amostras_monitor)
            else:
                amostras = carregar_amostras_monitor(amostras_monitor)  # type: ignore

    for r in amostras:
        if "_dt" not in r and "ts_utc" in r:
            r["_dt"] = normalizar_timestamp(r["ts_utc"])

    linhas: list[str] = []

    for sis in SISTEMAS_ORDEM:
        arq = sessao.obter("C", sis, n)
        if not arq or not arq.pontos:
            continue

        pontos = sorted(
            arq.pontos,
            key=lambda p: p.get("parametros", {}).get("ordem_janela", 0),
        )
        k = len(pontos)

        for idx, p in enumerate(pontos):
            params = p.get("parametros", {})
            amb = p.get("ambiente", {})

            ordem = params.get("ordem_janela", idx)
            janela_num = ordem + 1
            tem_assentamento = amb.get("assentar_s") is not None
            janela_str = f"{janela_num}*" if tem_assentamento else str(janela_num)

            taxa_alvo = num(params.get("taxa_alvo"), 0)

            t0_str = amb.get("inicio_utc")
            t1_str = amb.get("fim_utc")

            pts: list[dict[str, Any]] = []
            if t0_str and t1_str and amostras:
                t0 = normalizar_timestamp(t0_str)
                t1 = normalizar_timestamp(t1_str)
                pts = [r for r in amostras if t0 <= r["_dt"] <= t1]

            # 1. MHz médio (0 casas)
            mhz_vals: list[float] = []
            for r in pts:
                v = r.get("cpu_mhz_medio")
                if v is not None and str(v).strip():
                    with contextlib.suppress(ValueError):
                        mhz_vals.append(float(v))
            mhz_medio = sum(mhz_vals) / len(mhz_vals) if mhz_vals else None
            mhz_str = num(mhz_medio, 0)

            # 2. CPU host % (0 casas)
            ocup_pct = None
            if len(pts) >= 2:
                with contextlib.suppress(ValueError):
                    docup = float(pts[-1]["cpu_host_ocupado"]) - float(pts[0]["cpu_host_ocupado"])
                    dtotal = float(pts[-1]["cpu_host_total"]) - float(pts[0]["cpu_host_total"])
                    if dtotal > 0:
                        ocup_pct = (docup / dtotal) * 100.0
            ocup_str = num(ocup_pct, 0)

            # 3. PSI CPU pico (2 casas)
            psi_vals: list[float] = []
            for r in pts:
                v = r.get("psi_cpu_some_avg10")
                if v is not None and str(v).strip():
                    with contextlib.suppress(ValueError):
                        psi_vals.append(float(v))
            psi_pico = max(psi_vals) if psi_vals else None
            psi_str = num(psi_pico, 2)

            cols_dados = f"{janela_str} & {taxa_alvo} & {mhz_str} & {ocup_str} & {psi_str} \\\\"

            if idx == 0:
                linhas.append(f"\\multirow{{{k}}}{{*}}{{{sis}}}\n" f" & {cols_dados}")
            else:
                linhas.append(f" & {cols_dados}")
        linhas.append(r"\hline")

    return "\n".join(linhas) + "\n" if linhas else ""


def linhas_ponte(sessao: Sessao, ef: int = 64) -> str:
    """Gera linhas da ponte de protocolo (Cenário A em 100k, anterior vs nova sessão)."""
    linhas: list[str] = []

    for sis in SISTEMAS_ORDEM:
        arq_ponte = sessao.obter("A_ponte", sis, 100000)
        arq_nova = sessao.obter("A", sis, 100000)

        pt_p = (
            next(
                (p for p in arq_ponte.pontos if p.get("parametros", {}).get("ef_search") == ef),
                None,
            )
            if arq_ponte
            else None
        )
        pt_n = (
            next(
                (p for p in arq_nova.pontos if p.get("parametros", {}).get("ef_search") == ef),
                None,
            )
            if arq_nova
            else None
        )

        rec_p = num(pt_p.get("metricas", {}).get("recall_at_k"), 4) if pt_p else "---"
        p50_p = num(pt_p.get("metricas", {}).get("p50"), 2) if pt_p else "---"
        qps_p = num(pt_p.get("metricas", {}).get("qps"), 1) if pt_p else "---"

        rec_n = num(pt_n.get("metricas", {}).get("recall_at_k"), 4) if pt_n else "---"
        p50_n = num(pt_n.get("metricas", {}).get("p50"), 2) if pt_n else "---"
        qps_n = num(pt_n.get("metricas", {}).get("qps"), 1) if pt_n else "---"

        linhas.append(f"{sis} & {rec_p} & {p50_p} & {qps_p} & {rec_n} & {p50_n} & {qps_n} \\\\")
    linhas.append(r"\hline")

    return "\n".join(linhas) + "\n"


def linhas_reprodutibilidade(
    sessao: Sessao,
    anterior: Sessao,
    ef: int = 64,
) -> str:
    """Gera linhas de reprodutibilidade (100k e 500k, 23/08 vs nova sessão)."""
    linhas: list[str] = []

    for n in (100000, 500000):
        rotulo = formato_escala(n)
        sublinhas: list[tuple[str, str, str, str, str, str]] = []

        for sis in SISTEMAS_ORDEM:
            arq_ant = anterior.obter("A", sis, n)
            arq_nov = sessao.obter("A", sis, n)

            pt_a = (
                next(
                    (p for p in arq_ant.pontos if p.get("parametros", {}).get("ef_search") == ef),
                    None,
                )
                if arq_ant
                else None
            )
            pt_n = (
                next(
                    (p for p in arq_nov.pontos if p.get("parametros", {}).get("ef_search") == ef),
                    None,
                )
                if arq_nov
                else None
            )

            rec_a = num(pt_a.get("metricas", {}).get("recall_at_k"), 4) if pt_a else "---"
            qps_a_val = pt_a.get("metricas", {}).get("qps") if pt_a else None
            qps_a = num(qps_a_val, 1)

            rec_n = num(pt_n.get("metricas", {}).get("recall_at_k"), 4) if pt_n else "---"
            qps_n_val = pt_n.get("metricas", {}).get("qps") if pt_n else None
            qps_n = num(qps_n_val, 1)

            razao_val = (
                (qps_n_val / qps_a_val)
                if (qps_n_val is not None and qps_a_val and qps_a_val > 0)
                else None
            )
            razao = num(razao_val, 2)

            sublinhas.append((sis, rec_a, qps_a, rec_n, qps_n, razao))

        k = len(sublinhas)
        for idx, (sis, ra, qa, rn, qn, rz) in enumerate(sublinhas):
            if idx == 0:
                linhas.append(
                    f"\\multirow{{{k}}}{{*}}{{{rotulo}}}\n"
                    f" & {sis} & {ra} & {qa} & {rn} & {qn} & {rz} \\\\"
                )
            else:
                linhas.append(f" & {sis} & {ra} & {qa} & {rn} & {qn} & {rz} \\\\")
        linhas.append(r"\hline")

    return "\n".join(linhas) + "\n"


def linhas_controle_weaviate(sessao: Sessao, n: int) -> str:
    """Gera linhas de controle do Weaviate em p=10% (|recall padrao - eq| <= 0.005)."""
    arq_padrao = sessao.obter("B_padrao", "weaviate", n)
    arq_eq = sessao.obter("B_eq", "weaviate", n)

    pts_p = (
        [
            p
            for p in arq_padrao.pontos
            if abs(p.get("parametros", {}).get("seletividade", -1) - 0.10) < 1e-4
        ]
        if arq_padrao
        else []
    )
    pts_e = (
        [
            p
            for p in arq_eq.pontos
            if abs(p.get("parametros", {}).get("seletividade", -1) - 0.10) < 1e-4
        ]
        if arq_eq
        else []
    )

    efs = sorted(
        {
            p.get("parametros", {}).get("ef_search")
            for p in pts_p + pts_e
            if p.get("parametros", {}).get("ef_search") is not None
        }
    )

    linhas: list[str] = []
    for ef in efs:
        pt_p = next((p for p in pts_p if p.get("parametros", {}).get("ef_search") == ef), None)
        pt_e = next((p for p in pts_e if p.get("parametros", {}).get("ef_search") == ef), None)

        r_p = pt_p.get("metricas", {}).get("recall_at_k") if pt_p else None
        r_e = pt_e.get("metricas", {}).get("recall_at_k") if pt_e else None
        delta = abs(r_p - r_e) if (r_p is not None and r_e is not None) else None
        atende = ("Sim" if delta <= 0.005 else "Não") if delta is not None else "---"

        linhas.append(f"{ef} & {num(r_p, 4)} & {num(r_e, 4)} & {num(delta, 4)} & {atende} \\\\")
    linhas.append(r"\hline")

    return "\n".join(linhas) + "\n"
