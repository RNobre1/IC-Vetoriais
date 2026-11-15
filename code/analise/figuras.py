"""Geração de figuras vetoriais em PDF a partir dos resultados da sessão.

Diretrizes visuais:
- Saída em PDF vetorial com largura fixa de 16 cm (ajustada para largura útil da página A4)
- Tipografia sans-serif (Helvetica/Arial/DejaVu Sans) a 9 pt
- Fundo branco limpo, grade cinza clara sutil
- Sem título interno nas figuras (o caption LaTeX atua como título)
- Mapeamento estrito e imutável de cores e marcadores por sistema:
  - pgvector: `#2a78d6`, círculo ('o')
  - Qdrant: `#eb6834`, quadrado ('s')
  - Weaviate: `#1baf7a`, triângulo ('^')
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from analise.custo import CONTAINER_POR_SISTEMA
from analise.formato import formato_escala
from analise.sessao import Sessao, normalizar_timestamp

LARGURA_CM = 16.0
POLEGADA_CM = 2.54
LARGURA_POL = LARGURA_CM / POLEGADA_CM

ESTILO_SISTEMAS = {
    "pgvector": {"color": "#2a78d6", "marker": "o", "label": "pgvector"},
    "qdrant": {"color": "#eb6834", "marker": "s", "label": "Qdrant"},
    "weaviate": {"color": "#1baf7a", "marker": "^", "label": "Weaviate"},
}


def _configurar_eixo(ax: plt.Axes) -> None:
    """Aplica estilo padrão ao eixo."""
    ax.set_facecolor("white")
    ax.grid(True, linestyle="--", linewidth=0.5, color="#e0e0e0", alpha=0.7)
    for spine in ax.spines.values():
        spine.set_color("#666666")
        spine.set_linewidth(0.8)
    ax.tick_params(colors="#333333", labelsize=8)


def fig_recall_qps(
    sessao: Sessao,
    escalas: Sequence[int],
    *,
    caminho_saida: str | Path | None = None,
) -> Figure:
    """Gera figura recall@10 × QPS com um painel por escala lado a lado."""
    plt.rcParams.update({"font.size": 9, "font.sans-serif": ["Helvetica", "Arial", "sans-serif"]})

    n_paineis = max(1, len(escalas))
    fig, eixos = plt.subplots(
        nrows=1,
        ncols=n_paineis,
        figsize=(LARGURA_POL, 6.0 / POLEGADA_CM),
        sharey=False,
    )
    if n_paineis == 1:
        eixos = [eixos]

    fig.patch.set_facecolor("white")

    for ax, n in zip(eixos, escalas, strict=False):
        _configurar_eixo(ax)
        ax.set_title(formato_escala(n), fontsize=9, fontweight="bold", pad=6)
        ax.set_xlim(0.84, 1.005)
        ax.set_yscale("log")
        ax.set_xlabel("Recall@10", fontsize=9)
        ax.set_ylabel("QPS (log)", fontsize=9)

        for sis, estilo in ESTILO_SISTEMAS.items():
            arq = sessao.obter("A", sis, n)
            if not arq or not arq.pontos:
                continue

            pontos = sorted(
                arq.pontos,
                key=lambda p: p.get("parametros", {}).get("ef_search", 0),
            )
            recalls = [p["metricas"]["recall_at_k"] for p in pontos]
            qps_vals = [p["metricas"]["qps"] for p in pontos]

            yerr_inf = []
            yerr_sup = []
            for p in pontos:
                reps = p["metricas"].get("repeticoes")
                if reps and len(reps) > 1:
                    qs = [r["qps"] for r in reps if "qps" in r]
                    yerr_inf.append(p["metricas"]["qps"] - min(qs))
                    yerr_sup.append(max(qs) - p["metricas"]["qps"])
                else:
                    yerr_inf.append(0.0)
                    yerr_sup.append(0.0)

            tem_erro = any(e > 0 for e in yerr_inf + yerr_sup)
            if tem_erro:
                ax.errorbar(
                    recalls,
                    qps_vals,
                    yerr=[yerr_inf, yerr_sup],
                    fmt=f"{estilo['marker']}-",
                    color=estilo["color"],
                    linewidth=1.5,
                    markersize=5,
                    capsize=2,
                    label=estilo["label"],
                )
            else:
                ax.plot(
                    recalls,
                    qps_vals,
                    f"{estilo['marker']}-",
                    color=estilo["color"],
                    linewidth=1.5,
                    markersize=5,
                    label=estilo["label"],
                )

            # Rótulo direto na ponta da curva
            if recalls and qps_vals:
                ax.annotate(
                    estilo["label"],
                    (recalls[-1], qps_vals[-1]),
                    textcoords="offset points",
                    xytext=(4, 0),
                    fontsize=7,
                    color=estilo["color"],
                    va="center",
                )

        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(fontsize=8, loc="lower left", framealpha=0.9)

    fig.tight_layout()
    if caminho_saida:
        p = Path(caminho_saida)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, format="pdf", bbox_inches="tight")
    return fig


def fig_cenario_c(
    sessao: Sessao,
    n: int,
    *,
    caminho_saida: str | Path | None = None,
) -> Figure:
    """Gera figura de 2 painéis para o Cenário C (latência p99 e recall inferior por janela)."""
    plt.rcParams.update({"font.size": 9, "font.sans-serif": ["Helvetica", "Arial", "sans-serif"]})

    fig, (ax1, ax2) = plt.subplots(
        nrows=1,
        ncols=2,
        figsize=(LARGURA_POL, 6.0 / POLEGADA_CM),
    )
    fig.patch.set_facecolor("white")
    _configurar_eixo(ax1)
    _configurar_eixo(ax2)

    rotulos_x = ["0", "10", "100", "1000", "0", "0*"]

    for sis, estilo in ESTILO_SISTEMAS.items():
        arq = sessao.obter("C", sis, n)
        if not arq or not arq.pontos:
            continue

        pontos = sorted(
            arq.pontos,
            key=lambda p: p.get("parametros", {}).get("ordem_janela", 0),
        )
        x_indices = list(range(len(pontos)))
        p99s = [p["metricas"].get("p99", 0) for p in pontos]
        recs = [p["metricas"].get("recall_inferior", 0) for p in pontos]

        ax1.plot(
            x_indices,
            p99s,
            f"{estilo['marker']}-",
            color=estilo["color"],
            linewidth=1.5,
            markersize=5,
            label=estilo["label"],
        )
        ax2.plot(
            x_indices,
            recs,
            f"{estilo['marker']}-",
            color=estilo["color"],
            linewidth=1.5,
            markersize=5,
            label=estilo["label"],
        )

    ax1.set_xticks(range(len(rotulos_x)))
    ax1.set_xticklabels(rotulos_x)
    ax1.set_ylabel("Latência p99 (ms)", fontsize=9)
    ax1.set_xlabel("Taxa alvo (ins/s)", fontsize=9)
    h1, l1 = ax1.get_legend_handles_labels()
    if h1:
        ax1.legend(fontsize=8, loc="best", framealpha=0.9)

    ax2.set_xticks(range(len(rotulos_x)))
    ax2.set_xticklabels(rotulos_x)
    ax2.set_ylabel("Recall inferior", fontsize=9)
    ax2.set_xlabel("Taxa alvo (ins/s)", fontsize=9)
    h2, l2 = ax2.get_legend_handles_labels()
    if h2:
        ax2.legend(fontsize=8, loc="best", framealpha=0.9)

    fig.tight_layout()
    if caminho_saida:
        p = Path(caminho_saida)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, format="pdf", bbox_inches="tight")
    return fig


def fig_memoria(
    monitor_csv: str | Path,
    marcos: str | Path | Sequence[dict[str, Any]],
    n: int,
    *,
    caminho_saida: str | Path | None = None,
) -> Figure:
    """Gera figura de memória (mem_current e anon em MiB) por sistema ao longo do tempo."""
    plt.rcParams.update({"font.size": 9, "font.sans-serif": ["Helvetica", "Arial", "sans-serif"]})

    # Carrega marcos
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

    # Identifica fases para a escala n
    fases_por_sistema: dict[str, list[tuple[str, datetime, datetime]]] = {
        sis: [] for sis in ESTILO_SISTEMAS
    }
    inicios: dict[tuple[str, str], datetime] = {}

    for m in marcos_lista:
        if m.get("n") != n:
            continue
        sis = m.get("sistema", "").lower()
        if sis not in fases_por_sistema:
            continue
        passo = m.get("passo")
        evento = m.get("evento")
        ts_raw = m.get("ts_utc")
        if not passo or not evento or not ts_raw:
            continue
        ts = normalizar_timestamp(ts_raw)
        if evento == "inicio":
            inicios[(sis, passo)] = ts
        elif evento == "fim" and (sis, passo) in inicios:
            t0 = inicios.pop((sis, passo))
            fases_por_sistema[sis].append((passo, t0, ts))

    # Carrega CSV
    amostras: list[dict[str, Any]] = []
    with Path(monitor_csv).open(encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            ts_str = linha.get("ts_utc")
            if not ts_str:
                continue
            linha["_dt"] = normalizar_timestamp(ts_str)
            amostras.append(linha)

    # Determina sistemas que possuem amostras/fases
    sistemas_ativos = [sis for sis in ESTILO_SISTEMAS if fases_por_sistema[sis] or amostras]
    if not sistemas_ativos:
        sistemas_ativos = list(ESTILO_SISTEMAS.keys())

    fig, eixos = plt.subplots(
        nrows=len(sistemas_ativos),
        ncols=1,
        figsize=(LARGURA_POL, 3.0 * len(sistemas_ativos) / POLEGADA_CM),
        sharex=False,
    )
    if len(sistemas_ativos) == 1:
        eixos = [eixos]
    fig.patch.set_facecolor("white")

    for ax, sis in zip(eixos, sistemas_ativos, strict=False):
        _configurar_eixo(ax)
        estilo = ESTILO_SISTEMAS[sis]
        c = CONTAINER_POR_SISTEMA.get(sis, sis)
        col_mem = f"{c}_mem_current_b"
        col_anon = f"{c}_anon_b"

        fases = fases_por_sistema.get(sis, [])
        if fases:
            t_bloco_inicio = min(f[1] for f in fases)
            t_bloco_fim = max(f[2] for f in fases)
            amostras_sis = [r for r in amostras if t_bloco_inicio <= r["_dt"] <= t_bloco_fim]
        else:
            t_bloco_inicio = amostras[0]["_dt"] if amostras else datetime.now()
            amostras_sis = amostras

        if amostras_sis and col_mem in amostras_sis[0]:
            ts_rel_min = [(r["_dt"] - t_bloco_inicio).total_seconds() / 60.0 for r in amostras_sis]
            mem_mib = [float(r[col_mem]) / 1048576.0 for r in amostras_sis]
            anon_mib = [float(r[col_anon]) / 1048576.0 for r in amostras_sis]

            ax.plot(
                ts_rel_min,
                mem_mib,
                color=estilo["color"],
                linewidth=1.5,
                label=f"{estilo['label']} Total",
            )
            ax.plot(
                ts_rel_min,
                anon_mib,
                color=estilo["color"],
                linestyle="--",
                linewidth=1.5,
                label=f"{estilo['label']} Anônima",
            )

        # Sombreamento das fases
        for i, (passo, t0, t1) in enumerate(fases):
            x0 = (t0 - t_bloco_inicio).total_seconds() / 60.0
            x1 = (t1 - t_bloco_inicio).total_seconds() / 60.0
            cor_fundo = "#f2f2f2" if i % 2 == 0 else "#e6e6e6"
            ax.axvspan(x0, x1, color=cor_fundo, alpha=0.5, zorder=0)
            ax.text(
                (x0 + x1) / 2.0,
                0.92,
                passo,
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="top",
                fontsize=7,
                color="#555555",
            )

        ax.set_ylabel("Memória (MiB)", fontsize=9)
        ax.set_xlabel("Tempo (min)", fontsize=9)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(fontsize=8, loc="upper right", framealpha=0.9)

    fig.tight_layout()
    if caminho_saida:
        p = Path(caminho_saida)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, format="pdf", bbox_inches="tight")
    return fig
