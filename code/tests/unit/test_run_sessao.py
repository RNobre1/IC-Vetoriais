"""Testes das partes puras do executor da sessão (`benchmarks.run_sessao`).

O executor mede, numa escala e num sistema, todos os cenários a partir do
menor número de seeds que preserva o que cada cenário mede (decisão
[[../../vault/decisões/2026-11-15-protocolo-da-sessao-final]]). O plano de
passos é dado puro e testado aqui; a execução contra os SGBDs é exercitada
pelo ensaio da sessão.
"""

from __future__ import annotations

import json

import pytest

from benchmarks.run_sessao import (
    ConfigSessao,
    ordem_dos_sistemas,
    parse_args,
    plano_de_passos,
    registrar_marco,
    sonda_cpu,
    varredura_b,
)

# ---------------------------------------------------------------------------
# Plano de passos
# ---------------------------------------------------------------------------


def test_pgvector_semeia_uma_vez_e_ganha_btree_para_o_equalizado() -> None:
    passos = plano_de_passos("pgvector", cenario_c=True)
    assert passos == [
        "seed_b",
        "A",
        "B",
        "btree",
        "B_eq",
        "drop_btree",
        "C",
        "limpar",
    ]
    assert passos.count("seed_b") == 1


def test_pgvector_sem_cenario_c() -> None:
    assert plano_de_passos("pgvector", cenario_c=False) == [
        "seed_b",
        "A",
        "B",
        "btree",
        "B_eq",
        "limpar",
    ]


@pytest.mark.parametrize("sistema", ["qdrant", "weaviate"])
def test_especializados_tem_um_seed_por_layout(sistema: str) -> None:
    # O C roda na coleção do A, antes de ela ser descartada; o índice de
    # payload do B não entra na coleção do A.
    assert plano_de_passos(sistema, cenario_c=True) == [
        "seed_a",
        "A",
        "C",
        "limpar",
        "seed_b",
        "B",
        "limpar",
        "seed_b_eq",
        "B_eq",
        "limpar",
    ]


def test_sistema_desconhecido() -> None:
    with pytest.raises(ValueError, match="sistema"):
        plano_de_passos("milvus", cenario_c=False)


# ---------------------------------------------------------------------------
# Ordem dos sistemas e varredura do B
# ---------------------------------------------------------------------------


def test_ordem_dos_sistemas_gira_por_escala() -> None:
    assert ordem_dos_sistemas(100_000) == ["pgvector", "qdrant", "weaviate"]
    assert ordem_dos_sistemas(1_000_000) == ["qdrant", "weaviate", "pgvector"]
    assert ordem_dos_sistemas(500_000) == ["weaviate", "pgvector", "qdrant"]


def test_ordem_dos_sistemas_de_escala_de_ensaio_e_a_canonica() -> None:
    assert ordem_dos_sistemas(5_000) == ["pgvector", "qdrant", "weaviate"]


EFS = [16, 32, 64, 128, 256]
SELS = [0.01, 0.1, 0.5, 1.0]


def test_varredura_b_completa_por_padrao() -> None:
    assert varredura_b("qdrant", n=1_000_000, equalizado=False, seletividades=SELS, efs=EFS) == [
        (SELS, EFS)
    ]
    assert varredura_b("weaviate", n=1_000_000, equalizado=True, seletividades=SELS, efs=EFS) == [
        (SELS, EFS)
    ]


def test_varredura_b_weaviate_padrao_reduz_acima_do_corte_em_escala_grande() -> None:
    # Acima do flatSearchCutoff (40.000 elegíveis) padrão e equalizado executam
    # o mesmo caminho; p=10% fica completo como controle do mecanismo, e
    # p=50%/100% só no ponto de referência ef=64.
    assert varredura_b("weaviate", n=1_000_000, equalizado=False, seletividades=SELS, efs=EFS) == [
        ([0.01, 0.1], EFS),
        ([0.5, 1.0], [64]),
    ]
    assert varredura_b("weaviate", n=500_000, equalizado=False, seletividades=SELS, efs=EFS) == [
        ([0.01, 0.1], EFS),
        ([0.5, 1.0], [64]),
    ]


def test_varredura_b_weaviate_padrao_completa_em_100k() -> None:
    assert varredura_b("weaviate", n=100_000, equalizado=False, seletividades=SELS, efs=EFS) == [
        (SELS, EFS)
    ]


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


def test_parse_args_defaults() -> None:
    cfg = parse_args(["--n", "100000", "--sistema", "qdrant"])
    assert isinstance(cfg, ConfigSessao)
    assert cfg.n_base == 100_000
    assert cfg.sistema == "qdrant"
    assert cfg.n_queries == 1_000
    assert cfg.repeticoes_a == 5
    assert cfg.ef_search == EFS
    assert cfg.seletividades == SELS
    assert cfg.cenario_c is False
    assert cfg.janelas_c == [0, 10, 100, 1000, 0, 0]
    assert cfg.duracao_c_s == 60.0
    assert cfg.aquecimento_c_s == 5.0
    assert cfg.ef_c == 64
    assert cfg.pool_c == 80_000


def test_parse_args_cenario_c_e_janelas_curtas() -> None:
    cfg = parse_args(
        [
            "--n",
            "5000",
            "--sistema",
            "weaviate",
            "--cenario-c",
            "--duracao-c",
            "10",
            "--aquecimento-c",
            "2",
            "--pool-c",
            "15000",
            "--queries",
            "200",
        ]
    )
    assert cfg.cenario_c is True
    assert cfg.duracao_c_s == 10.0
    assert cfg.aquecimento_c_s == 2.0
    assert cfg.pool_c == 15_000
    assert cfg.n_queries == 200


def test_parse_args_recusa_pool_insuficiente() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--n", "5000", "--sistema", "qdrant", "--cenario-c", "--pool-c", "100"])


def test_parse_args_recusa_sistema_desconhecido() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--n", "5000", "--sistema", "milvus"])


# ---------------------------------------------------------------------------
# Marcos e sonda de CPU
# ---------------------------------------------------------------------------


def test_registrar_marco_acrescenta_linha_jsonl(tmp_path) -> None:
    arq = tmp_path / "marcos.jsonl"
    registrar_marco(arq, n=100, sistema="qdrant", passo="A", evento="inicio", extra={"x": 1})
    registrar_marco(arq, n=100, sistema="qdrant", passo="A", evento="fim")
    linhas = [json.loads(linha) for linha in arq.read_text(encoding="utf-8").splitlines()]
    assert [linha["evento"] for linha in linhas] == ["inicio", "fim"]
    assert linhas[0]["x"] == 1
    assert linhas[0]["ts_utc"].endswith("Z")
    assert linhas[0]["sistema"] == "qdrant"


def test_sonda_cpu_devolve_tempo_positivo_de_carga_fixa() -> None:
    r = sonda_cpu(iteracoes=20_000)
    assert r["sonda_cpu_s"] > 0
    assert r["sonda_cpu_iteracoes"] == 20_000
