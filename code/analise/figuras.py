"""Geração de figuras vetoriais em PDF a partir dos resultados da sessão.

Diretrizes visuais:
- Saída em PDF vetorial com largura fixa de 16 cm (ajustada para largura útil da página A4)
- Tipografia sans-serif (Helvetica/Arial/DejaVu Sans) a 9 pt
- Fundo branco limpo, grade cinza clara sutil
- Sem título interno nas figuras (o caption LaTeX atua como título)
- Formatação de eixos com vírgula decimal (padrão PT-BR)
- Legenda fora da área das curvas para evitar sobreposição
- Mapeamento estrito e imutável de cores e marcadores por sistema:
  - pgvector: `#2a78d6`, círculo ('o')
  - Qdrant: `#eb6834`, quadrado ('s')
  - Weaviate: `#1baf7a`, triângulo ('^')
"""

from __future__ import annotations

import contextlib
import csv
import json
import math
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

from analise.formato import num
from analise.sessao import Sessao, normalizar_timestamp
from lib.footprint import CONTAINER_POR_SISTEMA

LARGURA_CM = 16.0
POLEGADA_CM = 2.54
LARGURA_POL = LARGURA_CM / POLEGADA_CM

ESTILO_SISTEMAS = {
    "pgvector": {"color": "#2a78d6", "marker": "o", "label": "pgvector"},
    "qdrant": {"color": "#eb6834", "marker": "s", "label": "Qdrant"},
    "weaviate": {"color": "#1baf7a", "marker": "^", "label": "Weaviate"},
}

MAPA_SISTEMAS = {
    "pgvector": "pgvector",
    "qdrant": "Qdrant",
    "weaviate": "Weaviate",
}

FASES_RELEVANTES_MEMORIA = {
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


def formato_escala_extenso(n: int) -> str:
    """Formata escala por extenso (ex: 100 mil vetores, 1 milhão de vetores)."""
    if n == 1_000_000:
        return "1 milhão de vetores"
    if n >= 1_000_000 and n % 1_000_000 == 0:
        return f"{n // 1_000_000} milhões de vetores"
    if n >= 1_000 and n % 1_000 == 0:
        return f"{n // 1_000} mil vetores"
    return f"{n} vetores"


def _formatador_pt_br(val: float, pos: int) -> str:
    """Formata ticks dos eixos substituindo ponto decimal por vírgula."""
    if val.is_integer():
        return f"{int(val):,}".replace(",", ".")
    s = f"{val:g}"
    return s.replace(".", ",")


def _configurar_eixo(ax: plt.Axes) -> None:
    """Aplica estilo padrão ao eixo."""
    ax.set_facecolor("white")
    ax.grid(True, linestyle="--", linewidth=0.5, color="#e0e0e0", alpha=0.7)
    for spine in ax.spines.values():
        spine.set_color("#666666")
        spine.set_linewidth(0.8)
    ax.tick_params(colors="#333333", labelsize=8)
    formatter = FuncFormatter(_formatador_pt_br)
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(formatter)


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
        figsize=(LARGURA_POL, 7.5 / POLEGADA_CM),
        sharey=False,
    )
    if n_paineis == 1:
        eixos = [eixos]

    fig.patch.set_facecolor("white")

    for ax, n in zip(eixos, escalas, strict=False):
        _configurar_eixo(ax)
        ax.set_title(formato_escala_extenso(n), fontsize=9, fontweight="bold", pad=6)
        ax.set_yscale("log")
        ax.set_xlabel("Recall@10", fontsize=9)
        ax.set_ylabel("QPS (escala log)", fontsize=9)

        min_recall_medido = 0.84
        pontas: list[dict[str, Any]] = []

        for sis, estilo in ESTILO_SISTEMAS.items():
            arq = sessao.obter("A", sis, n)
            if not arq or not arq.pontos:
                continue

            pontos = sorted(
                arq.pontos,
                key=lambda p: p.get("parametros", {}).get("ef_search", 0),
            )
            recalls = [
                p["metricas"]["recall_at_k"]
                for p in pontos
                if p["metricas"].get("recall_at_k") is not None
            ]
            qps_vals = [
                p["metricas"]["qps"] for p in pontos if p["metricas"].get("recall_at_k") is not None
            ]

            if recalls:
                min_recall_medido = min(min_recall_medido, min(recalls))

            yerr_inf = []
            yerr_sup = []
            for p in pontos:
                if p["metricas"].get("recall_at_k") is None:
                    continue
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

            if recalls and qps_vals:
                pontas.append(
                    {
                        "x": recalls[-1],
                        "y": qps_vals[-1],
                        "label": estilo["label"],
                        "color": estilo["color"],
                    }
                )

        # Evita colisão nos rótulos diretos da ponta da curva
        for pt in pontas:
            dx, dy = 6, 2
            for other in pontas:
                if other is not pt and abs(pt["x"] - other["x"]) < 0.03:
                    diff_log_y = math.log10(pt["y"]) - math.log10(other["y"])
                    if 0 <= diff_log_y < 0.15:
                        dy = 8
                    elif -0.15 < diff_log_y < 0:
                        dy = -5
            ax.annotate(
                pt["label"],
                (pt["x"], pt["y"]),
                textcoords="offset points",
                xytext=(dx, dy),
                fontsize=7,
                color=pt["color"],
                va="center",
            )

        limite_inf_x = max(0.0, min_recall_medido - 0.02)
        ax.set_xlim(limite_inf_x, 1.005)

    # Legenda única da figura abaixo de tudo, sem sobrepor os eixos x
    handles_unicos: list[Any] = []
    labels_unicos: list[str] = []
    for ax in eixos:
        handles, labels_list = ax.get_legend_handles_labels()
        for handle, label in zip(handles, labels_list, strict=False):
            if label not in labels_unicos:
                handles_unicos.append(handle)
                labels_unicos.append(label)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.26)
    if handles_unicos:
        fig.legend(
            handles_unicos,
            labels_unicos,
            loc="lower center",
            ncol=3,
            bbox_to_anchor=(0.5, 0.0),
            fontsize=9,
            frameon=False,
        )

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
        figsize=(LARGURA_POL, 7.5 / POLEGADA_CM),
    )
    fig.patch.set_facecolor("white")
    _configurar_eixo(ax1)
    _configurar_eixo(ax2)

    # Identifica pontos de qualquer sistema para derivar eixos x
    pontos_referencia: list[dict[str, Any]] = []
    for sis in ESTILO_SISTEMAS:
        arq = sessao.obter("C", sis, n)
        if arq and arq.pontos and len(arq.pontos) > len(pontos_referencia):
            pontos_referencia = sorted(
                arq.pontos,
                key=lambda p: p.get("parametros", {}).get("ordem_janela", 0),
            )

    rotulos_x: list[str] = []
    for p in pontos_referencia:
        taxa = p.get("parametros", {}).get("taxa_alvo", 0)
        amb = p.get("ambiente", {})
        rotulo_taxa = num(taxa, 0)
        if amb.get("assentar_s") is not None:
            rotulo_taxa = f"{rotulo_taxa}*"
        rotulos_x.append(rotulo_taxa)

    if not rotulos_x:
        rotulos_x = ["0", "10", "100", "1.000", "0", "0*"]

    for sis, estilo in ESTILO_SISTEMAS.items():
        arq = sessao.obter("C", sis, n)
        if not arq or not arq.pontos:
            continue

        pontos = sorted(
            arq.pontos,
            key=lambda p: p.get("parametros", {}).get("ordem_janela", 0),
        )

        x_indices_p99: list[int] = []
        p99s: list[float] = []
        x_indices_rec: list[int] = []
        recs: list[float] = []

        for idx, p in enumerate(pontos):
            ordem = p.get("parametros", {}).get("ordem_janela", idx)
            m = p.get("metricas", {})
            p99_val = m.get("p99")
            if p99_val is not None:
                x_indices_p99.append(ordem)
                p99s.append(float(p99_val))

            rec_val = m.get("recall_inferior")
            # Recall ausente NUNCA é plotado como 0
            if rec_val is not None:
                x_indices_rec.append(ordem)
                recs.append(float(rec_val))

        if x_indices_p99:
            ax1.plot(
                x_indices_p99,
                p99s,
                f"{estilo['marker']}-",
                color=estilo["color"],
                linewidth=1.5,
                markersize=5,
                label=estilo["label"],
            )
        if x_indices_rec:
            ax2.plot(
                x_indices_rec,
                recs,
                f"{estilo['marker']}-",
                color=estilo["color"],
                linewidth=1.5,
                markersize=5,
                label=estilo["label"],
            )

    # Linha vertical tracejada cinza entre janela 4 e 5 (x=3.5) indicando fim da escrita
    ax1.axvline(3.5, color="#888888", linestyle="--", linewidth=1.0, alpha=0.7)
    ax2.axvline(3.5, color="#888888", linestyle="--", linewidth=1.0, alpha=0.7)

    ax1.set_xticks(range(len(rotulos_x)))
    ax1.set_xticklabels(rotulos_x)
    ax1.set_ylabel("Latência p99 (ms)", fontsize=9)
    ax1.set_xlabel("Janela (taxa alvo, ins/s)", fontsize=9)

    ax2.set_xticks(range(len(rotulos_x)))
    ax2.set_xticklabels(rotulos_x)
    ax2.set_ylabel("Recall@10 (limite inferior)", fontsize=9)
    ax2.set_xlabel("Janela (taxa alvo, ins/s)", fontsize=9)

    # Legenda única abaixo dos painéis
    handles_unicos: list[Any] = []
    labels_unicos: list[str] = []
    for ax in (ax1, ax2):
        handles, labels_list = ax.get_legend_handles_labels()
        for handle, label in zip(handles, labels_list, strict=False):
            if label not in labels_unicos:
                handles_unicos.append(handle)
                labels_unicos.append(label)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.26)
    if handles_unicos:
        fig.legend(
            handles_unicos,
            labels_unicos,
            loc="lower center",
            ncol=3,
            bbox_to_anchor=(0.5, 0.0),
            fontsize=9,
            frameon=False,
        )

    if caminho_saida:
        p = Path(caminho_saida)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, format="pdf", bbox_inches="tight")
    return fig


def fig_memoria(
    monitor_csv: str | Path | Sequence[str | Path],
    marcos: str | Path | Sequence[dict[str, Any]],
    n: int,
    *,
    caminho_saida: str | Path | None = None,
) -> Figure:
    """Gera figura temporal de memória (memory.current e anon) com sombreamento por fase."""
    plt.rcParams.update({"font.size": 9, "font.sans-serif": ["Helvetica", "Arial", "sans-serif"]})

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

    # Carrega CSV(s)
    caminhos_csv: list[Path] = []
    if isinstance(monitor_csv, str | Path):
        caminhos_csv.append(Path(monitor_csv))
    else:
        caminhos_csv.extend(Path(c) for c in monitor_csv)

    amostras: list[dict[str, Any]] = []
    for p_csv in caminhos_csv:
        if not p_csv.is_file():
            continue
        with p_csv.open(encoding="utf-8") as f:
            leitor = csv.DictReader(f)
            for linha in leitor:
                ts_str = linha.get("ts_utc")
                if not ts_str:
                    continue
                linha["_dt"] = normalizar_timestamp(ts_str)
                amostras.append(linha)

    amostras.sort(key=lambda r: r["_dt"])

    # Determina sistemas que possuem amostras/fases
    sistemas_ativos = [sis for sis in ESTILO_SISTEMAS if fases_por_sistema[sis] or amostras]
    if not sistemas_ativos:
        sistemas_ativos = list(ESTILO_SISTEMAS.keys())

    altura_total = max(8.0, (3.5 * len(sistemas_ativos) + 1.8)) / POLEGADA_CM
    fig, eixos = plt.subplots(
        nrows=len(sistemas_ativos),
        ncols=1,
        figsize=(LARGURA_POL, altura_total),
        sharex=False,
    )
    if len(sistemas_ativos) == 1:
        eixos = [eixos]
    fig.patch.set_facecolor("white")

    for idx, (ax, sis) in enumerate(zip(eixos, sistemas_ativos, strict=False)):
        _configurar_eixo(ax)
        estilo = ESTILO_SISTEMAS[sis]
        c = CONTAINER_POR_SISTEMA.get(sis, sis)
        col_mem = f"{c}_mem_current_b"
        col_anon = f"{c}_anon_b"

        # Título do painel = nome do sistema de exibição
        nome_sistema_disp = MAPA_SISTEMAS.get(sis.lower(), estilo["label"])
        ax.set_title(nome_sistema_disp, fontsize=9, fontweight="bold", pad=4)

        fases = fases_por_sistema.get(sis, [])
        if fases:
            t_bloco_inicio = min(f[1] for f in fases)
            t_bloco_fim = max(f[2] for f in fases)
            amostras_sis = [r for r in amostras if t_bloco_inicio <= r["_dt"] <= t_bloco_fim]
        else:
            t_bloco_inicio = amostras[0]["_dt"] if amostras else datetime.now()
            amostras_sis = amostras

        # Filtra apenas amostras com valores válidos (pula células vazias)
        amostras_validas = []
        for r in amostras_sis:
            vm = r.get(col_mem)
            va = r.get(col_anon)
            if vm is not None and str(vm).strip() and va is not None and str(va).strip():
                with contextlib.suppress(ValueError):
                    amostras_validas.append((r["_dt"], float(vm), float(va)))

        span_x_min = 1.0
        if amostras_validas:
            ts_rel_min = [
                (dt - t_bloco_inicio).total_seconds() / 60.0 for dt, _, _ in amostras_validas
            ]
            mem_mib = [vm / 1048576.0 for _, vm, _ in amostras_validas]
            anon_mib = [va / 1048576.0 for _, _, va in amostras_validas]
            if ts_rel_min:
                span_x_min = max(1.0, max(ts_rel_min) - min(ts_rel_min))

            ax.plot(
                ts_rel_min,
                mem_mib,
                color=estilo["color"],
                linewidth=1.5,
            )
            ax.plot(
                ts_rel_min,
                anon_mib,
                color=estilo["color"],
                linestyle="--",
                linewidth=1.5,
            )

        # Sombreamento apenas das fases nomeadas de medição e seed
        cinzas = ["#f5f5f5", "#e8e8e8"]
        i_fase_nomeada = 0

        for passo, t0, t1 in fases:
            rotulo_fase = FASES_RELEVANTES_MEMORIA.get(passo)
            if not rotulo_fase:
                # Fases auxiliares (dados, reiniciar, limpar, etc.) ficam sem rótulo e sem sombreado
                continue

            x0 = (t0 - t_bloco_inicio).total_seconds() / 60.0
            x1 = (t1 - t_bloco_inicio).total_seconds() / 60.0
            largura_trecho = x1 - x0

            cor_fundo = cinzas[i_fase_nomeada % 2]
            i_fase_nomeada += 1

            ax.axvspan(x0, x1, color=cor_fundo, alpha=0.7, zorder=0)

            # Centralizado no topo do trecho, 7 pt, sem sobrepor (omite se o trecho for estreito demais)
            largura_minima_necessaria = max(0.015, len(rotulo_fase) * 0.005) * span_x_min
            if largura_trecho >= largura_minima_necessaria:
                ax.text(
                    (x0 + x1) / 2.0,
                    0.92,
                    rotulo_fase,
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="top",
                    fontsize=7,
                    color="#444444",
                )

        ax.set_ylabel("Memória (MiB)", fontsize=9)
        if idx == len(eixos) - 1:
            ax.set_xlabel("Tempo desde o início do bloco (min)", fontsize=9)

    # Legenda única abaixo da figura em cinza escuro
    elementos_legenda = [
        Line2D(
            [0],
            [0],
            color="#444444",
            linestyle="-",
            linewidth=1.5,
            label="Total (memory.current)",
        ),
        Line2D(
            [0],
            [0],
            color="#444444",
            linestyle="--",
            linewidth=1.5,
            label="Anônima (anon)",
        ),
    ]

    fig.tight_layout()
    # Reserva espaço inferior para a legenda sem colidir com o eixo x
    fig.subplots_adjust(bottom=0.18, hspace=0.38)
    fig.legend(
        handles=elementos_legenda,
        loc="lower center",
        ncol=2,
        bbox_to_anchor=(0.5, 0.0),
        fontsize=9,
        frameon=False,
    )

    if caminho_saida:
        p = Path(caminho_saida)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, format="pdf", bbox_inches="tight")
    return fig
