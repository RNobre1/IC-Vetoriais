"""Testes de `benchmarks.cenario_a` (TDD — escritos antes da implementação).

`cenario_a` orquestra a busca pura. Para ser testável sem Docker, a lógica
de medição opera sobre o Protocol `BuscadorVetorial` (um adaptador por SGBD,
testados em integração à parte). Aqui injetamos um `FakeBuscador`
determinístico e verificamos:

- um `ResultadoBenchmark` por valor de `efSearch`;
- `configurar_ef_search` chamado com cada valor, na ordem;
- warmup descartado (não entra nas métricas);
- recall@K calculado contra o ground truth;
- bloco de parâmetros/métricas/ambiente preenchido conforme a ADR
  [[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]].
"""

from __future__ import annotations

import numpy as np
import pytest

from benchmarks.cenario_a import medir_sistema
from lib.reporting import ResultadoBenchmark

# ---------------------------------------------------------------------------
# Fake
# ---------------------------------------------------------------------------


class FakeBuscador:
    """Buscador determinístico.

    `perfeito=True`: devolve exatamente os `k` ids do ground truth da query
    correspondente (recall = 1.0). `perfeito=False`: devolve ids deslocados
    (recall = 0.0). Conta chamadas para validar warmup.
    """

    def __init__(self, gt_ids: np.ndarray, *, nome: str = "fake", perfeito: bool = True) -> None:
        self.nome = nome
        self._gt = gt_ids
        self._perfeito = perfeito
        self.efs_configurados: list[int] = []
        self.chamadas_busca = 0
        self._idx = 0

    def configurar_ef_search(self, ef: int) -> None:
        self.efs_configurados.append(ef)
        self._idx = 0  # reinicia o ponteiro de query a cada ef

    def buscar_uma(self, query: np.ndarray, k: int) -> list[int]:
        del query
        self.chamadas_busca += 1
        linha = self._gt[self._idx % len(self._gt)]
        self._idx += 1
        if self._perfeito:
            return list(linha[:k])
        return list(linha[:k] + 100_000)  # nenhum id em comum → recall 0


@pytest.fixture
def queries() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.standard_normal((20, 8)).astype(np.float32)


@pytest.fixture
def gt_ids() -> np.ndarray:
    """Ground truth realista: 10 ids DISTINTOS por linha (sem reposição).

    `top_k_exato` nunca repete id numa linha; usar `rng.integers` geraria
    duplicatas e `recall_at_k` (baseado em conjuntos) nunca chegaria a 1.0.
    """
    rng = np.random.default_rng(7)
    linhas = [rng.choice(1000, size=10, replace=False) for _ in range(20)]
    return np.array(linhas, dtype=np.int64)


# ---------------------------------------------------------------------------
# Estrutura da saída
# ---------------------------------------------------------------------------


def test_um_resultado_por_ef_search(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    resultados = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[16, 32, 64],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
    )
    assert len(resultados) == 3
    assert all(isinstance(r, ResultadoBenchmark) for r in resultados)
    assert [r.parametros["ef_search"] for r in resultados] == [16, 32, 64]


def test_configura_ef_em_ordem(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[16, 64, 256],
        k=5,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
    )
    assert buscador.efs_configurados == [16, 64, 256]


def test_campos_fixos_do_resultado(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids, nome="pgvector")
    r = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[32],
        k=10,
        n_base=12345,
        timestamp_utc="2026-05-10T12-00-00Z",
    )[0]
    assert r.cenario == "A"
    assert r.sistema == "pgvector"
    assert r.n == 12345
    assert r.timestamp_utc == "2026-05-10T12-00-00Z"
    assert r.parametros["k"] == 10
    assert r.parametros["ef_search"] == 32
    assert "warmup" in r.parametros
    assert set(r.metricas) >= {"p50", "p95", "p99", "qps", "recall_at_k"}


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------


def test_warmup_e_descartado_das_metricas(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    warmup = 5
    medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[16],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=warmup,
    )
    # 1 ef × (warmup + len(queries)) buscas
    assert buscador.chamadas_busca == warmup + len(queries)


def test_warmup_zero_ok(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[16],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=0,
    )
    assert buscador.chamadas_busca == len(queries)


# ---------------------------------------------------------------------------
# Recall
# ---------------------------------------------------------------------------


def test_recall_1_quando_buscador_perfeito(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids, perfeito=True)
    r = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[64],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=0,
    )[0]
    assert r.metricas["recall_at_k"] == pytest.approx(1.0)


def test_recall_0_quando_buscador_erra_tudo(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids, perfeito=False)
    r = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[64],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=0,
    )[0]
    assert r.metricas["recall_at_k"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Métricas têm tipos serializáveis e valores plausíveis
# ---------------------------------------------------------------------------


def test_metricas_sao_float_plausiveis(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    r = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[32],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
    )[0]
    for chave in ("p50", "p95", "p99", "qps", "recall_at_k"):
        assert isinstance(r.metricas[chave], float)
    assert r.metricas["p99"] >= r.metricas["p50"] >= 0.0
    assert r.metricas["qps"] > 0.0


# ---------------------------------------------------------------------------
# Validações de borda
# ---------------------------------------------------------------------------


def test_levanta_se_queries_vazias(gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    with pytest.raises(ValueError, match="quer"):
        medir_sistema(
            buscador,
            queries=np.zeros((0, 8), dtype=np.float32),
            gt_ids=gt_ids,
            ef_search_values=[16],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-10T00-00-00Z",
        )


def test_levanta_se_ef_search_values_vazio(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    with pytest.raises(ValueError, match="ef_search"):
        medir_sistema(
            buscador,
            queries=queries,
            gt_ids=gt_ids,
            ef_search_values=[],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-10T00-00-00Z",
        )


def test_levanta_se_warmup_negativo(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    with pytest.raises(ValueError, match="warmup"):
        medir_sistema(
            buscador,
            queries=queries,
            gt_ids=gt_ids,
            ef_search_values=[16],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-10T00-00-00Z",
            warmup=-1,
        )


def test_levanta_se_num_queries_difere_do_gt(queries: np.ndarray) -> None:
    gt_curto = np.zeros((5, 10), dtype=np.int64)  # 5 != 20 queries
    buscador = FakeBuscador(gt_curto)
    with pytest.raises(ValueError, match="quer"):
        medir_sistema(
            buscador,
            queries=queries,
            gt_ids=gt_curto,
            ef_search_values=[16],
            k=10,
            n_base=100,
            timestamp_utc="2026-05-10T00-00-00Z",
        )


# ---------------------------------------------------------------------------
# Repetições (Contrato Atualizado T1)
# ---------------------------------------------------------------------------


def test_repeticoes_rejeita_menor_que_um(queries: np.ndarray, gt_ids: np.ndarray) -> None:
    buscador = FakeBuscador(gt_ids)
    for r_invalido in (0, -1, -5):
        with pytest.raises(ValueError, match="repeticoes"):
            medir_sistema(
                buscador,
                queries=queries,
                gt_ids=gt_ids,
                ef_search_values=[16],
                k=10,
                n_base=100,
                timestamp_utc="2026-05-10T00-00-00Z",
                repeticoes=r_invalido,
            )


def test_repeticoes_padrao_um_preserva_contrato_existente(
    queries: np.ndarray, gt_ids: np.ndarray
) -> None:
    buscador = FakeBuscador(gt_ids)
    res = medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=[16],
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        repeticoes=1,
    )[0]
    # Com repeticoes == 1, chaves devem ser estritamente idênticas às originais
    assert set(res.parametros) == {"ef_search", "k", "warmup"}
    assert set(res.metricas) == {"p50", "p95", "p99", "qps", "recall_at_k"}
    assert "repeticoes" not in res.parametros
    assert "repeticoes" not in res.metricas
    assert "p50_agrupado" not in res.metricas


def test_repeticoes_ordem_varredura_zig_zag_e_aquecimento_por_bloco(
    queries: np.ndarray, gt_ids: np.ndarray
) -> None:
    # Registra a sequência exata de chamadas a configurar_ef_search
    buscador = FakeBuscador(gt_ids)
    warmup = 3
    r = 3
    efs = [16, 32, 64]
    medir_sistema(
        buscador,
        queries=queries,
        gt_ids=gt_ids,
        ef_search_values=efs,
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=warmup,
        repeticoes=r,
    )
    # Repetições:
    # rep 0 (par): 16, 32, 64
    # rep 1 (ímpar): 64, 32, 16
    # rep 2 (par): 16, 32, 64
    esperado_efs = [16, 32, 64, 64, 32, 16, 16, 32, 64]
    assert buscador.efs_configurados == esperado_efs

    # Para cada bloco (R * len(efs) = 3 * 3 = 9 blocos):
    # cada bloco executa warmup (3) + queries (len(queries) = 20) = 23 buscas
    assert buscador.chamadas_busca == 9 * (warmup + len(queries))


def test_repeticoes_multiplas_calcula_medianas_agrupados_e_posicoes(
    queries: np.ndarray, gt_ids: np.ndarray
) -> None:
    sub_queries = queries[:2]  # 2 queries
    sub_gt = gt_ids[:2]
    efs = [16, 32]

    class BuscadorControlado:
        nome = "fake_rep"

        def __init__(self) -> None:
            self.ef_atual = 16
            self.historico_ef: list[int] = []
            self.total_buscas = 0

        def configurar_ef_search(self, ef: int) -> None:
            self.ef_atual = ef
            self.historico_ef.append(ef)

        def buscar_uma(self, query: np.ndarray, k: int) -> list[int]:
            del query
            self.total_buscas += 1
            # Na primeira repetição (onde self.ef_atual foi configurado na 1ª vez), retorna perfeito
            # Nas seguintes, retorna errado, para validar que recall_at_k vem da 1ª repetição.
            if len(self.historico_ef) <= 2:
                idx = (self.total_buscas - 1) % len(sub_gt)
                return list(sub_gt[idx][:k])
            return list(sub_gt[0][:k] + 999_999)

    buscador = BuscadorControlado()

    # R = 2 repetições, 2 efs -> 4 blocos.
    # Bloco 0: rep 0, ef 16 (pos 0) -> 2 queries
    # Bloco 1: rep 0, ef 32 (pos 1) -> 2 queries
    # Bloco 2: rep 1, ef 32 (pos 0) -> 2 queries (ordem reversa!)
    # Bloco 3: rep 1, ef 16 (pos 1) -> 2 queries
    # Cada query precisa de 2 timestamps (t0, t1)
    # Total de chamadas de relógio = 4 blocos * 2 queries * 2 = 16 timestamps

    # Latências desejadas para ef=16:
    # rep 0: 10ms, 10ms -> p50=10, p95=10, p99=10, tempo_total = 0.02s -> qps = 2/0.02 = 100
    # rep 1: 30ms, 30ms -> p50=30, p95=30, p99=30, tempo_total = 0.06s -> qps = 2/0.06 = 33.333
    # Mediana ef 16: p50=20, p95=20, p99=20, qps=median(100, 33.333)=66.666
    # Agrupado ef 16 (10, 10, 30, 30): p50=20, etc.

    # Latências desejadas para ef=32:
    # rep 0: 20ms, 20ms
    # rep 1: 40ms, 40ms

    # Timestamps (s):
    # Bloco 0 (rep 0, ef 16):
    #   q0: 0.000 -> 0.010 (10ms)
    #   q1: 0.010 -> 0.020 (10ms)
    # Bloco 1 (rep 0, ef 32):
    #   q0: 0.020 -> 0.040 (20ms)
    #   q1: 0.040 -> 0.060 (20ms)
    # Bloco 2 (rep 1, ef 32): [reverso: ef 32 vem primeiro!]
    #   q0: 0.060 -> 0.100 (40ms)
    #   q1: 0.100 -> 0.140 (40ms)
    # Bloco 3 (rep 1, ef 16):
    #   q0: 0.140 -> 0.170 (30ms)
    #   q1: 0.170 -> 0.200 (30ms)

    tempos = [
        0.000,
        0.010,
        0.010,
        0.020,  # Bloco 0 (ef 16)
        0.020,
        0.040,
        0.040,
        0.060,  # Bloco 1 (ef 32)
        0.060,
        0.100,
        0.100,
        0.140,  # Bloco 2 (ef 32)
        0.140,
        0.170,
        0.170,
        0.200,  # Bloco 3 (ef 16)
    ]
    ponteiro = [0]

    def relogio_fake() -> float:
        t = tempos[ponteiro[0]]
        ponteiro[0] += 1
        return t

    resultados = medir_sistema(
        buscador,
        queries=sub_queries,
        gt_ids=sub_gt,
        ef_search_values=efs,
        k=10,
        n_base=100,
        timestamp_utc="2026-05-10T00-00-00Z",
        warmup=0,
        repeticoes=2,
        relogio=relogio_fake,
    )

    # Resultados devem estar na ordem original de ef_search_values: [16, 32]
    assert len(resultados) == 2
    res_16 = resultados[0]
    res_32 = resultados[1]
    assert res_16.parametros["ef_search"] == 16
    assert res_32.parametros["ef_search"] == 32

    # Verifica ef 16
    assert res_16.parametros["repeticoes"] == 2
    assert res_16.metricas["recall_at_k"] == pytest.approx(1.0)  # da 1ª repetição
    assert res_16.metricas["p50"] == pytest.approx(20.0)
    assert res_16.metricas["p95"] == pytest.approx(20.0)
    assert res_16.metricas["p99"] == pytest.approx(20.0)
    assert res_16.metricas["qps"] == pytest.approx((100.0 + (2.0 / 0.06)) / 2.0)
    assert res_16.metricas["p50_agrupado"] == pytest.approx(20.0)

    # Repetições de ef 16:
    reps_16 = res_16.metricas["repeticoes"]
    assert len(reps_16) == 2
    assert reps_16[0]["posicao"] == 0  # no rep 0, ef 16 foi testado na posição 0
    assert reps_16[0]["recall_at_k"] == pytest.approx(1.0)
    assert reps_16[1]["posicao"] == 1  # no rep 1 (reverso), ef 16 foi testado na posição 1
    assert reps_16[1]["recall_at_k"] == pytest.approx(0.0)

    # Repetições de ef 32:
    reps_32 = res_32.metricas["repeticoes"]
    assert len(reps_32) == 2
    assert reps_32[0]["posicao"] == 1  # no rep 0, ef 32 foi testado na posição 1
    assert reps_32[1]["posicao"] == 0  # no rep 1 (reverso), ef 32 foi testado na posição 0
