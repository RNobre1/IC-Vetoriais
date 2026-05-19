"""Testes de `lib.reporting` (TDD — escritos antes da implementação).

`lib.reporting` normaliza a saída dos benchmarks:
- `ResultadoBenchmark`: registro imutável (metadados + parâmetros + métricas + ambiente).
- `salvar_resultado(...)`: JSON UTF-8 determinístico em `code/results/`.
- `salvar_ground_truth` / `carregar_ground_truth`: persistência round-trip do
  top-K exato em `data/ground_truth/` (`.npz`).

Reprodutibilidade exige: nome de arquivo determinístico, JSON com `sort_keys`
(diff estável entre execuções), `ensure_ascii=False` (PT-BR sem escapes),
e round-trip exato dos arrays de ground truth.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest

from lib.reporting import (
    ResultadoBenchmark,
    carregar_ground_truth,
    salvar_ground_truth,
    salvar_resultado,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def resultado() -> ResultadoBenchmark:
    return ResultadoBenchmark(
        cenario="A",
        sistema="pgvector",
        n=100_000,
        timestamp_utc="2026-05-10T18:30:00Z",
        parametros={"ef_search": 64, "m": 16, "ef_construction": 200, "k": 10},
        metricas={"p50": 1.2, "p95": 3.4, "p99": 9.9, "qps": 812.5, "recall_at_10": 0.973},
        ambiente={"sgbd_imagem": "pgvector/pgvector:0.8.2-pg18-bookworm", "host": "dell-g15"},
    )


# ---------------------------------------------------------------------------
# ResultadoBenchmark — imutabilidade
# ---------------------------------------------------------------------------


def test_resultado_e_imutavel(resultado: ResultadoBenchmark) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        resultado.sistema = "qdrant"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# salvar_resultado — caminho e conteúdo
# ---------------------------------------------------------------------------


def test_salvar_resultado_nome_de_arquivo_segue_padrao(
    resultado: ResultadoBenchmark, tmp_path: Path
) -> None:
    caminho = salvar_resultado(resultado, results_dir=tmp_path)
    assert caminho.parent == tmp_path
    assert caminho.name == "cenario_A_pgvector_100000_2026-05-10T18-30-00Z.json"
    assert caminho.exists()


def test_salvar_resultado_cria_dir_inexistente(
    resultado: ResultadoBenchmark, tmp_path: Path
) -> None:
    destino = tmp_path / "results" / "nested"
    caminho = salvar_resultado(resultado, results_dir=destino)
    assert caminho.exists()


def test_json_tem_blocos_esperados(resultado: ResultadoBenchmark, tmp_path: Path) -> None:
    caminho = salvar_resultado(resultado, results_dir=tmp_path)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert set(dados.keys()) == {
        "cenario",
        "sistema",
        "n",
        "timestamp_utc",
        "parametros",
        "metricas",
        "ambiente",
    }
    assert dados["sistema"] == "pgvector"
    assert dados["metricas"]["recall_at_10"] == pytest.approx(0.973)
    assert dados["parametros"]["ef_search"] == 64


def test_json_e_deterministico_sort_keys(resultado: ResultadoBenchmark, tmp_path: Path) -> None:
    c1 = salvar_resultado(resultado, results_dir=tmp_path / "a")
    c2 = salvar_resultado(resultado, results_dir=tmp_path / "b")
    assert c1.read_text(encoding="utf-8") == c2.read_text(encoding="utf-8")
    # chaves de topo em ordem alfabética → sort_keys ativo
    texto = c1.read_text(encoding="utf-8")
    assert texto.index('"ambiente"') < texto.index('"cenario"') < texto.index('"sistema"')


def test_json_preserva_acentos_sem_escape(tmp_path: Path) -> None:
    r = ResultadoBenchmark(
        cenario="A",
        sistema="pgvector",
        n=1,
        timestamp_utc="2026-05-10T00-00-00Z",
        parametros={},
        metricas={},
        ambiente={"observacao": "execução com seleção de índice"},
    )
    caminho = salvar_resultado(r, results_dir=tmp_path)
    bruto = caminho.read_text(encoding="utf-8")
    assert "execução com seleção de índice" in bruto
    assert "\\u" not in bruto  # ensure_ascii=False


def test_salvar_resultado_roundtrip_semantico(
    resultado: ResultadoBenchmark, tmp_path: Path
) -> None:
    caminho = salvar_resultado(resultado, results_dir=tmp_path)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert dados == dataclasses.asdict(resultado)


# ---------------------------------------------------------------------------
# Ground truth — persistência round-trip
# ---------------------------------------------------------------------------


def test_ground_truth_roundtrip(tmp_path: Path) -> None:
    rng = np.random.default_rng(42)
    scores = rng.standard_normal((50, 10)).astype(np.float32)
    ids = rng.integers(0, 1000, size=(50, 10)).astype(np.int64)

    caminho = salvar_ground_truth(scores, ids, dest_dir=tmp_path, nome="msmarco_100k")
    assert caminho.exists()
    assert caminho.suffix == ".npz"

    scores_lido, ids_lido = carregar_ground_truth(caminho)
    np.testing.assert_array_equal(scores, scores_lido)
    np.testing.assert_array_equal(ids, ids_lido)
    assert scores_lido.dtype == np.float32
    assert ids_lido.dtype == np.int64


def test_ground_truth_cria_dir_inexistente(tmp_path: Path) -> None:
    destino = tmp_path / "data" / "ground_truth"
    scores = np.zeros((2, 3), dtype=np.float32)
    ids = np.zeros((2, 3), dtype=np.int64)
    caminho = salvar_ground_truth(scores, ids, dest_dir=destino, nome="x")
    assert caminho.exists()


def test_ground_truth_levanta_se_shapes_divergem(tmp_path: Path) -> None:
    scores = np.zeros((10, 5), dtype=np.float32)
    ids = np.zeros((10, 4), dtype=np.int64)
    with pytest.raises(ValueError, match="shape"):
        salvar_ground_truth(scores, ids, dest_dir=tmp_path, nome="x")


def test_ground_truth_levanta_se_nao_2d(tmp_path: Path) -> None:
    scores = np.zeros((10,), dtype=np.float32)
    ids = np.zeros((10,), dtype=np.int64)
    with pytest.raises(ValueError, match="2"):
        salvar_ground_truth(scores, ids, dest_dir=tmp_path, nome="x")
