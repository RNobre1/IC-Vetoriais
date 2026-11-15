"""Executor da sessão de medição: todos os cenários de um sistema numa escala.

Uma chamada mede um sistema numa escala, do seed ao descarte, com o menor
número de seeds que preserva o que cada cenário mede. Decisão em
[[../../vault/decisões/2026-11-15-protocolo-da-sessao-final]]:

- **pgvector**: um seed por escala, no layout do Cenário B (vetores + coluna
  `seletor` preenchida, sem índice nela). Nele se medem recursos, A e B
  padrão; o B equalizado ganha só o B-tree em `seletor`, e o C roda depois de
  o B-tree ser removido. O build do HNSW em 1M é o passo mais caro da sessão e
  é idêntico nos três layouts — semeá-lo três vezes não mede nada novo.
- **Qdrant e Weaviate**: um seed por layout (A, B padrão, B equalizado),
  porque são baratos e porque o índice de payload pode alterar o grafo do
  Qdrant, o que contaminaria o A. O C roda na coleção do A.
- Cada sistema é medido sem dados dos outros: o contêiner e o volume do
  serviço são recriados no início e a cada descarte, de modo que a linha de
  base de memória não carrega heap de coleções anteriores. Os contêineres dos
  outros dois sistemas continuam de pé, vazios e ociosos.

Os JSONs têm o mesmo formato dos CLIs `run_cenario_a`/`run_cenario_b`, mais o
Cenário C. Marcos de fase vão para um JSONL; cruzados com o CSV do
amostrador de recursos (`lib.monitor`), atribuem memória, CPU e swap a cada
fase na análise.

Uso:
    python -m benchmarks.run_sessao --n 1000000 --sistema qdrant --cenario-c \\
        --marcos results/sessoes/2026-11-15/marcos.jsonl
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks.cenario_c import SEQUENCIA_JANELAS_PADRAO, tamanho_lote, vetores_necessarios
from benchmarks.run_cenario_a import SISTEMAS_VALIDOS

EF_SEARCH_PADRAO = [16, 32, 64, 128, 256]
SELETIVIDADES_PADRAO = [0.01, 0.1, 0.5, 1.0]
EF_REFERENCIA = 64

# flatSearchCutoff padrão do Weaviate (objetos elegíveis). Abaixo dele, o B
# padrão responde por varredura exata; acima, executa o mesmo caminho HNSW
# do B equalizado.
CORTE_FLAT_WEAVIATE = 40_000
# A partir desta escala o B padrão do Weaviate acima do corte é medido só no
# ponto de referência (custo de horas); a primeira seletividade acima do
# corte fica completa como controle do mecanismo.
ESCALA_REDUCAO_WEAVIATE = 500_000

SERVICO_POR_SISTEMA = {
    "pgvector": "postgres-pgvector",
    "qdrant": "qdrant",
    "weaviate": "weaviate",
}


# ---------------------------------------------------------------------------
# Plano (dado puro)
# ---------------------------------------------------------------------------


def plano_de_passos(sistema: str, *, cenario_c: bool) -> list[str]:
    """Sequência de passos de um sistema numa escala."""
    if sistema == "pgvector":
        passos = ["seed_b", "A", "B", "btree", "B_eq"]
        if cenario_c:
            passos += ["drop_btree", "C"]
        return [*passos, "limpar"]
    if sistema in ("qdrant", "weaviate"):
        # O C fica por último, como no pgvector: se a escrita concorrente
        # falhar, os demais cenários do sistema já estão gravados.
        bloco_a = ["seed_a", "A", *(["C"] if cenario_c else []), "limpar"]
        return ["seed_b", "B", "limpar", "seed_b_eq", "B_eq", "limpar", *bloco_a]
    raise ValueError(f"sistema desconhecido: {sistema}")


def ordem_dos_sistemas(n: int) -> list[str]:
    """Ordem dos sistemas, girada por escala para não confundir ordem com sistema."""
    if n == 1_000_000:
        return ["qdrant", "weaviate", "pgvector"]
    if n == 500_000:
        return ["weaviate", "pgvector", "qdrant"]
    return ["pgvector", "qdrant", "weaviate"]


def varredura_b(
    sistema: str,
    *,
    n: int,
    equalizado: bool,
    seletividades: Sequence[float],
    efs: Sequence[int],
) -> list[tuple[list[float], list[int]]]:
    """Blocos `(seletividades, efs)` do Cenário B para um sistema e condição."""
    sels, efl = list(seletividades), list(efs)
    if sistema != "weaviate" or equalizado or n < ESCALA_REDUCAO_WEAVIATE:
        return [(sels, efl)]
    abaixo = [p for p in sels if p * n < CORTE_FLAT_WEAVIATE]
    acima = [p for p in sels if p * n >= CORTE_FLAT_WEAVIATE]
    controle, reduzidas = acima[:1], acima[1:]
    if not reduzidas or EF_REFERENCIA not in efl:
        return [(sels, efl)]
    return [(abaixo + controle, efl), (reduzidas, [EF_REFERENCIA])]


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfigSessao:
    n_base: int
    sistema: str
    n_queries: int = 1_000
    k: int = 10
    ef_search: list[int] = field(default_factory=lambda: list(EF_SEARCH_PADRAO))
    seletividades: list[float] = field(default_factory=lambda: list(SELETIVIDADES_PADRAO))
    warmup: int = 50
    repeticoes_a: int = 5
    cenario_c: bool = False
    janelas_c: list[int] = field(default_factory=lambda: list(SEQUENCIA_JANELAS_PADRAO))
    aquecimento_c_s: float = 5.0
    duracao_c_s: float = 60.0
    tick_c_s: float = 0.1
    ef_c: int = EF_REFERENCIA
    pool_c: int = 80_000
    ms_marco_dir: Path = Path("../data/ms_marco")
    embeddings_dir: Path = Path("../data/embeddings")
    results_dir: Path = Path("./results")
    marcos: Path | None = None


def _lista(tipo):
    def conv(texto: str):
        try:
            return [tipo(x) for x in texto.split(",") if x.strip()]
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"lista inválida: {texto!r}") from e

    return conv


def parse_args(argv: Sequence[str]) -> ConfigSessao:
    p = argparse.ArgumentParser(prog="run_sessao", description="Sessão de medição por sistema.")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--sistema", required=True)
    p.add_argument("--queries", type=int, default=1_000)
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--ef-search", type=_lista(int), default=list(EF_SEARCH_PADRAO))
    p.add_argument("--seletividades", type=_lista(float), default=list(SELETIVIDADES_PADRAO))
    p.add_argument("--warmup", type=int, default=50)
    p.add_argument("--repeticoes-a", type=int, default=5)
    p.add_argument("--cenario-c", action="store_true")
    p.add_argument("--janelas-c", type=_lista(int), default=list(SEQUENCIA_JANELAS_PADRAO))
    p.add_argument("--aquecimento-c", type=float, default=5.0)
    p.add_argument("--duracao-c", type=float, default=60.0)
    p.add_argument("--tick-c", type=float, default=0.1)
    p.add_argument("--ef-c", type=int, default=EF_REFERENCIA)
    p.add_argument("--pool-c", type=int, default=80_000)
    p.add_argument("--ms-marco-dir", type=Path, default=Path("../data/ms_marco"))
    p.add_argument("--embeddings-dir", type=Path, default=Path("../data/embeddings"))
    p.add_argument("--results-dir", type=Path, default=Path("./results"))
    p.add_argument("--marcos", type=Path, default=None)
    a = p.parse_args(argv)

    if a.sistema not in SISTEMAS_VALIDOS:
        p.error(f"sistema desconhecido: {a.sistema}. Válidos: {SISTEMAS_VALIDOS}.")
    if a.n <= 0 or a.queries <= 0 or a.k <= 0 or a.warmup < 0 or a.repeticoes_a < 1:
        p.error("--n, --queries, --k e --repeticoes-a precisam ser positivos; --warmup >= 0.")
    if a.cenario_c:
        precisa = vetores_necessarios(
            a.janelas_c, aquecimento_s=a.aquecimento_c, duracao_s=a.duracao_c
        )
        if a.pool_c < precisa:
            p.error(f"--pool-c {a.pool_c} menor que os {precisa} vetores que as janelas pedem.")
        try:
            for taxa in a.janelas_c:
                tamanho_lote(taxa, tick_s=a.tick_c)
        except ValueError as e:
            p.error(f"--janelas-c: {e}")

    return ConfigSessao(
        n_base=a.n,
        sistema=a.sistema,
        n_queries=a.queries,
        k=a.k,
        ef_search=a.ef_search,
        seletividades=a.seletividades,
        warmup=a.warmup,
        repeticoes_a=a.repeticoes_a,
        cenario_c=a.cenario_c,
        janelas_c=a.janelas_c,
        aquecimento_c_s=a.aquecimento_c,
        duracao_c_s=a.duracao_c,
        tick_c_s=a.tick_c,
        ef_c=a.ef_c,
        pool_c=a.pool_c,
        ms_marco_dir=a.ms_marco_dir,
        embeddings_dir=a.embeddings_dir,
        results_dir=a.results_dir,
        marcos=a.marcos,
    )


# ---------------------------------------------------------------------------
# Marcos de fase e sondas do hospedeiro
# ---------------------------------------------------------------------------


def _agora_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def registrar_marco(
    arquivo: Path | None,
    *,
    n: int,
    sistema: str,
    passo: str,
    evento: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Acrescenta uma linha JSON com o instante de uma fase (início/fim)."""
    linha = {"ts_utc": _agora_utc(), "n": n, "sistema": sistema, "passo": passo, "evento": evento}
    linha.update(extra or {})
    print(json.dumps(linha, ensure_ascii=False), flush=True)
    if arquivo is None:
        return
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(linha, ensure_ascii=False, sort_keys=True) + "\n")


def sonda_cpu(iteracoes: int = 3_000_000) -> dict[str, Any]:
    """Tempo de uma carga fixa de CPU em uma thread.

    Rodada antes e depois de cada bloco: se o hospedeiro mudar de velocidade
    ao longo da noite (térmica, frequência), a mudança aparece aqui, separada
    do sistema que estava sendo medido.
    """
    t0 = time.perf_counter()
    acc = 0
    for i in range(iteracoes):
        acc += i * i % 7
    return {"sonda_cpu_s": time.perf_counter() - t0, "sonda_cpu_iteracoes": iteracoes}


def ler_pswpout() -> int | None:
    """Páginas enviadas ao swap desde o boot (`/proc/vmstat`); `None` fora do Linux."""
    try:
        with open("/proc/vmstat", encoding="ascii") as fh:
            for linha in fh:
                if linha.startswith("pswpout "):
                    return int(linha.split()[1])
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------
# Serviços Docker
# ---------------------------------------------------------------------------


def _docker(argv: list[str], *, checar: bool = True) -> str:
    r = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    if checar and r.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)} falhou ({r.returncode}): {r.stderr.strip()}")
    return r.stdout.strip()


def reiniciar_servico(sistema: str, *, espera_s: int = 300) -> float:
    """Recria contêiner e volume do serviço do `sistema`; devolve a duração.

    É o reset por sistema: zera os dados e devolve ao sistema operacional a
    memória que o processo retinha de coleções anteriores.
    """
    from lib.footprint import CONTAINER_POR_SISTEMA

    t0 = time.perf_counter()
    container = CONTAINER_POR_SISTEMA[sistema]
    servico = SERVICO_POR_SISTEMA[sistema]
    volumes = _docker(
        [
            "docker",
            "inspect",
            "-f",
            '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}} {{end}}{{end}}',
            container,
        ],
        checar=False,
    ).split()
    _docker(["docker", "compose", "rm", "-s", "-f", servico])
    for vol in volumes:
        _docker(["docker", "volume", "rm", vol])
    _docker(["docker", "compose", "up", "-d", servico])
    limite = time.monotonic() + espera_s
    while time.monotonic() < limite:
        estado = _docker(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", container], checar=False
        )
        if estado == "healthy":
            return time.perf_counter() - t0
        time.sleep(1.0)
    raise TimeoutError(f"{container} não ficou healthy em {espera_s} s após recriação.")


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


@dataclass
class _Estado:
    """Conexão e recursos do layout que está semeado no momento."""

    buscador: Any = None
    recurso: Any = None
    nome: str = ""
    layout: str = ""
    recursos: Any = None
    extra_seed: dict[str, Any] = field(default_factory=dict)

    def fechar(self) -> None:
        if self.recurso is not None and hasattr(self.recurso, "close"):
            # O serviço pode já ter sido recriado; a conexão morta não importa.
            with contextlib.suppress(Exception):
                self.recurso.close()
        self.buscador = self.recurso = None


def _fora_de_transacao(conn: Any, sql: str) -> None:
    """Executa `sql` em autocommit (VACUUM e CHECKPOINT recusam transação)."""
    conn.commit()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.autocommit = False


def _nome_recurso(sistema: str, layout: str, n: int) -> str:
    prefixo = {"A": "bench_a", "B": "bench_b", "B_eq": "bench_b_eq"}[layout]
    if sistema != "weaviate":
        return f"{prefixo}_{n}"
    from benchmarks.run_cenario_b import nome_classe_weaviate

    return f"{nome_classe_weaviate(prefixo)}{n}"


def _metricas_tolerantes(b: Any, *, gt: Any, k: int, id0: int) -> dict[str, Any]:
    """Métricas da janela; se o recall falhar, grava o resto e o erro."""
    from benchmarks.cenario_c import metricas_da_janela, resumir_consultas, resumir_producao

    try:
        if gt is None:
            raise RuntimeError("verdade exata incremental indisponível")
        return metricas_da_janela(b, gt=gt, k=k, id_insercao_inicial=id0)
    except Exception as e:  # noqa: BLE001 — não perder latência e taxa por causa do recall
        return {
            **resumir_consultas(b.latencias_ms),
            **resumir_producao(
                b.registros, inicio_medicao=b.inicio_medicao, fim_medicao=b.fim_medicao
            ),
            "inseridos_acumulados_antes": b.m_antes,
            "inseridos_acumulados_depois": b.m_depois,
            "erro_recall": repr(e)[:300],
        }


def _ts_livre(results_dir: Path, cenario: str, sistema: str, n: int) -> str:
    """Timestamp cujo arquivo de curva ainda não existe (nunca sobrescreve)."""
    from benchmarks.run_cenario_a import timestamp_utc

    while True:
        ts = timestamp_utc()
        if not (results_dir / f"cenario_{cenario}_{sistema}_{n}_{ts}.json").exists():
            return ts
        time.sleep(1.0)


def executar(cfg: ConfigSessao) -> list[Path]:  # noqa: C901 — sequência linear de passos
    """Mede um sistema numa escala, passo a passo. Devolve os JSONs gravados."""
    from dotenv import load_dotenv

    from benchmarks.cenario_a import medir_sistema
    from benchmarks.cenario_b import medir_sistema_filtrado
    from benchmarks.cenario_c import (
        ConfigC,
        GtIncremental,
        executar_janelas,
    )
    from benchmarks.insersores import FabricaInseridor, contar
    from benchmarks.run_cenario_a import (
        _construir_buscador,
        _medir_recursos,
        _rss_baseline,
        _seed,
        split_embeddings,
    )
    from benchmarks.run_cenario_b import _seed_b, sintetizar_seletor
    from ground_truth.exact_search import top_k_exato, top_k_exato_filtrado
    from lib.footprint import executar_docker, medir_rss_bytes
    from lib.reporting import ResultadoBenchmark, salvar_curva
    from pipeline.embeddings import gerar_embeddings
    from pipeline.ms_marco_loader import sample_passages

    load_dotenv()
    env = dict(os.environ)
    s, n = cfg.sistema, cfg.n_base
    plano = plano_de_passos(s, cenario_c=cfg.cenario_c)

    def marco(passo: str, evento: str, extra: dict[str, Any] | None = None) -> None:
        registrar_marco(cfg.marcos, n=n, sistema=s, passo=passo, evento=evento, extra=extra)

    marco("bloco", "inicio", {"plano": plano, **sonda_cpu()})

    # --- dados e verdades exatas --------------------------------------------
    marco("dados", "inicio")
    tsv = cfg.ms_marco_dir / "collection.tsv"
    total = n + cfg.n_queries + (cfg.pool_c if cfg.cenario_c else 0)
    textos = [p.text for p in sample_passages(tsv, n=total)]
    embs = gerar_embeddings(textos[: n + cfg.n_queries], cache_dir=cfg.embeddings_dir)
    base, queries = split_embeddings(embs, n_base=n, n_queries=cfg.n_queries)
    pool = (
        gerar_embeddings(textos[n + cfg.n_queries :], cache_dir=cfg.embeddings_dir)
        if cfg.cenario_c
        else None
    )
    del textos
    _, gt_a = top_k_exato(base, queries, k=cfg.k)
    seletor = sintetizar_seletor(n)
    metadata = [{"seletor": float(seletor[i])} for i in range(n)]
    gt_b = {
        p: top_k_exato_filtrado(base, queries, seletor=seletor, p=p, k=cfg.k)[1]
        for p in cfg.seletividades
    }
    marco("dados", "fim")

    escritos: list[Path] = []
    est = _Estado()
    ambiente_base = {
        "sistema": s,
        "protocolo": "sessao-2026-11",
        "ordem_sistemas": ordem_dos_sistemas(n),
        "tentativa": int(os.environ.get("SESSAO_TENTATIVA", "1")),
    }

    def conectar(layout: str) -> None:
        est.fechar()
        est.nome = _nome_recurso(s, layout, n)
        est.layout = layout
        # "healthy" não garante a porta TCP: em volume novo, o entrypoint do
        # PostgreSQL responde ao `pg_isready` pelo socket Unix antes de o
        # servidor definitivo abrir a porta. Tenta de novo por até ~60 s.
        for tentativa in range(12):
            try:
                est.buscador, est.recurso = _construir_buscador(s, nome_recurso=est.nome, env=env)
                return
            except Exception as e:  # noqa: BLE001 — qualquer falha de conexão
                if tentativa == 11:
                    raise
                marco("conectar", "nova_tentativa", {"erro": repr(e)[:200]})
                time.sleep(5.0)

    def medir_swap(passo: str, fn):
        antes = ler_pswpout()
        marco(passo, "inicio")
        r = fn()
        depois = ler_pswpout()
        delta = None if antes is None or depois is None else depois - antes
        marco(passo, "fim", {"swap_out_paginas": delta})
        return r, delta

    def semear(layout: str, equalizado: bool | None) -> None:
        conectar(layout)
        rss0 = _rss_baseline(s)
        if layout == "A":
            t_carga, t_indice = _seed(s, vetores=base, recurso=est.recurso, nome_recurso=est.nome)
        else:
            t_carga, t_indice = _seed_b(
                s,
                vetores=base,
                metadata=metadata,
                recurso=est.recurso,
                nome_recurso=est.nome,
                equalizado=bool(equalizado),
            )
        est.recursos = _medir_recursos(
            s,
            recurso=est.recurso,
            nome_recurso=est.nome,
            tempo_carga_s=t_carga,
            tempo_indice_utilizavel_s=t_indice,
            rss_baseline_bytes=rss0,
        )
        est.extra_seed = {"layout_seed": layout}
        if s == "pgvector":
            # Fora do relógio: sem isto, hint bits e estatísticas de `seletor`
            # dependeriam do autovacuum, e o planner do B também.
            t0 = time.perf_counter()
            _fora_de_transacao(est.recurso, f"VACUUM (ANALYZE) {est.nome}")
            est.extra_seed["vacuum_analyze_s"] = time.perf_counter() - t0

    def gravar(resultados, recursos) -> None:
        escritos.append(salvar_curva(resultados, results_dir=cfg.results_dir, recursos=recursos))
        print(f"gravado: {escritos[-1]}", flush=True)

    def passo_a() -> None:
        ts = _ts_livre(cfg.results_dir, "A", s, n)

        def medir():
            return medir_sistema(
                est.buscador,
                queries=queries,
                gt_ids=gt_a,
                ef_search_values=cfg.ef_search,
                k=cfg.k,
                n_base=n,
                timestamp_utc=ts,
                warmup=cfg.warmup,
                repeticoes=cfg.repeticoes_a,
                ambiente={**ambiente_base, **est.extra_seed},
            )

        resultados, delta = medir_swap("A", medir)
        for r in resultados:
            r.ambiente["swap_out_paginas_no_passo"] = delta
        gravar(resultados, est.recursos)

    def passo_b(equalizado: bool, passo: str, extra: dict[str, Any] | None = None) -> None:
        ts = _ts_livre(cfg.results_dir, "B", s, n)
        blocos = varredura_b(
            s, n=n, equalizado=equalizado, seletividades=cfg.seletividades, efs=cfg.ef_search
        )

        def medir():
            todos = []
            for sels, efs in blocos:
                todos += medir_sistema_filtrado(
                    est.buscador,
                    queries=queries,
                    gt_por_seletividade=gt_b,
                    ef_search_values=efs,
                    seletividades=sels,
                    k=cfg.k,
                    n_base=n,
                    timestamp_utc=ts,
                    warmup=cfg.warmup,
                    ambiente={
                        **ambiente_base,
                        **est.extra_seed,
                        **(extra or {}),
                        "equalizado": equalizado,
                    },
                )
            return todos

        resultados, delta = medir_swap(passo, medir)
        for r in resultados:
            r.ambiente["swap_out_paginas_no_passo"] = delta
            r.ambiente["varredura_reduzida"] = len(blocos) > 1
        gravar(resultados, est.recursos)

    def passo_btree() -> dict[str, Any]:
        t0 = time.perf_counter()
        with est.recurso.cursor() as cur:
            cur.execute(f"CREATE INDEX {est.nome}_seletor_idx ON {est.nome} USING btree (seletor)")
            cur.execute(f"ANALYZE {est.nome}")
        est.recurso.commit()
        return {"btree_seletor_s": time.perf_counter() - t0, "seed_compartilhado": True}

    def passo_c() -> None:
        from lib.footprint import aguardar_fila_weaviate
        from seeders.qdrant_seeder import aguardar_green

        ts = _ts_livre(cfg.results_dir, "C", s, n)
        cfg_c = ConfigC(
            n_base=n,
            n_queries=cfg.n_queries,
            k=cfg.k,
            ef_search=cfg.ef_c,
            janelas=list(cfg.janelas_c),
            aquecimento_s=cfg.aquecimento_c_s,
            duracao_s=cfg.duracao_c_s,
            tick_s=cfg.tick_c_s,
            n_insercoes_pool=cfg.pool_c,
        )
        id0 = n + cfg.n_queries
        est.buscador.configurar_ef_search(cfg.ef_c)
        ultima = len(cfg_c.janelas) - 1

        def stats_checkpointer() -> dict[str, Any]:
            with est.recurso.cursor() as cur:
                cur.execute("SELECT * FROM pg_stat_checkpointer")
                cols = [d.name for d in cur.description]
                linha = cur.fetchone()
            est.recurso.commit()
            return {
                c: (v.isoformat() if hasattr(v, "isoformat") else v)
                for c, v in zip(cols, linha, strict=True)
            }

        def tentar(extra: dict[str, Any], chave: str, fn) -> None:
            """Telemetria item a item: a falha de um não pula os outros."""
            try:
                extra[chave] = fn()
            except Exception as e:  # noqa: BLE001
                extra[f"erro_{chave}"] = repr(e)[:300]
                if s == "pgvector":
                    # Consulta que falhou deixa a transação abortada; a
                    # busca seguinte falharia junto.
                    with contextlib.suppress(Exception):
                        est.recurso.rollback()

        def antes(ordem: int, taxa: int) -> dict[str, Any]:
            extra: dict[str, Any] = {}
            # Passos de protocolo primeiro, telemetria depois.
            if ordem == ultima and cfg_c.assentar_antes_da_ultima:
                t0 = time.perf_counter()
                if s == "qdrant":
                    aguardar_green(est.recurso, est.nome, tentativas=1800, intervalo=1.0)
                elif s == "weaviate":
                    aguardar_fila_weaviate(est.recurso, nome_classe=est.nome)
                extra["assentar_s"] = time.perf_counter() - t0
            if s == "pgvector":
                _fora_de_transacao(est.recurso, "CHECKPOINT")
                tentar(extra, "checkpointer_antes", stats_checkpointer)
            tentar(extra, "swap_out_antes", ler_pswpout)
            tentar(extra, "rss_inicio_bytes", lambda: medir_rss_bytes(executar_docker, sistema=s))
            marco("C", "janela_inicio", {"ordem": ordem, "taxa": taxa})
            return extra

        def depois(ordem: int, taxa: int) -> dict[str, Any]:
            extra: dict[str, Any] = {}
            tentar(extra, "swap_out_depois", ler_pswpout)
            if s == "pgvector":
                tentar(extra, "checkpointer_depois", stats_checkpointer)
            tentar(extra, "rss_fim_bytes", lambda: medir_rss_bytes(executar_docker, sistema=s))
            marco("C", "janela_fim", {"ordem": ordem, "taxa": taxa})
            return extra

        marco("C", "inicio")
        brutas = executar_janelas(
            est.buscador.buscar_uma,
            fabrica_inseridor=FabricaInseridor(s, est.nome, env),
            queries=queries,
            insercoes=pool,
            id_insercao_inicial=id0,
            cfg=cfg_c,
            ao_iniciar_janela=antes,
            ao_terminar_janela=depois,
        )
        m_final = brutas[-1].m_depois
        # Dado bruto primeiro: se o cálculo de recall falhar, as janelas
        # (60 s cada, irrepetíveis sem refazer o seed) não se perdem.
        destino = (
            cfg.marcos.parent if cfg.marcos else cfg.results_dir
        ) / f"c_brutas_{s}_{n}_{ts}.npz"
        destino.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            destino,
            **{
                f"j{b.ordem}_{campo}": getattr(b, campo)
                for b in brutas
                for campo in ("consultas", "ids_obtidos", "m_inicio", "m_fim", "latencias_ms")
            },
            **{
                f"j{b.ordem}_registros": np.asarray(
                    [(r.t_agendado, r.t_envio, r.t_confirmado, r.n) for r in b.registros],
                    dtype=np.float64,
                ).reshape(-1, 4)
                for b in brutas
            },
            janelas_json=np.asarray(
                json.dumps(
                    [
                        {
                            "ordem": b.ordem,
                            "taxa": b.taxa,
                            "inicio_medicao": b.inicio_medicao,
                            "fim_medicao": b.fim_medicao,
                            "inicio_utc": b.inicio_utc,
                            "fim_utc": b.fim_utc,
                            "m_antes": b.m_antes,
                            "m_depois": b.m_depois,
                            "extra": b.extra,
                        }
                        for b in brutas
                    ],
                    default=str,
                )
            ),
        )
        try:
            contagem: int | None = contar(s, est.recurso, est.nome)
        except Exception as e:  # noqa: BLE001
            contagem = None
            print(f"AVISO: contagem falhou: {e!r}", flush=True)
        marco("C", "fim", {"inseridos": m_final, "contagem": contagem})
        marco("C_recall", "inicio")
        try:
            gt: Any = GtIncremental(
                base=base,
                queries=queries,
                insercoes=pool[: max(m_final, 1)],
                k=cfg.k,
                id_insercao_inicial=id0,
            )
        except Exception as e:  # noqa: BLE001 — sem verdade exata, o resto ainda vale
            gt = None
            print(f"AVISO: verdade incremental falhou: {e!r}", flush=True)
        resultados = []
        for b in brutas:
            resultados.append(
                ResultadoBenchmark(
                    cenario="C",
                    sistema=s,
                    n=n,
                    timestamp_utc=ts,
                    parametros={
                        "taxa_alvo": b.taxa,
                        "ordem_janela": b.ordem,
                        "ef_search": cfg.ef_c,
                        "k": cfg.k,
                        "aquecimento_s": cfg.aquecimento_c_s,
                        "duracao_s": cfg.duracao_c_s,
                        "tick_s": cfg.tick_c_s,
                        "tamanho_lote": tamanho_lote(b.taxa, tick_s=cfg.tick_c_s),
                    },
                    metricas=_metricas_tolerantes(b, gt=gt, k=cfg.k, id0=id0),
                    ambiente={
                        **ambiente_base,
                        **est.extra_seed,
                        **b.extra,
                        "inicio_utc": b.inicio_utc,
                        "fim_utc": b.fim_utc,
                        "contagem_final": contagem,
                        "contagem_esperada": n + m_final,
                    },
                )
            )
        marco("C_recall", "fim")
        gravar(resultados, None)
        if contagem is not None and contagem != n + m_final:
            print(
                f"AVISO: contagem {contagem} != esperado {n + m_final} — inserção confirmada ausente.",
                flush=True,
            )

    for passo in ["reiniciar", *plano]:
        if passo in ("reiniciar", "limpar"):
            est.fechar()
            marco(passo, "inicio")
            dur = reiniciar_servico(s)
            marco(passo, "fim", {"duracao_s": dur})
        elif passo in ("seed_a", "seed_b", "seed_b_eq"):
            layout = {"seed_a": "A", "seed_b": "B", "seed_b_eq": "B_eq"}[passo]
            _, delta = medir_swap(passo, lambda layout=layout: semear(layout, layout == "B_eq"))
            est.extra_seed["swap_out_paginas_no_seed"] = delta
        elif passo == "A":
            passo_a()
        elif passo == "B":
            passo_b(False, "B")
        elif passo == "btree":
            info, _ = medir_swap("btree", passo_btree)
            est.extra_seed.update(info)
            est.recursos = _medir_recursos(
                s,
                recurso=est.recurso,
                nome_recurso=est.nome,
                tempo_carga_s=None,
                tempo_indice_utilizavel_s=None,
            )
        elif passo == "B_eq":
            passo_b(True, "B_eq")
        elif passo == "drop_btree":
            with est.recurso.cursor() as cur:
                cur.execute(f"DROP INDEX {est.nome}_seletor_idx")
            est.recurso.commit()
            # O C roda sem o B-tree; o ambiente não pode dizer o contrário.
            est.extra_seed.pop("btree_seletor_s", None)
            est.extra_seed["btree_seletor_removido"] = True
            marco("drop_btree", "fim")
        elif passo == "C":
            medir_swap("C_total", passo_c)
        else:  # pragma: no cover — plano_de_passos é a fonte
            raise ValueError(f"passo desconhecido: {passo}")

    est.fechar()
    marco("bloco", "fim", sonda_cpu())
    return escritos


def main(argv: Sequence[str] | None = None) -> int:
    import sys

    cfg = parse_args(sys.argv[1:] if argv is None else argv)
    escritos = executar(cfg)
    print(f"Sessão {cfg.sistema} N={cfg.n_base}: {len(escritos)} arquivo(s) gravado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
