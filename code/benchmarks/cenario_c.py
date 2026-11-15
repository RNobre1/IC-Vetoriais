"""Cenário C — carga mista RAG: buscas sob inserção concorrente.

Mede o que acontece com a *leitura* de um índice vetorial enquanto documentos
novos chegam, situação de um pipeline RAG em operação e que o ANN-Benchmarks
não cobre (lá o índice é estático). Decisões em
[[../../vault/decisões/2026-04-28-cenarios-A-B-C]] e
[[../../vault/decisões/2026-11-15-desenho-do-cenario-c]].

Desenho:

- A coleção do Cenário A (base de N vetores, já indexada) recebe uma sequência
  de janelas com taxa alvo de inserção — por padrão 0, 10, 100, 1000 e de novo
  0 inserções/s. A última janela, sem escrita, separa o efeito da escrita
  concorrente do efeito do crescimento da coleção.
- O produtor roda em **outro processo**: no mesmo processo, o GIL faria o
  trabalho do produtor aparecer como latência do consumidor. Envia lotes a
  cada `tick_s` (tamanho = taxa · tick) numa agenda fixa; se o servidor não
  acompanha, o atraso é registrado, nunca compensado com lotes maiores.
- O consumidor é único e sequencial, como nos Cenários A e B, com `ef_search`
  fixo, e cicla as consultas held-out.
- O recall de cada consulta é medido contra a busca exata sobre a base mais os
  vetores cuja inserção já tinha sido confirmada (`GtIncremental`). Vetor
  confirmado durante a própria consulta não pune o sistema: conta o melhor dos
  dois extremos (`recall_janela`).

As partes puras deste módulo têm testes unitários; `executar_janelas`, que
liga processos e SGBDs reais, é exercitada pelo ensaio da sessão de medição.
"""

from __future__ import annotations

import math
import multiprocessing as mp
import queue
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from lib.metrics import latencia_percentis, qps

TAXAS_INSERCAO_PADRAO = [0, 10, 100, 1000]  # inserções por segundo
# Duas janelas finais sem escrita: a 5ª logo após a escrita, a 6ª depois de o
# sistema assentar (otimizadores e filas de indexação concluídos).
SEQUENCIA_JANELAS_PADRAO = [*TAXAS_INSERCAO_PADRAO, 0, 0]
TICK_PADRAO_S = 0.1


@dataclass(frozen=True, slots=True)
class ConfigC:
    """Configuração do Cenário C."""

    n_base: int = 1_000_000
    n_queries: int = 1_000
    k: int = 10
    ef_search: int = 64
    janelas: list[int] = field(default_factory=lambda: list(SEQUENCIA_JANELAS_PADRAO))
    aquecimento_s: float = 5.0
    duracao_s: float = 60.0
    tick_s: float = TICK_PADRAO_S
    n_insercoes_pool: int = 80_000
    assentar_antes_da_ultima: bool = True
    sonda_visibilidade_ultimos: int = 50


def intervalo_entre_insercoes(taxa_ins_por_s: float) -> float:
    """Segundos entre inserções consecutivas para uma `taxa` (ins/s).

    `taxa == 0` ⇒ leitura pura, intervalo `inf`. `taxa < 0` é inválida.
    """
    if taxa_ins_por_s < 0:
        raise ValueError(f"taxa inválida: {taxa_ins_por_s} (esperado >= 0).")
    if taxa_ins_por_s == 0:
        return math.inf
    return 1.0 / taxa_ins_por_s


def tamanho_lote(taxa: int, *, tick_s: float) -> int:
    """Vetores por lote para cumprir `taxa` ins/s enviando um lote por tick.

    Recusa taxas que não fecham lote inteiro: arredondar faria a taxa enviada
    divergir da taxa declarada no resultado.
    """
    if taxa < 0:
        raise ValueError(f"taxa inválida: {taxa} (esperado >= 0).")
    exato = taxa * tick_s
    lote = round(exato)
    if abs(exato - lote) > 1e-9:
        raise ValueError(f"taxa {taxa} com tick {tick_s} s não dá lote inteiro ({exato}).")
    return int(lote)


def vetores_necessarios(janelas: Sequence[int], *, aquecimento_s: float, duracao_s: float) -> int:
    """Vetores consumidos no pior caso: cada janela insere durante aquecimento e medição."""
    return int(sum(round(t * (aquecimento_s + duracao_s)) for t in janelas))


# ---------------------------------------------------------------------------
# Produtor
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegistroLote:
    """Um lote enviado: quando devia sair, quando saiu, quando foi confirmado."""

    t_agendado: float
    t_envio: float
    t_confirmado: float
    n: int


class _ContadorCompartilhado(Protocol):
    value: int


def produzir(
    inserir_lote: Callable[[list[int], np.ndarray], Any],
    *,
    vetores: np.ndarray,
    id_inicial: int,
    taxa: int,
    tick_s: float,
    contador: _ContadorCompartilhado,
    deve_parar: Callable[[], bool],
    relogio: Callable[[], float] = time.monotonic,
    dormir: Callable[[float], None] = time.sleep,
) -> list[RegistroLote]:
    """Envia lotes de `vetores` a `taxa` ins/s até `deve_parar()` ou o pool acabar.

    Agenda *open-loop*: o lote `i` é agendado em `t0 + i·tick_s`. Adiantado, o
    produtor dorme; atrasado, envia logo, com o mesmo tamanho de lote. Assim a
    taxa sustentada é medida, e não imposta. `contador.value` soma os vetores
    **confirmados** — é o que o consumidor lê para saber quais já existem.
    """
    lote = tamanho_lote(taxa, tick_s=tick_s)
    if lote == 0:
        return []
    registros: list[RegistroLote] = []
    t0 = relogio()
    i = 0
    offset = 0
    while not deve_parar():
        if offset + lote > vetores.shape[0]:
            break
        agendado = t0 + i * tick_s
        espera = agendado - relogio()
        if espera > 0:
            dormir(espera)
            if deve_parar():
                break
        ids = list(range(id_inicial + offset, id_inicial + offset + lote))
        envio = relogio()
        inserir_lote(ids, vetores[offset : offset + lote])
        confirmado = relogio()
        offset += lote
        contador.value = contador.value + lote
        registros.append(
            RegistroLote(t_agendado=agendado, t_envio=envio, t_confirmado=confirmado, n=lote)
        )
        i += 1
    return registros


# ---------------------------------------------------------------------------
# Verdade exata que cresce com as inserções
# ---------------------------------------------------------------------------


class GtIncremental:
    """Top-K exato de cada consulta sobre `base ∪ insercoes[:m]`, para qualquer `m`.

    O top-K da base é calculado uma vez (é o mesmo do Cenário A); os produtos
    internos com o pool de inserções também. Para um prefixo `m`, basta juntar
    o top-K da base com o top-K do prefixo — o top-K do conjunto está contido
    nessa união. Ids da base são `0..N-1`; os do pool começam em
    `id_insercao_inicial`.
    """

    def __init__(
        self,
        *,
        base: np.ndarray,
        queries: np.ndarray,
        insercoes: np.ndarray,
        k: int,
        id_insercao_inicial: int,
    ) -> None:
        from ground_truth.exact_search import top_k_exato

        self._k = k
        self._id0 = id_insercao_inicial
        self._base_scores, self._base_ids = top_k_exato(base, queries, k=k)
        # (consultas × pool): linha contígua por consulta.
        self._scores_ins = np.ascontiguousarray(
            queries.astype(np.float32) @ insercoes.astype(np.float32).T
        )
        self.m_max = insercoes.shape[0]

    @property
    def base_ids(self) -> np.ndarray:
        return self._base_ids

    def top_k(self, j: int, m: int) -> np.ndarray:
        """Ids do top-K exato da consulta `j` com os `m` primeiros inseridos."""
        if m < 0 or m > self.m_max:
            raise ValueError(f"m={m} fora de [0, {self.m_max}].")
        if m == 0:
            return self._base_ids[j]
        s = self._scores_ins[j, :m]
        kk = min(self._k, m)
        cand = np.argpartition(-s, kk - 1)[:kk] if m > kk else np.arange(m)
        scores = np.concatenate([self._base_scores[j], s[cand]])
        ids = np.concatenate([self._base_ids[j], cand.astype(np.int64) + self._id0])
        ordem = np.argsort(-scores, kind="stable")[: self._k]
        return ids[ordem]


class _Gt(Protocol):
    def top_k(self, j: int, m: int) -> np.ndarray: ...


def recall_janela(
    *,
    ids_obtidos: np.ndarray,
    consultas: np.ndarray,
    m_inicio: np.ndarray,
    m_fim: np.ndarray,
    gt: _Gt,
    k: int,
    id_insercao_inicial: int,
) -> dict[str, Any]:
    """Recall@K da janela como dois limites, mais o recall dos recém-inseridos.

    Cada resposta é comparada com a verdade exata no estado do início da
    consulta (`m_inicio`) e no do fim (`m_fim`). Um vetor confirmado enquanto a
    consulta estava em voo pode legitimamente aparecer ou não, e nenhum dos dois
    estados é "o" certo: por consulta tomam-se o pior e o melhor, e a janela
    reporta as duas médias (`recall_inferior`, `recall_superior`). Escolher só
    o melhor favoreceria o sistema mais lento, que passa mais tempo em voo.

    `recall_novos` é a fração dos vizinhos verdadeiros no início da consulta
    que são vetores inseridos e foram devolvidos: mede se o que já tinha sido
    confirmado é encontrável. `None` quando nenhum vizinho verdadeiro era novo;
    `n_gt_novos` publica o denominador, que é pequeno nas taxas baixas.
    """
    n = ids_obtidos.shape[0]
    if n == 0:
        raise ValueError("janela sem consultas — nada para medir.")
    soma_min = 0
    soma_max = 0
    gt_novos = 0
    acertos_novos = 0
    for i in range(n):
        obtidos = set(ids_obtidos[i, :k].tolist())
        j = int(consultas[i])
        verdade_ini = set(gt.top_k(j, int(m_inicio[i]))[:k].tolist())
        acertos_ini = len(obtidos & verdade_ini)
        if int(m_fim[i]) == int(m_inicio[i]):
            acertos_fim = acertos_ini
        else:
            acertos_fim = len(obtidos & set(gt.top_k(j, int(m_fim[i]))[:k].tolist()))
        soma_min += min(acertos_ini, acertos_fim)
        soma_max += max(acertos_ini, acertos_fim)
        novos = {x for x in verdade_ini if x >= id_insercao_inicial}
        gt_novos += len(novos)
        acertos_novos += len(novos & obtidos)
    return {
        "recall_inferior": soma_min / (n * k),
        "recall_superior": soma_max / (n * k),
        "n_gt_novos": gt_novos,
        "recall_novos": (acertos_novos / gt_novos) if gt_novos else None,
    }


def sondar_visibilidade(
    buscar: Callable[[np.ndarray, int], list[int]],
    *,
    vetores: np.ndarray,
    id_inicial: int,
    ultimos: int,
    k: int,
) -> dict[str, Any]:
    """Busca cada um dos `ultimos` vetores inseridos pelo próprio vetor.

    Roda logo depois de o produtor parar, fora da janela medida. Um vetor
    confirmado e já buscável volta entre os `k` primeiros da própria consulta;
    o que ainda está numa fila de indexação, não. `vetores` são os inseridos em
    ordem, com ids a partir de `id_inicial`.
    """
    total = vetores.shape[0]
    n = min(ultimos, total)
    if n == 0:
        return {"visibilidade_n": 0, "visibilidade_fracao": None}
    achados = 0
    for idx in range(total - n, total):
        if (id_inicial + idx) in buscar(vetores[idx], k):
            achados += 1
    return {"visibilidade_n": n, "visibilidade_fracao": achados / n}


# ---------------------------------------------------------------------------
# Resumos
# ---------------------------------------------------------------------------


def resumir_producao(
    registros: Sequence[RegistroLote], *, inicio_medicao: float, fim_medicao: float
) -> dict[str, Any]:
    """Taxa sustentada e custo das inserções dentro da janela medida.

    Conta os lotes **confirmados** em `[inicio_medicao, fim_medicao)`: é a taxa
    que o sistema absorveu de fato enquanto as buscas eram medidas.
    """
    dentro = [r for r in registros if inicio_medicao <= r.t_confirmado < fim_medicao]
    inseridos = sum(r.n for r in dentro)
    duracao = fim_medicao - inicio_medicao
    lat_ms = [(r.t_confirmado - r.t_envio) * 1000.0 for r in registros]
    p = latencia_percentis(lat_ms) if lat_ms else None
    return {
        "inseridos_na_medicao": inseridos,
        "inseridos_total": sum(r.n for r in registros),
        "taxa_sustentada": inseridos / duracao if duracao > 0 else 0.0,
        "lote_p50_ms": p["p50"] if p else None,
        "lote_p99_ms": p["p99"] if p else None,
        "atraso_max_s": max((r.t_envio - r.t_agendado for r in registros), default=0.0),
    }


def resumir_consultas(latencias_ms: np.ndarray) -> dict[str, float]:
    """p50/p95/p99 e QPS de cliente único, como nos Cenários A e B."""
    p = latencia_percentis(latencias_ms)
    return {
        **p,
        "qps": qps(
            num_queries=int(latencias_ms.size), tempo_total_s=float(latencias_ms.sum()) / 1000.0
        ),
        "n_consultas": int(latencias_ms.size),
    }


# ---------------------------------------------------------------------------
# Execução com processos e SGBDs reais
# ---------------------------------------------------------------------------


class Inseridor(Protocol):
    def __call__(self, ids: list[int], vetores: np.ndarray) -> Any: ...


def _processo_produtor(
    fabrica: Callable[[], tuple[Inseridor, Callable[[], None]]],
    vetores: np.ndarray,
    id_inicial: int,
    taxa: int,
    tick_s: float,
    contador: Any,
    pronto: Any,
    iniciar: Any,
    parar: Any,
    saida: Any,
) -> None:
    """Corpo do processo produtor: conecta, avisa, espera a largada e produz."""
    inserir, fechar = fabrica()
    try:
        pronto.set()
        iniciar.wait()
        registros = produzir(
            inserir,
            vetores=vetores,
            id_inicial=id_inicial,
            taxa=taxa,
            tick_s=tick_s,
            contador=contador,
            deve_parar=parar.is_set,
        )
        saida.put([(r.t_agendado, r.t_envio, r.t_confirmado, r.n) for r in registros])
    except BaseException as e:  # o processo pai precisa saber, não só o log
        saida.put(("erro", repr(e)))
        raise
    finally:
        fechar()


@dataclass
class JanelaBruta:
    """O que uma janela produz antes de virar métrica."""

    taxa: int
    ordem: int
    consultas: np.ndarray
    ids_obtidos: np.ndarray
    m_inicio: np.ndarray
    m_fim: np.ndarray
    latencias_ms: np.ndarray
    registros: list[RegistroLote]
    inicio_medicao: float
    fim_medicao: float
    inicio_utc: str
    fim_utc: str
    m_antes: int
    m_depois: int
    extra: dict[str, Any] = field(default_factory=dict)


def _gancho(
    fn: Callable[[int, int], dict[str, Any] | None] | None,
    ordem: int,
    taxa: int,
    extra: dict[str, Any],
    chave_erro: str,
) -> None:
    """Roda um gancho de telemetria sem deixar a falha dele derrubar a janela.

    Os ganchos medem coisas acessórias (memória do contêiner, estado do
    checkpointer). Perder uma janela de 60 s — e, no pgvector, o seed de 1M
    que a precede — por causa delas seria trocar o dado pelo instrumento.
    """
    if fn is None:
        return
    try:
        extra.update(fn(ordem, taxa) or {})
    except Exception as e:  # noqa: BLE001
        extra[chave_erro] = repr(e)[:300]


def _utc_agora() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def executar_janelas(
    buscar: Callable[[np.ndarray, int], list[int]],
    *,
    fabrica_inseridor: Callable[[], tuple[Inseridor, Callable[[], None]]],
    queries: np.ndarray,
    insercoes: np.ndarray,
    id_insercao_inicial: int,
    cfg: ConfigC,
    ao_iniciar_janela: Callable[[int, int], dict[str, Any] | None] | None = None,
    ao_terminar_janela: Callable[[int, int], dict[str, Any] | None] | None = None,
) -> list[JanelaBruta]:
    """Roda as janelas de `cfg.janelas` em sequência, sem pausa além dos ganchos.

    `buscar(query, k)` é a busca do adaptador já configurado com `ef_search`.
    `fabrica_inseridor` precisa ser *picklable* (roda no processo filho) e
    devolve `(inserir_lote, fechar)`. O recall é calculado depois, fora das
    janelas, para que o cálculo não abra um intervalo sem escrita entre elas.

    Os ganchos rodam fora da medição e o que devolvem vai para `extra` da
    janela: o executor da sessão os usa para assentar o sistema antes da
    última janela e para registrar o estado do *checkpointer* do PostgreSQL.
    Depois de cada janela com escrita, `sondar_visibilidade` busca os últimos
    vetores confirmados pelo próprio vetor.
    """
    necessarios = vetores_necessarios(
        cfg.janelas, aquecimento_s=cfg.aquecimento_s, duracao_s=cfg.duracao_s
    )
    if insercoes.shape[0] < necessarios:
        raise ValueError(
            f"pool de inserções insuficiente: {insercoes.shape[0]} < {necessarios} necessários."
        )
    ctx = mp.get_context("spawn")
    n_q = queries.shape[0]
    m_acumulado = 0
    brutas: list[JanelaBruta] = []

    for ordem, taxa in enumerate(cfg.janelas):
        extra: dict[str, Any] = {}
        _gancho(ao_iniciar_janela, ordem, taxa, extra, "erro_gancho_inicio")
        contador = ctx.Value("q", 0)
        proc = None
        saida = ctx.Queue()
        parar = ctx.Event()
        if taxa > 0:
            pronto, iniciar = ctx.Event(), ctx.Event()
            proc = ctx.Process(
                target=_processo_produtor,
                args=(
                    fabrica_inseridor,
                    insercoes[m_acumulado:],
                    id_insercao_inicial + m_acumulado,
                    taxa,
                    cfg.tick_s,
                    contador,
                    pronto,
                    iniciar,
                    parar,
                    saida,
                ),
                daemon=True,
            )
            proc.start()
            if not pronto.wait(timeout=120):
                proc.terminate()
                raise RuntimeError(f"produtor da janela {ordem} não conectou em 120 s.")
            iniciar.set()

        t0 = time.monotonic()
        inicio_medicao = t0 + cfg.aquecimento_s
        fim_medicao = inicio_medicao + cfg.duracao_s
        j = 0
        while time.monotonic() < inicio_medicao:
            buscar(queries[j % n_q], cfg.k)
            j += 1

        inicio_utc = _utc_agora()
        consultas: list[int] = []
        m_ini: list[int] = []
        m_fim: list[int] = []
        lat: list[float] = []
        ids_l: list[list[int]] = []
        j = 0
        while time.monotonic() < fim_medicao:
            q = j % n_q
            mi = m_acumulado + contador.value
            t_a = time.perf_counter()
            ids = buscar(queries[q], cfg.k)
            lat.append((time.perf_counter() - t_a) * 1000.0)
            mf = m_acumulado + contador.value
            consultas.append(q)
            m_ini.append(mi)
            m_fim.append(mf)
            ids_l.append(list(ids)[: cfg.k] + [-1] * (cfg.k - len(ids)))
            j += 1
        fim_utc = _utc_agora()

        registros: list[RegistroLote] = []
        if proc is not None:
            parar.set()
            try:
                dados = saida.get(timeout=300)
            except queue.Empty as e:
                raise RuntimeError(
                    f"produtor da janela {ordem} terminou sem resultado "
                    f"(exitcode={proc.exitcode})."
                ) from e
            proc.join(timeout=120)
            if isinstance(dados, tuple) and dados and dados[0] == "erro":
                raise RuntimeError(f"produtor da janela {ordem} falhou: {dados[1]}")
            registros = [RegistroLote(*t) for t in dados]

        m_depois = m_acumulado + contador.value
        if m_depois > m_acumulado:
            try:
                extra.update(
                    sondar_visibilidade(
                        buscar,
                        vetores=insercoes[m_acumulado:m_depois],
                        id_inicial=id_insercao_inicial + m_acumulado,
                        ultimos=cfg.sonda_visibilidade_ultimos,
                        k=cfg.k,
                    )
                )
            except Exception as e:  # noqa: BLE001 — sonda acessória
                extra["erro_visibilidade"] = repr(e)[:300]
        _gancho(ao_terminar_janela, ordem, taxa, extra, "erro_gancho_fim")
        brutas.append(
            JanelaBruta(
                taxa=taxa,
                ordem=ordem,
                consultas=np.asarray(consultas, dtype=np.int64),
                ids_obtidos=np.asarray(ids_l, dtype=np.int64),
                m_inicio=np.asarray(m_ini, dtype=np.int64),
                m_fim=np.asarray(m_fim, dtype=np.int64),
                latencias_ms=np.asarray(lat, dtype=np.float64),
                registros=registros,
                inicio_medicao=inicio_medicao,
                fim_medicao=fim_medicao,
                inicio_utc=inicio_utc,
                fim_utc=fim_utc,
                m_antes=m_acumulado,
                m_depois=m_depois,
                extra=extra,
            )
        )
        m_acumulado = m_depois

    return brutas


def metricas_da_janela(
    bruta: JanelaBruta, *, gt: _Gt, k: int, id_insercao_inicial: int
) -> dict[str, Any]:
    """Converte uma `JanelaBruta` nas métricas que vão para o JSON."""
    return {
        **resumir_consultas(bruta.latencias_ms),
        **recall_janela(
            ids_obtidos=bruta.ids_obtidos,
            consultas=bruta.consultas,
            m_inicio=bruta.m_inicio,
            m_fim=bruta.m_fim,
            gt=gt,
            k=k,
            id_insercao_inicial=id_insercao_inicial,
        ),
        **resumir_producao(
            bruta.registros, inicio_medicao=bruta.inicio_medicao, fim_medicao=bruta.fim_medicao
        ),
        "inseridos_acumulados_antes": bruta.m_antes,
        "inseridos_acumulados_depois": bruta.m_depois,
    }
