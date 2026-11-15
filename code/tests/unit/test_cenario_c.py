"""Testes da lógica pura de `benchmarks.cenario_c` (TDD).

Cenário C (carga mista RAG): um produtor insere vetores a uma taxa alvo
enquanto um consumidor faz buscas. Aqui ficam as partes que não dependem de
Docker: escalonamento do produtor, verdade exata que cresce com as inserções,
recall sob escrita e os resumos de cada janela. A orquestração com processos
e SGBDs reais é exercitada pelo ensaio da sessão de medição.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from benchmarks.cenario_c import (
    SEQUENCIA_JANELAS_PADRAO,
    TAXAS_INSERCAO_PADRAO,
    ConfigC,
    GtIncremental,
    RegistroLote,
    intervalo_entre_insercoes,
    produzir,
    recall_janela,
    resumir_producao,
    sondar_visibilidade,
    tamanho_lote,
    vetores_necessarios,
)

# ---------------------------------------------------------------------------
# Escalonamento de inserções
# ---------------------------------------------------------------------------


def test_taxa_zero_significa_sem_insercoes() -> None:
    assert intervalo_entre_insercoes(0) == math.inf


def test_intervalo_e_inverso_da_taxa() -> None:
    assert intervalo_entre_insercoes(10) == pytest.approx(0.1)
    assert intervalo_entre_insercoes(1000) == pytest.approx(0.001)


def test_taxa_negativa_invalida() -> None:
    with pytest.raises(ValueError, match="taxa"):
        intervalo_entre_insercoes(-1)


def test_tamanho_lote_e_taxa_vezes_tick() -> None:
    assert tamanho_lote(10, tick_s=0.1) == 1
    assert tamanho_lote(100, tick_s=0.1) == 10
    assert tamanho_lote(1000, tick_s=0.1) == 100
    assert tamanho_lote(0, tick_s=0.1) == 0


def test_tamanho_lote_recusa_taxa_que_nao_fecha_lote_inteiro() -> None:
    # 15 ins/s com tick de 100 ms daria 1,5 vetor por lote: a taxa alvo não
    # seria a taxa enviada. Melhor recusar que arredondar em silêncio.
    with pytest.raises(ValueError, match="inteiro"):
        tamanho_lote(15, tick_s=0.1)


def test_vetores_necessarios_cobre_aquecimento_e_medicao() -> None:
    # 1000 ins/s por 5 s + 60 s = 65.000; 10 e 100 somam 650 e 6.500.
    total = vetores_necessarios([0, 10, 100, 1000, 0], aquecimento_s=5, duracao_s=60)
    assert total == 650 + 6_500 + 65_000


def test_config_defaults() -> None:
    cfg = ConfigC()
    assert TAXAS_INSERCAO_PADRAO == [0, 10, 100, 1000]
    # As duas janelas finais sem escrita separam o efeito da escrita
    # concorrente do efeito do crescimento: a 5ª logo após a escrita, a 6ª
    # depois de o sistema assentar (otimizadores e filas concluídos).
    assert cfg.janelas == list(SEQUENCIA_JANELAS_PADRAO) == [0, 10, 100, 1000, 0, 0]
    assert cfg.assentar_antes_da_ultima is True
    assert cfg.k == 10
    assert cfg.ef_search == 64
    assert cfg.n_base == 1_000_000
    assert cfg.n_insercoes_pool >= vetores_necessarios(
        cfg.janelas, aquecimento_s=cfg.aquecimento_s, duracao_s=cfg.duracao_s
    )


# ---------------------------------------------------------------------------
# Produtor (relógio falso)
# ---------------------------------------------------------------------------


class _Relogio:
    """Relógio monotônico controlado: `dormir` avança o tempo sem esperar."""

    def __init__(self) -> None:
        self.t = 100.0

    def agora(self) -> float:
        return self.t

    def dormir(self, s: float) -> None:
        self.t += max(0.0, s)


class _Contador:
    def __init__(self) -> None:
        self.value = 0


def test_produtor_envia_lotes_na_cadencia_e_conta_confirmados() -> None:
    rel = _Relogio()
    enviados: list[list[int]] = []

    def inserir(ids: list[int], vetores: np.ndarray) -> None:
        assert len(ids) == vetores.shape[0]
        enviados.append(list(ids))
        rel.t += 0.01  # cada lote leva 10 ms

    vet = np.zeros((50, 4), dtype=np.float32)
    contador = _Contador()
    # Para depois de 5 lotes.
    registros = produzir(
        inserir,
        vetores=vet,
        id_inicial=1000,
        taxa=100,
        tick_s=0.1,
        contador=contador,
        deve_parar=lambda: len(enviados) >= 5,
        relogio=rel.agora,
        dormir=rel.dormir,
    )
    assert enviados[0] == list(range(1000, 1010))
    assert enviados[1] == list(range(1010, 1020))
    assert contador.value == 50
    assert len(registros) == 5
    # Agenda open-loop: lote i agendado em t0 + i·tick.
    t0 = registros[0].t_agendado
    assert [r.t_agendado - t0 for r in registros] == pytest.approx([0.0, 0.1, 0.2, 0.3, 0.4])
    assert all(r.n == 10 for r in registros)
    assert all(r.t_confirmado - r.t_envio == pytest.approx(0.01) for r in registros)


def test_produtor_atrasado_nao_compensa_com_lote_maior() -> None:
    rel = _Relogio()
    tamanhos: list[int] = []

    def inserir(ids: list[int], vetores: np.ndarray) -> None:
        tamanhos.append(len(ids))
        rel.t += 0.25  # mais lento que o tick: o produtor fica para trás

    registros = produzir(
        inserir,
        vetores=np.zeros((100, 4), dtype=np.float32),
        id_inicial=0,
        taxa=100,
        tick_s=0.1,
        contador=_Contador(),
        deve_parar=lambda: len(tamanhos) >= 4,
        relogio=rel.agora,
        dormir=rel.dormir,
    )
    assert tamanhos == [10, 10, 10, 10]
    # O atraso fica registrado em vez de escondido.
    assert registros[-1].t_envio - registros[-1].t_agendado > 0.4


def test_produtor_para_quando_o_pool_acaba() -> None:
    rel = _Relogio()

    def inserir(ids: list[int], vetores: np.ndarray) -> None:
        rel.t += 0.001

    contador = _Contador()
    registros = produzir(
        inserir,
        vetores=np.zeros((25, 4), dtype=np.float32),
        id_inicial=0,
        taxa=100,
        tick_s=0.1,
        contador=contador,
        deve_parar=lambda: False,
        relogio=rel.agora,
        dormir=rel.dormir,
    )
    # Dois lotes de 10 cabem; o terceiro não é enviado pela metade.
    assert [r.n for r in registros] == [10, 10]
    assert contador.value == 20


# ---------------------------------------------------------------------------
# Verdade exata que cresce com as inserções
# ---------------------------------------------------------------------------


def _unitarios(n: int, d: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(n, d)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def _gt_bruto(base, ins, m, q, k, n_base_id, id_ins0):
    todos = np.vstack([base, ins[:m]]) if m else base
    ids = np.concatenate([np.arange(base.shape[0]) + n_base_id, np.arange(m) + id_ins0])
    s = todos @ q
    return set(ids[np.argsort(-s)[:k]].tolist())


def test_gt_incremental_igual_a_forca_bruta_em_todo_prefixo() -> None:
    base = _unitarios(300, 8, 1)
    ins = _unitarios(120, 8, 2)
    queries = _unitarios(6, 8, 3)
    k = 5
    gt = GtIncremental(base=base, queries=queries, insercoes=ins, k=k, id_insercao_inicial=1_000)
    for j in range(queries.shape[0]):
        for m in (0, 1, 7, 60, 120):
            esperado = _gt_bruto(base, ins, m, queries[j], k, 0, 1_000)
            assert set(gt.top_k(j, m).tolist()) == esperado


def test_gt_incremental_recusa_prefixo_alem_do_pool() -> None:
    gt = GtIncremental(
        base=_unitarios(20, 4, 1),
        queries=_unitarios(2, 4, 2),
        insercoes=_unitarios(5, 4, 3),
        k=3,
        id_insercao_inicial=100,
    )
    with pytest.raises(ValueError, match="m"):
        gt.top_k(0, 6)


# ---------------------------------------------------------------------------
# Recall sob escrita
# ---------------------------------------------------------------------------


class _GtFixo:
    """Verdade exata tabelada por (consulta, m) para testar a contagem."""

    def __init__(self, tabela: dict[tuple[int, int], list[int]]) -> None:
        self._t = tabela

    def top_k(self, j: int, m: int) -> np.ndarray:
        return np.array(self._t[(j, m)])


def test_recall_janela_sem_insercao_em_voo_tem_limites_iguais() -> None:
    gt = _GtFixo({(0, 0): [1, 2], (0, 5): [1, 2]})
    r = recall_janela(
        ids_obtidos=np.array([[1, 9]]),
        consultas=np.array([0]),
        m_inicio=np.array([0]),
        m_fim=np.array([5]),
        gt=gt,
        k=2,
        id_insercao_inicial=1000,
    )
    assert r["recall_inferior"] == pytest.approx(0.5)
    assert r["recall_superior"] == pytest.approx(0.5)
    assert r["n_gt_novos"] == 0
    assert r["recall_novos"] is None


def test_recall_janela_reporta_os_dois_extremos_quando_ha_vetor_em_voo() -> None:
    # 1003 foi confirmado enquanto a consulta estava em voo. Contra a verdade
    # do início a resposta acerta 1 de 2; contra a do fim, 2 de 2. Nenhum dos
    # dois é "o" recall: os dois são reportados como limites.
    gt = _GtFixo({(0, 3): [1, 2], (0, 4): [1003, 1]})
    r = recall_janela(
        ids_obtidos=np.array([[1003, 1]]),
        consultas=np.array([0]),
        m_inicio=np.array([3]),
        m_fim=np.array([4]),
        gt=gt,
        k=2,
        id_insercao_inicial=1000,
    )
    assert r["recall_inferior"] == pytest.approx(0.5)
    assert r["recall_superior"] == pytest.approx(1.0)
    # Recall dos novos só conta vetores já confirmados quando a consulta saiu.
    assert r["n_gt_novos"] == 0


def test_recall_novos_mede_se_os_inseridos_aparecem() -> None:
    gt = _GtFixo({(0, 9): [1001, 1002, 7], (1, 9): [1005, 3, 4]})
    r = recall_janela(
        ids_obtidos=np.array([[1001, 7, 8], [3, 4, 5]]),
        consultas=np.array([0, 1]),
        m_inicio=np.array([9, 9]),
        m_fim=np.array([9, 9]),
        gt=gt,
        k=3,
        id_insercao_inicial=1000,
    )
    # Novos na verdade: 1001, 1002, 1005; devolvido só 1001.
    assert r["n_gt_novos"] == 3
    assert r["recall_novos"] == pytest.approx(1 / 3)
    assert r["recall_inferior"] == pytest.approx((2 / 3 + 2 / 3) / 2)


# ---------------------------------------------------------------------------
# Sonda de visibilidade
# ---------------------------------------------------------------------------


def test_sondar_visibilidade_busca_cada_inserido_pelo_proprio_vetor() -> None:
    vet = np.eye(6, dtype=np.float32)
    visiveis = {104, 105}

    def buscar(q: np.ndarray, k: int) -> list[int]:
        i = int(np.argmax(q)) + 100
        return [i, 1, 2] if i in visiveis else [1, 2, 3]

    r = sondar_visibilidade(buscar, vetores=vet, id_inicial=100, ultimos=4, k=3)
    # Os 4 últimos são 102..105; só 104 e 105 aparecem.
    assert r == {"visibilidade_n": 4, "visibilidade_fracao": pytest.approx(0.5)}


def test_sondar_visibilidade_sem_insercoes() -> None:
    r = sondar_visibilidade(
        lambda q, k: [], vetores=np.zeros((0, 3), dtype=np.float32), id_inicial=0, ultimos=50, k=10
    )
    assert r == {"visibilidade_n": 0, "visibilidade_fracao": None}


# ---------------------------------------------------------------------------
# Resumo do produtor
# ---------------------------------------------------------------------------


def test_resumir_producao_mede_taxa_sustentada_na_janela_medida() -> None:
    regs = [
        RegistroLote(t_agendado=t, t_envio=t + 0.02, t_confirmado=t + 0.05, n=10)
        for t in np.arange(0.0, 10.0, 0.1)
    ]
    r = resumir_producao(regs, inicio_medicao=2.0, fim_medicao=8.0)
    # Lotes confirmados dentro de [2, 8): 60 lotes de 10.
    assert r["inseridos_na_medicao"] == 600
    assert r["taxa_sustentada"] == pytest.approx(100.0)
    assert r["lote_p50_ms"] == pytest.approx(30.0)
    assert r["atraso_max_s"] == pytest.approx(0.02)
    assert r["inseridos_total"] == 1000


def test_resumir_producao_sem_lotes() -> None:
    r = resumir_producao([], inicio_medicao=0.0, fim_medicao=60.0)
    assert r["inseridos_na_medicao"] == 0
    assert r["taxa_sustentada"] == 0.0
    assert r["lote_p50_ms"] is None
