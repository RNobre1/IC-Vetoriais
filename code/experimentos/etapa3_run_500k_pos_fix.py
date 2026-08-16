#!/usr/bin/env python3
"""Última parte dos experimentos da Etapa 3 (pós-fix timeout Qdrant).

Retoma a partir do Cenário A Qdrant para N=500000.
Embeddings já estão cacheados, GTs são recalculados rapidinho na memória.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

# ---- constantes ----
N_QUERIES = 1_000
K = 10
EF_SEARCH = [16, 32, 64, 128, 256]
WARMUP = 50
SELETIVIDADES = [0.01, 0.1, 0.5, 1.0]

MS_MARCO_DIR = Path("../data/ms_marco")
EMBEDDINGS_DIR = Path("../data/embeddings")
RESULTS_DIR = Path("./results")
GT_DIR = Path("../data/ground_truth")


def log(msg: str) -> None:
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _medir_footprint(sistema: str, recurso, nome_recurso: str) -> dict:
    if sistema == "qdrant":
        info = recurso.get_collection(nome_recurso)
        return {
            "points_count": info.points_count,
            "segments_count": info.segments_count,
            "status": str(info.status),
        }
    elif sistema == "weaviate":
        col = recurso.collections.get(nome_recurso)
        agg = col.aggregate.over_all(total_count=True)
        return {"total_objects": agg.total_count}
    elif sistema == "pgvector":
        with recurso.cursor() as cur:
            cur.execute(
                "SELECT pg_total_relation_size(%s::regclass)", (nome_recurso,),
            )
            total_bytes = cur.fetchone()[0]
            cur.execute(
                "SELECT pg_relation_size(%s::regclass)", (nome_recurso,),
            )
            table_bytes = cur.fetchone()[0]
            cur.execute(
                "SELECT pg_indexes_size(%s::regclass)", (nome_recurso,),
            )
            index_bytes = cur.fetchone()[0]
        return {
            "total_bytes": total_bytes, "table_bytes": table_bytes,
            "index_bytes": index_bytes,
            "total_mb": round(total_bytes / 1024 / 1024, 2),
        }
    return {}


def run_final() -> dict:
    from dotenv import load_dotenv

    from benchmarks.cenario_a import medir_sistema
    from benchmarks.cenario_b import medir_sistema_filtrado
    from benchmarks.run_cenario_a import (
        _construir_buscador,
        _limpar_recurso,
        _seed,
        split_embeddings,
        timestamp_utc,
    )
    from benchmarks.run_cenario_b import _seed_b, sintetizar_seletor
    from ground_truth.exact_search import top_k_exato, top_k_exato_filtrado
    from lib.reporting import salvar_curva
    from pipeline.embeddings import gerar_embeddings
    from pipeline.ms_marco_loader import sample_passages

    load_dotenv()
    env = dict(os.environ)
    timings: dict = {"experimentos": []}

    n_base = 500_000
    log(f"{'='*60}")
    log(f"RETOMANDO BLOCO N={n_base} (Qdrant e Weaviate Cenário A, e todos Cenário B)")
    log(f"{'='*60}")

    log(f"Carregando {n_base + N_QUERIES} passages...")
    passages = sample_passages(MS_MARCO_DIR / "collection.tsv", n=n_base + N_QUERIES)
    textos = [p.text for p in passages]

    log("Gerando embeddings (vai bater no cache)...")
    embs = gerar_embeddings(textos, cache_dir=EMBEDDINGS_DIR)
    log(f"Embeddings: {embs.shape} carregados.")

    base, queries = split_embeddings(embs, n_base=n_base, n_queries=N_QUERIES)

    # Recalcular GT rapidamente na memória
    log("Recalculando GT A...")
    _, gt_ids_a = top_k_exato(base, queries, k=K)

    log("Recalculando GT B...")
    seletor = sintetizar_seletor(n_base)
    gt_por_seletividade: dict[float, np.ndarray] = {}
    for p in SELETIVIDADES:
        _, gt_ids_b = top_k_exato_filtrado(base, queries, seletor=seletor, p=p, k=K)
        gt_por_seletividade[p] = gt_ids_b

    metadata_b = [{"seletor": float(seletor[i])} for i in range(n_base)]

    # Cenário A — Qdrant e Weaviate
    ts = timestamp_utc()
    for sistema in ["qdrant", "weaviate"]:
        log(f"\n--- Cenário A: {sistema} (N={n_base}) ---")
        nome_recurso = (
            f"bench_a_{n_base}" if sistema != "weaviate" else f"BenchA{n_base}"
        )
        buscador, recurso = _construir_buscador(
            sistema, nome_recurso=nome_recurso, env=env
        )
        try:
            _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome_recurso)
            log(f"  Seedando {n_base} vetores em {sistema}...")
            t0 = time.perf_counter()
            _seed(sistema, vetores=base, recurso=recurso, nome_recurso=nome_recurso)
            t_seed = time.perf_counter() - t0
            log(f"  Seed {sistema}: {t_seed:.1f}s")

            if sistema == "qdrant":
                log("  Esperando Qdrant otimizar segmentos...")
                for _ in range(120):
                    info = recurso.get_collection(nome_recurso)
                    if str(info.status) == "green":
                        break
                    time.sleep(2)

            log(f"  Footprint {sistema}: {_medir_footprint(sistema, recurso, nome_recurso)}")

            log(f"  Rodando benchmark A ({sistema})...")
            t0 = time.perf_counter()
            resultados = medir_sistema(
                buscador, queries=queries, gt_ids=gt_ids_a,
                ef_search_values=EF_SEARCH, k=K, n_base=n_base,
                timestamp_utc=ts, warmup=WARMUP, ambiente={"sistema": sistema},
            )
            log(f"  Benchmark A {sistema}: {time.perf_counter() - t0:.1f}s")
            salvar_curva(resultados, results_dir=RESULTS_DIR)
        finally:
            if hasattr(recurso, "close"):
                recurso.close()

    # Cenário B — pgvector, qdrant, weaviate
    ts_b = timestamp_utc()
    for sistema in ["pgvector", "qdrant", "weaviate"]:
        log(f"\n--- Cenário B: {sistema} (N={n_base}) ---")
        nome_recurso = (
            f"bench_b_{n_base}" if sistema != "weaviate" else f"BenchB{n_base}"
        )
        buscador, recurso = _construir_buscador(
            sistema, nome_recurso=nome_recurso, env=env
        )
        try:
            _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome_recurso)
            log(f"  Seedando {n_base} vetores + seletor em {sistema}...")
            t0 = time.perf_counter()
            _seed_b(
                sistema, vetores=base, metadata=metadata_b,
                recurso=recurso, nome_recurso=nome_recurso,
            )
            t_seed = time.perf_counter() - t0
            log(f"  Seed B {sistema}: {t_seed:.1f}s")

            if sistema == "qdrant":
                log("  Esperando Qdrant otimizar segmentos...")
                for _ in range(120):
                    info = recurso.get_collection(nome_recurso)
                    if str(info.status) == "green":
                        break
                    time.sleep(2)

            log(f"  Rodando benchmark B ({sistema})...")
            t0 = time.perf_counter()
            resultados = medir_sistema_filtrado(
                buscador, queries=queries, gt_por_seletividade=gt_por_seletividade,
                ef_search_values=EF_SEARCH, seletividades=SELETIVIDADES,
                k=K, n_base=n_base, timestamp_utc=ts_b, warmup=WARMUP,
                ambiente={"sistema": sistema},
            )
            log(f"  Benchmark B {sistema}: {time.perf_counter() - t0:.1f}s")
            salvar_curva(resultados, results_dir=RESULTS_DIR)
        finally:
            if hasattr(recurso, "close"):
                recurso.close()

    log("TODOS OS EXPERIMENTOS CONCLUÍDOS!")
    return timings

if __name__ == "__main__":
    run_final()
