#!/usr/bin/env python3
"""Contraprova: o `recall = 1,0` do Cenário B vem do fallback para busca exata?

**Hipótese sob teste.** Nos resultados da Etapa 3 (2026-07-09), Qdrant e Weaviate
apresentaram `recall@10 = 1,0000` *constante nos cinco valores de `ef_search`*
nas seletividades baixas. Recall que não responde a `ef_search` não pode vir de
percurso do grafo HNSW. A explicação candidata é o *fallback* documentado para
varredura exata quando o subconjunto elegível é pequeno:

- Weaviate `flatSearchCutoff`, default **40000** objetos;
- Qdrant `full_scan_threshold`, default **10000 KB**.

**Predição falseável.** Repetindo os mesmos pontos com o limiar zerado
(`flat_search_cutoff=0` / `full_scan_threshold=0`), que a documentação indica
para forçar o índice vetorial, o recall deve **deixar de ser exatamente 1,0000**
e voltar a crescer com `ef_search`. Se permanecer 1,0000 e plano, a hipótese
está errada e a explicação é outra.

Escala reduzida de propósito (Q=200, ef ∈ {16, 256}): o teste é sobre a *forma*
da curva — plana ou crescente —, não sobre os valores absolutos.

Uso: `./.venv/bin/python -m experimentos.contraprova_full_scan`
Requer os 3 SGBDs de pé (`make up`) e Verba desligado (`make ui-down`).
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

N_BASE = 100_000
N_QUERIES = 200
K = 10
EF_SEARCH = [16, 256]
SELETIVIDADES = [0.01, 0.1]
WARMUP = 20

MS_MARCO_DIR = Path("../data/ms_marco")
EMBEDDINGS_DIR = Path("../data/embeddings")
RESULTS_DIR = Path("./results")


def log(msg: str) -> None:
    print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] {msg}", flush=True)


def _seed(
    sistema: str,
    *,
    vetores: np.ndarray,
    metadata: list[dict[str, Any]],
    recurso: Any,
    nome: str,
    forcar_hnsw: bool,
) -> None:
    """Semeia com o limiar de full-scan no default do servidor ou zerado."""
    if sistema == "qdrant":
        from seeders.qdrant_seeder import FULL_SCAN_MINIMO, seed_qdrant

        # `seed_qdrant` já bloqueia até o status `green` (aguardar_indexacao=True).
        seed_qdrant(
            vetores=vetores, metadata=metadata, client=recurso, nome_colecao=nome,
            full_scan_threshold=FULL_SCAN_MINIMO if forcar_hnsw else None,
        )
    elif sistema == "weaviate":
        from seeders.weaviate_seeder import seed_weaviate

        seed_weaviate(
            vetores=vetores, metadata=metadata, client=recurso, nome_classe=nome,
            flat_search_cutoff=0 if forcar_hnsw else None,
        )


def executar() -> dict[str, Any]:
    import os

    from dotenv import load_dotenv

    from benchmarks.cenario_b import medir_sistema_filtrado
    from benchmarks.run_cenario_a import (
        _construir_buscador,
        _limpar_recurso,
        split_embeddings,
    )
    from benchmarks.run_cenario_b import sintetizar_seletor
    from ground_truth.exact_search import top_k_exato_filtrado
    from pipeline.embeddings import gerar_embeddings
    from pipeline.ms_marco_loader import sample_passages

    load_dotenv()
    env = dict(os.environ)

    log(f"Carregando embeddings ({N_BASE + N_QUERIES} passages, cache esperado)...")
    passages = sample_passages(
        MS_MARCO_DIR / "collection.tsv", n=N_BASE + N_QUERIES
    )
    embs = gerar_embeddings([p.text for p in passages], cache_dir=EMBEDDINGS_DIR)
    base, queries = split_embeddings(embs, n_base=N_BASE, n_queries=N_QUERIES)

    seletor = sintetizar_seletor(N_BASE)
    metadata = [{"seletor": float(seletor[i])} for i in range(N_BASE)]

    log("Calculando ground truth filtrado...")
    gt = {
        p: top_k_exato_filtrado(base, queries, seletor=seletor, p=p, k=K)[1]
        for p in SELETIVIDADES
    }
    for p in SELETIVIDADES:
        log(f"  p={p}: {int(round(p * N_BASE))} elegíveis de {N_BASE}")

    achados: list[dict[str, Any]] = []
    for sistema in ["qdrant", "weaviate"]:
        for forcar_hnsw in [False, True]:
            rotulo = "limiar mínimo (HNSW)" if forcar_hnsw else "default do servidor"
            nome = (
                f"contraprova_{'forced' if forcar_hnsw else 'default'}"
                if sistema != "weaviate"
                else f"Contraprova{'Forced' if forcar_hnsw else 'Default'}"
            )
            log(f"\n--- {sistema} | {rotulo} ---")
            buscador, recurso = _construir_buscador(
                sistema, nome_recurso=nome, env=env
            )
            try:
                _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome)
                t0 = time.perf_counter()
                _seed(
                    sistema, vetores=base, metadata=metadata, recurso=recurso,
                    nome=nome, forcar_hnsw=forcar_hnsw,
                )
                log(f"    seed em {time.perf_counter() - t0:.1f}s")

                resultados = medir_sistema_filtrado(
                    buscador, queries=queries, gt_por_seletividade=gt,
                    ef_search_values=EF_SEARCH, seletividades=SELETIVIDADES,
                    k=K, n_base=N_BASE,
                    timestamp_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ"),
                    warmup=WARMUP, ambiente={"sistema": sistema},
                )
                for r in resultados:
                    achados.append(
                        {
                            "sistema": sistema,
                            "forcar_hnsw": forcar_hnsw,
                            "seletividade": r.parametros["seletividade"],
                            "ef_search": r.parametros["ef_search"],
                            "recall_at_k": r.metricas["recall_at_k"],
                            "p50": r.metricas["p50"],
                            "qps": r.metricas["qps"],
                        }
                    )
                _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome)
            finally:
                if hasattr(recurso, "close"):
                    recurso.close()

    return {"n_base": N_BASE, "n_queries": N_QUERIES, "k": K, "achados": achados}


def _veredito(achados: list[dict[str, Any]]) -> list[str]:
    """Para cada (sistema, config, p): o recall responde a `ef_search`?"""
    linhas = ["", "=" * 78, "VEREDITO", "=" * 78]
    linhas.append(f"{'sistema':10} {'config':22} {'p':>6} {'recalls':22} conclusão")
    linhas.append("-" * 78)
    for sistema in ["qdrant", "weaviate"]:
        for forcar in [False, True]:
            for p in SELETIVIDADES:
                pontos = sorted(
                    (
                        a
                        for a in achados
                        if a["sistema"] == sistema
                        and a["forcar_hnsw"] == forcar
                        and a["seletividade"] == p
                    ),
                    key=lambda a: a["ef_search"],
                )
                if not pontos:
                    continue
                recalls = [a["recall_at_k"] for a in pontos]
                plano = max(recalls) - min(recalls) < 1e-9
                exato = plano and abs(recalls[0] - 1.0) < 1e-9
                cfg = "limiar mínimo (HNSW)" if forcar else "default do servidor"
                conclusao = (
                    "BUSCA EXATA (recall plano em 1,0)"
                    if exato
                    else ("plano, mas < 1,0" if plano else "HNSW (recall cresce c/ ef)")
                )
                linhas.append(
                    f"{sistema:10} {cfg:22} {p:>6} "
                    f"{' '.join(f'{r:.4f}' for r in recalls):22} {conclusao}"
                )
    return linhas


if __name__ == "__main__":
    dados = executar()
    for linha in _veredito(dados["achados"]):
        print(linha)

    destino = RESULTS_DIR / "contraprova_full_scan.json"
    destino.write_text(
        json.dumps(dados, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nResultado bruto salvo em {destino}")
