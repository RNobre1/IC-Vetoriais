"""Linha de comando (CLI) para geração de todas as tabelas LaTeX e figuras da sessão.

Execução:
    python -m analise.gerar \\
        --results-dir results \\
        --sessao results/sessoes/<id> \\
        --anterior "results/cenario_*_2026-08-23T*.json" \\
        --saida ../docx/relatorio_parcial/gerado \\
        --figuras ../docx/relatorio_parcial/figuras

Escreve um arquivo .tex por tabela:
- tab_recursos.tex
- tab_a_<n>.tex
- tab_b_<n>.tex (somente se houver JSON do Cenário B naquela escala)
- tab_c_<n>.tex
- tab_c_hospedeiro_<n>.tex (somente se houver dados de monitor e Cenário C)
- tab_ponte.tex
- tab_reprod.tex
- tab_controle_<n>.tex (somente onde 0,1 * n >= CORTE_FLAT_WEAVIATE)
- tab_custo.tex (consolidada com todas as escalas)
- tab_custo_<n>.tex (por escala, sem a coluna de escala)
E as figuras em PDF correspondentes.

Escalas ou cenários ausentes emitem aviso informativo e pulam a tabela específica
sem interromper a geração das demais.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from analise.custo import calcular_custo, carregar_amostras_monitor, linhas_custo
from analise.figuras import fig_cenario_c, fig_memoria, fig_recall_qps
from analise.sessao import carregar_arquivos, carregar_sessao
from analise.tabelas import (
    SISTEMAS_ORDEM,
    linhas_cenario_a,
    linhas_cenario_b,
    linhas_cenario_c,
    linhas_cenario_c_hospedeiro,
    linhas_controle_weaviate,
    linhas_ponte,
    linhas_recursos,
    linhas_reprodutibilidade,
)
from benchmarks.run_sessao import CORTE_FLAT_WEAVIATE


def gerar_artefatos(
    *,
    results_dir: str | Path,
    sessao_dir: str | Path,
    marcos_path: str | Path | None = None,
    monitor_csv: str | Path | Sequence[str | Path] | None = None,
    anterior_paths: Sequence[str | Path] | str | None = None,
    saida_tabelas: str | Path = "../docx/relatorio_parcial/gerado",
    saida_figuras: str | Path | None = "../docx/relatorio_parcial/figuras",
    ef_cenario_b: int = 64,
    ef_ponte: int = 64,
    ef_reprod: int = 64,
) -> list[str]:
    """Gera todas as tabelas LaTeX e figuras derivadas dos JSONs da sessão."""
    p_sessao = Path(sessao_dir)
    p_results = Path(results_dir)

    p_marcos = (
        Path(marcos_path)
        if marcos_path
        else (p_sessao / "marcos.jsonl" if p_sessao.is_dir() else p_sessao)
    )

    p_tab = Path(saida_tabelas)
    p_tab.mkdir(parents=True, exist_ok=True)

    p_fig = Path(saida_figuras) if saida_figuras else None
    if p_fig:
        p_fig.mkdir(parents=True, exist_ok=True)

    # Resolve caminhos do monitor CSV e pré-carrega amostras
    caminhos_csv: list[Path] = []
    if monitor_csv:
        if isinstance(monitor_csv, str | Path):
            caminhos_csv.append(Path(monitor_csv))
        else:
            caminhos_csv.extend(Path(c) for c in monitor_csv)
    elif p_sessao.is_dir():
        caminhos_csv = sorted(p_sessao.glob("monitor_*.csv"))

    amostras_monitor = carregar_amostras_monitor(caminhos_csv) if caminhos_csv else []

    sessao = carregar_sessao(p_results, p_marcos)
    avisos: list[str] = list(sessao.avisos)

    escalas = sessao.escalas

    # 1. tab_recursos.tex
    if escalas:
        conteudo_rec = linhas_recursos(sessao, escalas)
        (p_tab / "tab_recursos.tex").write_text(conteudo_rec, encoding="utf-8")
    else:
        avisos.append("Nenhuma escala encontrada na sessão; tab_recursos.tex pulada.")

    # 2. tab_a_<n>.tex
    for n in escalas:
        conteudo_a = linhas_cenario_a(sessao, n)
        if conteudo_a.strip():
            (p_tab / f"tab_a_{n}.tex").write_text(conteudo_a, encoding="utf-8")
        else:
            avisos.append(f"Sem dados de Cenário A para escala {n}; tab_a_{n}.tex pulada.")

    # 3. tab_b_<n>.tex (somente se houver JSON do Cenário B para essa escala)
    for n in escalas:
        tem_b = any(
            sessao.obter("B_padrao", s, n) is not None or sessao.obter("B_eq", s, n) is not None
            for s in SISTEMAS_ORDEM
        )
        if tem_b:
            conteudo_b = linhas_cenario_b(sessao, n, ef=ef_cenario_b)
            if conteudo_b.strip():
                (p_tab / f"tab_b_{n}.tex").write_text(conteudo_b, encoding="utf-8")
        else:
            avisos.append(f"Sem JSONs de Cenário B para escala {n}; tab_b_{n}.tex pulada.")

    # 4. tab_c_<n>.tex e tab_c_hospedeiro_<n>.tex
    for n in escalas:
        tem_c = any(sessao.obter("C", s, n) is not None for s in SISTEMAS_ORDEM)
        if tem_c:
            conteudo_c = linhas_cenario_c(sessao, n)
            if conteudo_c.strip():
                (p_tab / f"tab_c_{n}.tex").write_text(conteudo_c, encoding="utf-8")

            if caminhos_csv and any(c.is_file() for c in caminhos_csv):
                conteudo_c_hosp = linhas_cenario_c_hospedeiro(
                    sessao, n, amostras_monitor=amostras_monitor
                )
                if conteudo_c_hosp.strip():
                    (p_tab / f"tab_c_hospedeiro_{n}.tex").write_text(
                        conteudo_c_hosp, encoding="utf-8"
                    )
            else:
                avisos.append(f"Nenhum CSV de monitor encontrado; tab_c_hospedeiro_{n}.tex pulada.")
        else:
            avisos.append(f"Sem dados de Cenário C para escala {n}; tab_c_{n}.tex pulada.")

    # 5. tab_ponte.tex
    tem_ponte = any(sessao.obter("A_ponte", s, 100000) is not None for s in SISTEMAS_ORDEM)
    if tem_ponte:
        conteudo_ponte = linhas_ponte(sessao, ef=ef_ponte)
        (p_tab / "tab_ponte.tex").write_text(conteudo_ponte, encoding="utf-8")
    else:
        avisos.append("Sem dados de ponte em 100k; tab_ponte.tex pulada.")

    # 6. tab_reprod.tex
    if anterior_paths:
        sessao_ant = carregar_arquivos(anterior_paths)
        conteudo_reprod = linhas_reprodutibilidade(sessao, sessao_ant, ef=ef_reprod)
        if conteudo_reprod.strip():
            (p_tab / "tab_reprod.tex").write_text(conteudo_reprod, encoding="utf-8")
        else:
            avisos.append("Sem dados compatíveis para tab_reprod.tex; tabela pulada.")
    else:
        avisos.append("Nenhum dado anterior (--anterior) fornecido; tab_reprod.tex pulada.")

    # 7. tab_controle_<n>.tex (somente onde 0.1 * n >= CORTE_FLAT_WEAVIATE)
    for n in escalas:
        if 0.1 * n < CORTE_FLAT_WEAVIATE:
            avisos.append(
                f"Escala {n} abaixo do corte de flat search ({0.1*n} < {CORTE_FLAT_WEAVIATE}); "
                f"tab_controle_{n}.tex não aplicável."
            )
            continue

        arq_p = sessao.obter("B_padrao", "weaviate", n)
        arq_e = sessao.obter("B_eq", "weaviate", n)
        if arq_p and arq_e:
            conteudo_ctrl = linhas_controle_weaviate(sessao, n)
            if conteudo_ctrl.strip():
                (p_tab / f"tab_controle_{n}.tex").write_text(conteudo_ctrl, encoding="utf-8")
        else:
            avisos.append(
                f"Sem par de controle Weaviate para escala {n}; tab_controle_{n}.tex pulada."
            )

    # 8. tab_custo.tex e tab_custo_<n>.tex
    if caminhos_csv and any(c.is_file() for c in caminhos_csv):
        metricas_custo = calcular_custo(
            caminhos_csv, p_marcos, somente_relevantes=True, amostras=amostras_monitor
        )
        if metricas_custo:
            # Avisa se alguma fase teve amostras ausentes
            for m in metricas_custo:
                if m.pico_mem_mib is None and m.cpu_nucleos is None:
                    avisos.append(
                        f"Fase {m.sistema} {m.passo} (N={m.n}) não possui amostras válidas no monitor CSV."
                    )
            conteudo_custo = linhas_custo(metricas_custo)
            (p_tab / "tab_custo.tex").write_text(conteudo_custo, encoding="utf-8")
            escalas_custo = sorted({m.n for m in metricas_custo})
            for n_custo in escalas_custo:
                conteudo_n = linhas_custo(metricas_custo, escala=n_custo, incluir_escala=False)
                (p_tab / f"tab_custo_{n_custo}.tex").write_text(conteudo_n, encoding="utf-8")
        else:
            avisos.append(
                "Nenhum intervalo de fase compatível encontrado no CSV; tab_custo.tex pulada."
            )
    else:
        avisos.append("Nenhum CSV de monitor encontrado; tab_custo.tex pulada.")

    # Figuras PDF
    if p_fig:
        if escalas:
            fig_recall_qps(sessao, escalas, caminho_saida=p_fig / "fig_recall_qps.pdf")

        for n in escalas:
            if any(sessao.obter("C", s, n) is not None for s in SISTEMAS_ORDEM):
                fig_cenario_c(sessao, n, caminho_saida=p_fig / f"fig_cenario_c_{n}.pdf")

        if caminhos_csv and any(c.is_file() for c in caminhos_csv):
            for n in escalas:
                fig_memoria(
                    caminhos_csv,
                    p_marcos,
                    n,
                    caminho_saida=p_fig / f"fig_memoria_{n}.pdf",
                )

    return avisos


def main(argv: Sequence[str] | None = None) -> int:
    """Função de entrada da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Gera tabelas LaTeX e figuras derivadas dos JSONs da sessão."
    )
    parser.add_argument("--results-dir", default="results", help="Diretório dos JSONs de resultado")
    parser.add_argument(
        "--sessao",
        required=True,
        help="Diretório da sessão contendo marcos.jsonl e monitor_*.csv",
    )
    parser.add_argument(
        "--anterior",
        default=None,
        help="Glob ou caminhos dos JSONs da sessão anterior (ex.: 23/08)",
    )
    parser.add_argument(
        "--saida",
        default="../docx/relatorio_parcial/gerado",
        help="Diretório de saída para tabelas .tex",
    )
    parser.add_argument(
        "--figuras",
        default="../docx/relatorio_parcial/figuras",
        help="Diretório de saída para figuras .pdf",
    )

    args = parser.parse_args(argv)

    avisos = gerar_artefatos(
        results_dir=args.results_dir,
        sessao_dir=args.sessao,
        anterior_paths=args.anterior,
        saida_tabelas=args.saida,
        saida_figuras=args.figuras,
    )

    if avisos:
        print("=== Avisos da geração ===", file=sys.stderr)
        for av in avisos:
            print(f"- {av}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
