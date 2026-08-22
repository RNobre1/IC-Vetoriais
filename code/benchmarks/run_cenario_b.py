"""CLI do Cenário B — busca com filtro de seletividade variável.

Estende o pipeline do Cenário A: sintetiza o atributo numérico `seletor`,
calcula um ground truth exato **por seletividade** e roda
`cenario_b.medir_sistema_filtrado` (sweep `seletividade × efSearch`) nos 3
SGBDs, gravando uma curva por sistema.

Decisões: [[../../vault/decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]
(predicado `seletor < p`; GT filtrado por p; p=1.0 = âncora sem filtro).
Queries held-out / warmup herdados de
[[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]].

Uso:
    python -m benchmarks.run_cenario_b --n 500 --queries 50 \\
        --ef-search 16,64 --seletividades 0.01,0.1,0.5,1.0

Partes puras (`parse_args`, `sintetizar_seletor`) têm testes unitários;
a orquestração (`executar`) é coberta pelo smoke
`tests/integration/test_buscadores_filtrado.py` + run real.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from benchmarks.run_cenario_a import (
    SISTEMAS_VALIDOS,
    _construir_buscador,
    _limpar_recurso,
    _medir_recursos,
    _rss_baseline,
    split_embeddings,
    timestamp_utc,
)

EF_SEARCH_PADRAO = [16, 32, 64, 128, 256]
SELETIVIDADES_PADRAO = [0.01, 0.1, 0.5, 1.0]
SEED_SELETOR = 42


@dataclass(frozen=True, slots=True)
class Config:
    n_base: int = 10_000
    n_queries: int = 1_000
    k: int = 10
    ef_search: list[int] = field(default_factory=lambda: list(EF_SEARCH_PADRAO))
    seletividades: list[float] = field(default_factory=lambda: list(SELETIVIDADES_PADRAO))
    warmup: int = 50
    sistemas: list[str] = field(default_factory=lambda: list(SISTEMAS_VALIDOS))
    ms_marco_dir: Path = Path("../data/ms_marco")
    embeddings_dir: Path = Path("../data/embeddings")
    results_dir: Path = Path("./results")
    colecao_prefixo: str = "bench_b"
    equalizado: bool = False


def _lista_int(texto: str) -> list[int]:
    try:
        return [int(x) for x in texto.split(",") if x.strip()]
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"lista de inteiros inválida: {texto!r}") from e


def _lista_float(texto: str) -> list[float]:
    try:
        return [float(x) for x in texto.split(",") if x.strip()]
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"lista de floats inválida: {texto!r}") from e


def sintetizar_seletor(n_base: int, *, seed: int = SEED_SELETOR) -> np.ndarray:
    """Atributo `seletor` uniforme determinístico decorrelacionado, shape `(N,)`.

    Valores = permutação (semente fixa) de `{0, 1/N, …, (N-1)/N}`: únicos,
    uniformes em `[0, 1)`, decorrelacionados do id (a permutação quebra
    qualquer correlação com a ordem de inserção do MS MARCO). Logo
    `seletor < p` mantém exatamente `ceil(p·N)` vetores — seletividade `p`
    a menos de ±1/N. Vide ADR
    [[../../vault/decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]].
    """
    rng = np.random.default_rng(seed)
    return rng.permutation(n_base).astype(np.float64) / n_base


def parse_args(argv: Sequence[str]) -> Config:
    """Converte argv em `Config`. Sai com erro (SystemExit) em entrada inválida."""
    p = argparse.ArgumentParser(prog="run_cenario_b", description="Cenário B — busca com filtro.")
    p.add_argument("--n", type=int, default=10_000, help="tamanho da base seedada.")
    p.add_argument("--queries", type=int, default=1_000, help="nº de queries held-out.")
    p.add_argument("--k", type=int, default=10, help="K do recall@K / top-K.")
    p.add_argument("--ef-search", type=_lista_int, default=list(EF_SEARCH_PADRAO))
    p.add_argument(
        "--seletividades",
        type=_lista_float,
        default=list(SELETIVIDADES_PADRAO),
        help="frações elegíveis do predicado seletor<p (ex.: 0.01,0.1,0.5,1.0).",
    )
    p.add_argument("--warmup", type=int, default=50, help="buscas de aquecimento.")
    p.add_argument(
        "--sistemas",
        type=lambda s: [x.strip() for x in s.split(",") if x.strip()],
        default=list(SISTEMAS_VALIDOS),
    )
    p.add_argument("--ms-marco-dir", type=Path, default=Path("../data/ms_marco"))
    p.add_argument("--embeddings-dir", type=Path, default=Path("../data/embeddings"))
    p.add_argument("--results-dir", type=Path, default=Path("./results"))
    p.add_argument(
        "--equalizado",
        action="store_true",
        help=(
            "equipara o tratamento do atributo de filtro nos 3 SGBDs: B-tree em "
            "`seletor` no pgvector, full_scan_threshold no mínimo (10 KB) no "
            "Qdrant e flatSearchCutoff=0 no Weaviate. Sem isso, seletividades "
            "baixas são respondidas por busca exata e o recall medido não é de ANN."
        ),
    )
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
    if not a.seletividades:
        p.error("--seletividades vazio.")
    fora = [s for s in a.seletividades if not (0.0 < s <= 1.0)]
    if fora:
        p.error(f"--seletividades fora de (0, 1]: {fora}.")
    desconhecidos = set(a.sistemas) - set(SISTEMAS_VALIDOS)
    if desconhecidos:
        p.error(f"sistemas desconhecidos: {sorted(desconhecidos)}. Válidos: {SISTEMAS_VALIDOS}.")

    return Config(
        n_base=a.n,
        n_queries=a.queries,
        k=a.k,
        ef_search=a.ef_search,
        seletividades=a.seletividades,
        warmup=a.warmup,
        sistemas=a.sistemas,
        ms_marco_dir=a.ms_marco_dir,
        embeddings_dir=a.embeddings_dir,
        results_dir=a.results_dir,
        equalizado=a.equalizado,
        # Prefixo próprio: um re-run equalizado não pode reaproveitar nem
        # sobrescrever os recursos semeados na configuração default.
        colecao_prefixo="bench_b_eq" if a.equalizado else "bench_b",
    )


def nome_classe_weaviate(colecao_prefixo: str) -> str:
    """`bench_b` -> `BenchB`; `bench_b_eq` -> `BenchBEq`.

    O Weaviate exige nome de classe em CamelCase, então o prefixo não pode ser
    reaproveitado cru. Derivar em vez de manter uma segunda lista de nomes
    garante que um prefixo novo já nasça coberto nos três sistemas.
    """
    return "".join(parte.capitalize() for parte in colecao_prefixo.split("_"))


def _seed_b(
    sistema: str,
    *,
    vetores: np.ndarray,
    metadata,
    recurso,
    nome_recurso: str,
    equalizado: bool = False,
) -> tuple[float | None, float]:
    """Igual ao seed do Cenário A, porém passando o `metadata` com `seletor`.

    Com `equalizado=True`, os três sistemas passam a tratar o atributo de filtro
    da mesma forma: índice dedicado em `seletor` nos três e limiar de busca
    exata zerado nos dois especializados, de modo que toda seletividade seja
    respondida por HNSW. Vide `vault/decisões/2026-08-16-equalizacao-cenario-b`.

    Devolve `(tempo_carga_s, tempo_indice_utilizavel_s)`, como o Cenário A.
    """
    from lib.footprint import INTERVALO_PADRAO, TENTATIVAS_PADRAO, cronometrar_indexacao

    if sistema == "pgvector":
        from seeders.pgvector_seeder import seed_pgvector

        return cronometrar_indexacao(
            sistema,
            carregar=lambda: seed_pgvector(
                vetores=vetores,
                metadata=metadata,
                conn=recurso,
                nome_tabela=nome_recurso,
                indexar_seletor=equalizado,
            ),
        )
    if sistema == "qdrant":
        from seeders.qdrant_seeder import FULL_SCAN_MINIMO, aguardar_green, seed_qdrant

        return cronometrar_indexacao(
            sistema,
            carregar=lambda: seed_qdrant(
                vetores=vetores,
                metadata=metadata,
                client=recurso,
                nome_colecao=nome_recurso,
                full_scan_threshold=FULL_SCAN_MINIMO if equalizado else None,
                aguardar_indexacao=False,
            ),
            aguardar_indice=lambda: aguardar_green(
                recurso, nome_recurso, tentativas=TENTATIVAS_PADRAO, intervalo=INTERVALO_PADRAO
            ),
        )
    if sistema == "weaviate":
        from lib.footprint import aguardar_fila_weaviate
        from seeders.weaviate_seeder import seed_weaviate

        return cronometrar_indexacao(
            sistema,
            carregar=lambda: seed_weaviate(
                vetores=vetores,
                metadata=metadata,
                client=recurso,
                nome_classe=nome_recurso,
                flat_search_cutoff=0 if equalizado else None,
                aguardar_indexacao=False,
            ),
            aguardar_indice=lambda: aguardar_fila_weaviate(recurso, nome_classe=nome_recurso),
        )
    raise ValueError(f"sistema desconhecido: {sistema}")


def executar(cfg: Config) -> list[Path]:
    """Pipeline completo do Cenário B. Retorna os caminhos dos JSON gravados.

    Não é unit-testado (I/O pesado); o caminho lógico é coberto por
    `tests/integration/test_buscadores_filtrado.py` + run real.
    """
    from dotenv import load_dotenv

    from benchmarks.cenario_b import medir_sistema_filtrado
    from ground_truth.exact_search import top_k_exato_filtrado
    from lib.reporting import salvar_curva, salvar_ground_truth
    from pipeline.embeddings import gerar_embeddings
    from pipeline.ms_marco_loader import sample_passages

    load_dotenv()
    env = dict(os.environ)

    tsv = cfg.ms_marco_dir / "collection.tsv"
    passages = sample_passages(tsv, n=cfg.n_base + cfg.n_queries)
    textos = [p.text for p in passages]
    embs = gerar_embeddings(textos, cache_dir=cfg.embeddings_dir)
    base, queries = split_embeddings(embs, n_base=cfg.n_base, n_queries=cfg.n_queries)

    seletor = sintetizar_seletor(cfg.n_base)
    metadata = [{"seletor": float(seletor[i])} for i in range(cfg.n_base)]

    gt_dir = cfg.ms_marco_dir.parent / "ground_truth"
    gt_por_seletividade: dict[float, np.ndarray] = {}
    for p in cfg.seletividades:
        scores, gt_ids = top_k_exato_filtrado(base, queries, seletor=seletor, p=p, k=cfg.k)
        gt_por_seletividade[p] = gt_ids
        salvar_ground_truth(
            scores,
            gt_ids,
            dest_dir=gt_dir,
            nome=f"cenario_b_n{cfg.n_base}_q{cfg.n_queries}_k{cfg.k}_p{p}",
        )

    ts = timestamp_utc()
    escritos: list[Path] = []
    for sistema in cfg.sistemas:
        nome_recurso = (
            f"{cfg.colecao_prefixo}_{cfg.n_base}"
            if sistema != "weaviate"
            else f"{nome_classe_weaviate(cfg.colecao_prefixo)}{cfg.n_base}"
        )
        buscador, recurso = _construir_buscador(sistema, nome_recurso=nome_recurso, env=env)
        try:
            _limpar_recurso(sistema, recurso=recurso, nome_recurso=nome_recurso)
            rss_baseline = _rss_baseline(sistema)
            t_carga, t_indice = _seed_b(
                sistema,
                vetores=base,
                metadata=metadata,
                recurso=recurso,
                nome_recurso=nome_recurso,
                equalizado=cfg.equalizado,
            )
            recursos = _medir_recursos(
                sistema,
                recurso=recurso,
                nome_recurso=nome_recurso,
                tempo_carga_s=t_carga,
                tempo_indice_utilizavel_s=t_indice,
                rss_baseline_bytes=rss_baseline,
            )
            resultados = medir_sistema_filtrado(
                buscador,
                queries=queries,
                gt_por_seletividade=gt_por_seletividade,
                ef_search_values=cfg.ef_search,
                seletividades=cfg.seletividades,
                k=cfg.k,
                n_base=cfg.n_base,
                timestamp_utc=ts,
                warmup=cfg.warmup,
                # `equalizado` vai para o JSON: sem isso, duas curvas do mesmo
                # sistema e mesmo N ficam indistinguíveis no diretório.
                ambiente={"sistema": sistema, "equalizado": cfg.equalizado},
            )
            escritos.append(
                salvar_curva(resultados, results_dir=cfg.results_dir, recursos=recursos)
            )
        finally:
            if hasattr(recurso, "close"):
                recurso.close()

    return escritos


def main(argv: Sequence[str] | None = None) -> int:
    import sys

    cfg = parse_args(sys.argv[1:] if argv is None else argv)
    escritos = executar(cfg)
    print(f"Cenário B: {len(escritos)} resultado(s) gravado(s) em {cfg.results_dir}")
    for caminho in escritos:
        print(f"  {caminho}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
