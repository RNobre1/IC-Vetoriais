"""CLI do Cenário A — orquestra pipeline → seed → ground truth → benchmark.

Junta as peças já testadas (`pipeline.ms_marco_loader`, `pipeline.embeddings`,
`seeders.*`, `ground_truth.exact_search`, `benchmarks.buscadores`,
`benchmarks.cenario_a.medir_sistema`, `lib.reporting`) num executável.

Decisões metodológicas: [[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]]
(queries held-out, warmup descartado, escopo Etapa 2 = smoke N pequeno).

Uso:
    python -m benchmarks.run_cenario_a --n 500 --queries 50 --ef-search 16,64

As partes puras (`parse_args`, `split_embeddings`, `timestamp_utc`) têm testes
unitários; a orquestração (`executar`) é coberta pelo smoke de integração
`tests/integration/test_buscadores.py`.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

SISTEMAS_VALIDOS = ("pgvector", "qdrant", "weaviate")
EF_SEARCH_PADRAO = [16, 32, 64, 128, 256]


@dataclass(frozen=True, slots=True)
class Config:
    n_base: int = 10_000
    n_queries: int = 1_000
    k: int = 10
    ef_search: list[int] = field(default_factory=lambda: list(EF_SEARCH_PADRAO))
    warmup: int = 50
    sistemas: list[str] = field(default_factory=lambda: list(SISTEMAS_VALIDOS))
    ms_marco_dir: Path = Path("../data/ms_marco")
    embeddings_dir: Path = Path("../data/embeddings")
    results_dir: Path = Path("./results")
    colecao_prefixo: str = "bench_a"


def _lista_int(texto: str) -> list[int]:
    try:
        return [int(x) for x in texto.split(",") if x.strip()]
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"lista de inteiros inválida: {texto!r}") from e


def parse_args(argv: Sequence[str]) -> Config:
    """Converte argv em `Config`. Sai com erro (SystemExit) em entrada inválida."""
    p = argparse.ArgumentParser(prog="run_cenario_a", description="Cenário A — busca pura.")
    p.add_argument("--n", type=int, default=10_000, help="tamanho da base seedada.")
    p.add_argument("--queries", type=int, default=1_000, help="nº de queries held-out.")
    p.add_argument("--k", type=int, default=10, help="K do recall@K / top-K.")
    p.add_argument("--ef-search", type=_lista_int, default=list(EF_SEARCH_PADRAO))
    p.add_argument("--warmup", type=int, default=50, help="buscas de aquecimento descartadas.")
    p.add_argument(
        "--sistemas",
        type=lambda s: [x.strip() for x in s.split(",") if x.strip()],
        default=list(SISTEMAS_VALIDOS),
    )
    p.add_argument("--ms-marco-dir", type=Path, default=Path("../data/ms_marco"))
    p.add_argument("--embeddings-dir", type=Path, default=Path("../data/embeddings"))
    p.add_argument("--results-dir", type=Path, default=Path("./results"))
    a = p.parse_args(argv)

    if a.n <= 0:
        p.error(f"--n deve ser > 0 (recebido {a.n}).")
    if a.queries <= 0:
        p.error(f"--queries deve ser > 0 (recebido {a.queries}).")
    if a.k <= 0:
        p.error(f"--k deve ser > 0 (recebido {a.k}).")
    if a.warmup < 0:
        p.error(f"--warmup deve ser >= 0 (recebido {a.warmup}).")
    if not a.ef_search:
        p.error("--ef-search vazio.")
    desconhecidos = set(a.sistemas) - set(SISTEMAS_VALIDOS)
    if desconhecidos:
        p.error(f"sistemas desconhecidos: {sorted(desconhecidos)}. Válidos: {SISTEMAS_VALIDOS}.")

    return Config(
        n_base=a.n,
        n_queries=a.queries,
        k=a.k,
        ef_search=a.ef_search,
        warmup=a.warmup,
        sistemas=a.sistemas,
        ms_marco_dir=a.ms_marco_dir,
        embeddings_dir=a.embeddings_dir,
        results_dir=a.results_dir,
    )


def split_embeddings(
    embeddings: np.ndarray, *, n_base: int, n_queries: int
) -> tuple[np.ndarray, np.ndarray]:
    """Split determinístico: base = primeiros `n_base`; queries = `n_queries` held-out.

    As queries são os vetores imediatamente após a base — nunca sobrepõem o
    seed (ADR de queries held-out). Levanta `ValueError` se faltar dado.
    """
    preciso = n_base + n_queries
    if embeddings.shape[0] < preciso:
        raise ValueError(
            f"embeddings insuficiente: preciso {preciso} "
            f"(n_base={n_base} + n_queries={n_queries}), tenho {embeddings.shape[0]}."
        )
    base = embeddings[:n_base]
    queries = embeddings[n_base : n_base + n_queries]
    return base, queries


def timestamp_utc() -> str:
    """Timestamp UTC ISO FS-safe: `YYYY-MM-DDTHH-MM-SSZ` (sem `:`)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def _construir_buscador(sistema: str, *, nome_recurso: str, env: dict[str, str]):
    """Conecta ao SGBD e devolve o adaptador `BuscadorVetorial`."""
    from benchmarks.buscadores import (
        PgvectorBuscador,
        QdrantBuscador,
        WeaviateBuscador,
    )

    if sistema == "pgvector":
        import psycopg

        conn = psycopg.connect(
            f"host={env['PG_HOST']} port={env['PG_PORT']} dbname={env['PG_DATABASE']} "
            f"user={env['PG_USER']} password={env['PG_PASSWORD']}"
        )
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
        return PgvectorBuscador(conn=conn, nome_tabela=nome_recurso), conn
    if sistema == "qdrant":
        from qdrant_client import QdrantClient

        client = QdrantClient(host=env["QDRANT_HOST"], port=int(env["QDRANT_HTTP_PORT"]))
        return QdrantBuscador(client=client, nome_colecao=nome_recurso), client
    if sistema == "weaviate":
        import weaviate

        client = weaviate.connect_to_local(
            host=env["WEAVIATE_HOST"], port=int(env["WEAVIATE_PORT"])
        )
        return WeaviateBuscador(client=client, nome_classe=nome_recurso), client
    raise ValueError(f"sistema desconhecido: {sistema}")


def _limpar_recurso(sistema: str, *, recurso, nome_recurso: str) -> None:
    """Remove tabela/coleção/classe pré-existente — torna o CLI idempotente.

    Os seeders fazem `CREATE` sem `IF NOT EXISTS` (corretos para os testes de
    integração, que usam nomes únicos). O CLI reusa um nome estável por N, então
    precisa limpar antes de re-seedar. É scratch de benchmark, não dado real.
    """
    if sistema == "pgvector":
        with recurso.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {nome_recurso}")
        recurso.commit()
    elif sistema == "qdrant":
        if recurso.collection_exists(nome_recurso):
            recurso.delete_collection(collection_name=nome_recurso)
    elif sistema == "weaviate":
        if recurso.collections.exists(nome_recurso):
            recurso.collections.delete(nome_recurso)


def _seed(sistema: str, *, vetores: np.ndarray, recurso, nome_recurso: str) -> None:
    if sistema == "pgvector":
        from seeders.pgvector_seeder import seed_pgvector

        seed_pgvector(vetores=vetores, metadata=None, conn=recurso, nome_tabela=nome_recurso)
    elif sistema == "qdrant":
        from seeders.qdrant_seeder import seed_qdrant

        seed_qdrant(vetores=vetores, metadata=None, client=recurso, nome_colecao=nome_recurso)
    elif sistema == "weaviate":
        from seeders.weaviate_seeder import seed_weaviate

        seed_weaviate(vetores=vetores, metadata=None, client=recurso, nome_classe=nome_recurso)


def executar(cfg: Config) -> list[Path]:
    """Pipeline completo do Cenário A. Retorna os caminhos dos JSON gravados.

    Não é unit-testado (I/O pesado com Docker/embeddings); o caminho lógico é
    coberto por `tests/integration/test_buscadores.py`.
    """
    from dotenv import load_dotenv

    from ground_truth.exact_search import top_k_exato
    from lib.reporting import ResultadoBenchmark, salvar_curva, salvar_ground_truth
    from pipeline.embeddings import gerar_embeddings
    from pipeline.ms_marco_loader import sample_passages

    load_dotenv()
    env = dict(os.environ)

    tsv = cfg.ms_marco_dir / "collection.tsv"
    passages = sample_passages(tsv, n=cfg.n_base + cfg.n_queries)
    textos = [p.text for p in passages]
    embs = gerar_embeddings(textos, cache_dir=cfg.embeddings_dir)
    base, queries = split_embeddings(embs, n_base=cfg.n_base, n_queries=cfg.n_queries)

    _, gt_ids = top_k_exato(base, queries, k=cfg.k)
    salvar_ground_truth(
        np.zeros_like(gt_ids, dtype=np.float32),
        gt_ids,
        dest_dir=cfg.ms_marco_dir.parent / "ground_truth",
        nome=f"cenario_a_n{cfg.n_base}_q{cfg.n_queries}_k{cfg.k}",
    )

    ts = timestamp_utc()
    escritos: list[Path] = []
    for sistema in cfg.sistemas:
        nome_recurso = (
            f"{cfg.colecao_prefixo}_{cfg.n_base}"
            if sistema != "weaviate"
            else f"BenchA{cfg.n_base}"
        )
        buscador, recurso = _construir_buscador(sistema, nome_recurso=nome_recurso, env=env)
        try:
            _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome_recurso)
            _seed(sistema, vetores=base, recurso=recurso, nome_recurso=nome_recurso)
            from benchmarks.cenario_a import medir_sistema

            resultados: list[ResultadoBenchmark] = medir_sistema(
                buscador,
                queries=queries,
                gt_ids=gt_ids,
                ef_search_values=cfg.ef_search,
                k=cfg.k,
                n_base=cfg.n_base,
                timestamp_utc=ts,
                warmup=cfg.warmup,
                ambiente={"sistema": sistema},
            )
            escritos.append(salvar_curva(resultados, results_dir=cfg.results_dir))
        finally:
            if hasattr(recurso, "close"):
                recurso.close()

    return escritos


def main(argv: Sequence[str] | None = None) -> int:
    import sys

    cfg = parse_args(sys.argv[1:] if argv is None else argv)
    escritos = executar(cfg)
    print(f"Cenário A: {len(escritos)} resultado(s) gravado(s) em {cfg.results_dir}")
    for caminho in escritos:
        print(f"  {caminho}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
