#!/usr/bin/env python3
"""Continuação dos experimentos da Etapa 3 (pós-fix do timeout Qdrant).

Retoma de onde parou: Cenário B 100k (qdrant + weaviate) + bloco 500k completo.
Embeddings de 100k já estão em cache; resultados do Cenário A 100k e B pgvector
100k já salvos em results/.
"""

from __future__ import annotations

import json
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
SISTEMAS = ["pgvector", "qdrant", "weaviate"]

MS_MARCO_DIR = Path("../data/ms_marco")
EMBEDDINGS_DIR = Path("../data/embeddings")
RESULTS_DIR = Path("./results")
GT_DIR = Path("../data/ground_truth")


def log(msg: str) -> None:
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _medir_footprint(sistema: str, recurso, nome_recurso: str) -> dict:
    """Estima footprint de armazenamento para cada sistema."""
    if sistema == "pgvector":
        with recurso.cursor() as cur:
            cur.execute(
                "SELECT pg_total_relation_size(%s::regclass)",
                (nome_recurso,),
            )
            total_bytes = cur.fetchone()[0]
            cur.execute(
                "SELECT pg_relation_size(%s::regclass)",
                (nome_recurso,),
            )
            table_bytes = cur.fetchone()[0]
            cur.execute(
                "SELECT pg_indexes_size(%s::regclass)",
                (nome_recurso,),
            )
            index_bytes = cur.fetchone()[0]
        return {
            "total_bytes": total_bytes,
            "table_bytes": table_bytes,
            "index_bytes": index_bytes,
            "total_mb": round(total_bytes / 1024 / 1024, 2),
        }
    elif sistema == "qdrant":
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
    return {}


def run_remaining() -> dict:
    """Executa experimentos restantes."""
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
    from lib.reporting import salvar_curva, salvar_ground_truth
    from pipeline.embeddings import gerar_embeddings
    from pipeline.ms_marco_loader import sample_passages

    load_dotenv()
    env = dict(os.environ)
    timings: dict = {"experimentos": []}

    # ================================================================
    # PARTE 1: Cenário B 100k — qdrant e weaviate (retomada)
    # ================================================================
    n_base = 100_000
    log(f"{'='*60}")
    log("RETOMANDO Cenário B 100k (qdrant + weaviate)")
    log(f"{'='*60}")

    log("Carregando embeddings 101k do cache...")
    t0 = time.perf_counter()
    passages = sample_passages(MS_MARCO_DIR / "collection.tsv", n=n_base + N_QUERIES)
    textos = [p.text for p in passages]
    embs = gerar_embeddings(textos, cache_dir=EMBEDDINGS_DIR)
    t_emb = time.perf_counter() - t0
    log(f"  Embeddings: {embs.shape} em {t_emb:.1f}s {'(cache)' if t_emb < 5 else '(gerado)'}")

    base, queries = split_embeddings(embs, n_base=n_base, n_queries=N_QUERIES)

    # GT (já computado e salvo, mas recarregamos para os objetos em memória)
    seletor_100k = sintetizar_seletor(n_base)
    gt_por_sel_100k: dict[float, np.ndarray] = {}
    for p in SELETIVIDADES:
        _, gt_ids = top_k_exato_filtrado(base, queries, seletor=seletor_100k, p=p, k=K)
        gt_por_sel_100k[p] = gt_ids

    metadata_b = [{"seletor": float(seletor_100k[i])} for i in range(n_base)]
    ts_b = timestamp_utc()

    for sistema in ["qdrant", "weaviate"]:
        log(f"\n--- Cenário B (retomada): {sistema} (N={n_base}) ---")
        nome_recurso = f"bench_b_{n_base}" if sistema != "weaviate" else f"BenchB{n_base}"
        buscador, recurso = _construir_buscador(sistema, nome_recurso=nome_recurso, env=env)
        try:
            _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome_recurso)
            log(f"  Seedando {n_base} vetores + seletor em {sistema}...")
            t0 = time.perf_counter()
            _seed_b(
                sistema,
                vetores=base,
                metadata=metadata_b,
                recurso=recurso,
                nome_recurso=nome_recurso,
            )
            t_seed = time.perf_counter() - t0
            log(f"  Seed B {sistema}: {t_seed:.1f}s")

            # Esperar Qdrant ficar verde antes de buscar
            if sistema == "qdrant":
                log("  Esperando Qdrant otimizar segmentos...")
                for _ in range(60):
                    info = recurso.get_collection(nome_recurso)
                    if str(info.status) == "green":
                        break
                    time.sleep(2)
                log(f"  Status Qdrant: {info.status}")

            log(f"  Rodando benchmark B ({sistema})...")
            t0 = time.perf_counter()
            resultados = medir_sistema_filtrado(
                buscador,
                queries=queries,
                gt_por_seletividade=gt_por_sel_100k,
                ef_search_values=EF_SEARCH,
                seletividades=SELETIVIDADES,
                k=K,
                n_base=n_base,
                timestamp_utc=ts_b,
                warmup=WARMUP,
                ambiente={"sistema": sistema},
            )
            t_bench = time.perf_counter() - t0
            log(f"  Benchmark B {sistema}: {t_bench:.1f}s")
            salvar_curva(resultados, results_dir=RESULTS_DIR)
        finally:
            if hasattr(recurso, "close"):
                recurso.close()

    log("Cenário B 100k retomada CONCLUÍDA")

    # ================================================================
    # PARTE 2: Bloco 500k completo (A + B)
    # ================================================================
    n_base = 500_000
    log(f"\n{'='*60}")
    log(f"INICIANDO BLOCO N={n_base}")
    log(f"{'='*60}")

    exp_info: dict = {"n_base": n_base, "n_queries": N_QUERIES}

    log(f"Carregando {n_base + N_QUERIES} passages do MS MARCO...")
    t0 = time.perf_counter()
    passages = sample_passages(MS_MARCO_DIR / "collection.tsv", n=n_base + N_QUERIES)
    textos = [p.text for p in passages]
    t_load = time.perf_counter() - t0
    exp_info["tempo_carga_passages_s"] = round(t_load, 2)
    log(f"  Passages carregadas em {t_load:.1f}s")

    log(f"Gerando embeddings para {len(textos)} textos...")
    t0 = time.perf_counter()
    embs = gerar_embeddings(textos, cache_dir=EMBEDDINGS_DIR)
    t_emb = time.perf_counter() - t0
    exp_info["tempo_embeddings_s"] = round(t_emb, 2)
    exp_info["embeddings_cache_hit"] = t_emb < 5.0
    log(f"  Embeddings: {embs.shape} em {t_emb:.1f}s {'(cache)' if t_emb < 5 else '(gerado)'}")

    base, queries = split_embeddings(embs, n_base=n_base, n_queries=N_QUERIES)

    # Ground truth A
    log("Calculando ground truth exato (Cenário A)...")
    t0 = time.perf_counter()
    _, gt_ids_a = top_k_exato(base, queries, k=K)
    t_gt_a = time.perf_counter() - t0
    exp_info["tempo_gt_cenario_a_s"] = round(t_gt_a, 2)
    log(f"  GT Cenário A calculado em {t_gt_a:.1f}s")
    salvar_ground_truth(
        np.zeros_like(gt_ids_a, dtype=np.float32),
        gt_ids_a,
        dest_dir=GT_DIR,
        nome=f"cenario_a_n{n_base}_q{N_QUERIES}_k{K}",
    )

    # Ground truth B
    seletor = sintetizar_seletor(n_base)
    gt_por_seletividade: dict[float, np.ndarray] = {}
    tempos_gt_b: dict[str, float] = {}
    for p in SELETIVIDADES:
        log(f"Calculando GT filtrado (p={p})...")
        t0 = time.perf_counter()
        scores_b, gt_ids_b = top_k_exato_filtrado(base, queries, seletor=seletor, p=p, k=K)
        t_gt_b = time.perf_counter() - t0
        tempos_gt_b[str(p)] = round(t_gt_b, 2)
        gt_por_seletividade[p] = gt_ids_b
        salvar_ground_truth(
            scores_b,
            gt_ids_b,
            dest_dir=GT_DIR,
            nome=f"cenario_b_n{n_base}_q{N_QUERIES}_k{K}_p{p}",
        )
        log(f"  GT p={p}: {t_gt_b:.1f}s")
    exp_info["tempos_gt_cenario_b_s"] = tempos_gt_b

    # Cenário A — 500k
    ts = timestamp_utc()
    metadata_b = [{"seletor": float(seletor[i])} for i in range(n_base)]
    resultados_a: dict[str, list] = {}
    tempos_seed: dict[str, float] = {}
    footprints: dict[str, dict] = {}

    for sistema in SISTEMAS:
        log(f"\n--- Cenário A: {sistema} (N={n_base}) ---")
        nome_recurso = f"bench_a_{n_base}" if sistema != "weaviate" else f"BenchA{n_base}"
        buscador, recurso = _construir_buscador(sistema, nome_recurso=nome_recurso, env=env)
        try:
            _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome_recurso)
            log(f"  Seedando {n_base} vetores em {sistema}...")
            t0 = time.perf_counter()
            _seed(sistema, vetores=base, recurso=recurso, nome_recurso=nome_recurso)
            t_seed = time.perf_counter() - t0
            tempos_seed[sistema] = round(t_seed, 2)
            log(f"  Seed {sistema}: {t_seed:.1f}s")

            # Esperar Qdrant otimizar antes de medir
            if sistema == "qdrant":
                log("  Esperando Qdrant otimizar segmentos...")
                for _ in range(120):
                    info = recurso.get_collection(nome_recurso)
                    if str(info.status) == "green":
                        break
                    time.sleep(2)
                log(f"  Status Qdrant: {info.status}")

            try:
                fp = _medir_footprint(sistema, recurso, nome_recurso)
                footprints[sistema] = fp
                log(f"  Footprint {sistema}: {fp}")
            except Exception as e:
                log(f"  Footprint {sistema}: erro ({e})")

            log(f"  Rodando benchmark A ({sistema})...")
            t0 = time.perf_counter()
            resultados = medir_sistema(
                buscador,
                queries=queries,
                gt_ids=gt_ids_a,
                ef_search_values=EF_SEARCH,
                k=K,
                n_base=n_base,
                timestamp_utc=ts,
                warmup=WARMUP,
                ambiente={"sistema": sistema},
            )
            t_bench = time.perf_counter() - t0
            log(f"  Benchmark A {sistema}: {t_bench:.1f}s")
            salvar_curva(resultados, results_dir=RESULTS_DIR)
            resultados_a[sistema] = [
                {"ef_search": r.parametros.get("ef_search"), **r.metricas} for r in resultados
            ]
        finally:
            if hasattr(recurso, "close"):
                recurso.close()

    exp_info["tempos_seed_cenario_a_s"] = tempos_seed
    exp_info["footprints"] = footprints
    exp_info["resultados_cenario_a"] = resultados_a

    # Cenário B — 500k
    ts_b = timestamp_utc()
    resultados_b: dict[str, list] = {}
    tempos_seed_b: dict[str, float] = {}

    for sistema in SISTEMAS:
        log(f"\n--- Cenário B: {sistema} (N={n_base}) ---")
        nome_recurso = f"bench_b_{n_base}" if sistema != "weaviate" else f"BenchB{n_base}"
        buscador, recurso = _construir_buscador(sistema, nome_recurso=nome_recurso, env=env)
        try:
            _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome_recurso)
            log(f"  Seedando {n_base} vetores + seletor em {sistema}...")
            t0 = time.perf_counter()
            _seed_b(
                sistema,
                vetores=base,
                metadata=metadata_b,
                recurso=recurso,
                nome_recurso=nome_recurso,
            )
            t_seed = time.perf_counter() - t0
            tempos_seed_b[sistema] = round(t_seed, 2)
            log(f"  Seed B {sistema}: {t_seed:.1f}s")

            if sistema == "qdrant":
                log("  Esperando Qdrant otimizar segmentos...")
                for _ in range(120):
                    info = recurso.get_collection(nome_recurso)
                    if str(info.status) == "green":
                        break
                    time.sleep(2)
                log(f"  Status Qdrant: {info.status}")

            log(f"  Rodando benchmark B ({sistema})...")
            t0 = time.perf_counter()
            resultados = medir_sistema_filtrado(
                buscador,
                queries=queries,
                gt_por_seletividade=gt_por_seletividade,
                ef_search_values=EF_SEARCH,
                seletividades=SELETIVIDADES,
                k=K,
                n_base=n_base,
                timestamp_utc=ts_b,
                warmup=WARMUP,
                ambiente={"sistema": sistema},
            )
            t_bench = time.perf_counter() - t0
            log(f"  Benchmark B {sistema}: {t_bench:.1f}s")
            salvar_curva(resultados, results_dir=RESULTS_DIR)
            resultados_b[sistema] = [
                {
                    "ef_search": r.parametros.get("ef_search"),
                    "seletividade": r.parametros.get("seletividade"),
                    **r.metricas,
                }
                for r in resultados
            ]
        finally:
            if hasattr(recurso, "close"):
                recurso.close()

    exp_info["tempos_seed_cenario_b_s"] = tempos_seed_b
    exp_info["resultados_cenario_b"] = resultados_b
    timings["experimentos"].append(exp_info)

    # ---- Salvar timings consolidados ----
    timings_path = RESULTS_DIR / "etapa3_timings_remaining.json"
    timings_path.write_text(
        json.dumps(timings, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    log(f"\nTimings consolidados salvos em {timings_path}")
    log("TODOS OS EXPERIMENTOS CONCLUÍDOS!")
    return timings


if __name__ == "__main__":
    run_remaining()
