"""Testes de `lib.footprint` (TDD — escritos antes da implementação).

Contexto: o §4.4 do relatório parcial lista "uso de recursos (memória, disco) e
tempo de indexação" como métrica, e o §5.2 declara que esses valores não foram
reportados porque a Etapa 3 apenas os imprimiu no console. Este módulo existe
para que a medição passe a ser **persistida** junto da curva.

O que os testes fixam, e por quê:

- **Instrumento explícito por sistema.** Cada SGBD contabiliza armazenamento de
  forma diferente; o número só é interpretável se o JSON disser *como* foi
  medido. Instrumento e critério são derivados de um mapa único (Regra 2-A),
  nunca redigitados no ponto de uso.
- **Falha não pode virar silêncio.** A medição histórica em
  `experimentos/etapa3_run_100k_500k.py` envolvia a coleta num `try/except` que
  reduzia o erro a uma linha de log. Coleta que falha precisa **levantar**:
  número ausente é recuperável, número errado não.
- **Fila do Weaviate por classe.** A instância hospeda várias classes ao mesmo
  tempo; esperar a fila global drenar mediria o vizinho, não o objeto medido.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

import pytest

from lib.footprint import (
    CONTAINER_POR_SISTEMA,
    CRITERIO_INDICE_UTILIZAVEL,
    INSTRUMENTO_DISCO,
    MedidaRecursos,
    aguardar_fila_weaviate,
    cronometrar_indexacao,
    diretorio_weaviate,
    ler_configuracao_pgvector,
    medir_disco_pgvector,
    medir_disco_qdrant,
    medir_disco_weaviate,
    medir_rss_bytes,
    parse_du_bytes,
    parse_du_kib_bytes,
    parse_mem_usage_bytes,
)

# ---------------------------------------------------------------------------
# Dublês
# ---------------------------------------------------------------------------


class ExecutorFake:
    """Substitui a execução de `docker ...`, registrando o argv recebido.

    Aceita uma saída por chamada, na ordem — a coleta de disco emite dois
    comandos (blocos alocados e tamanho aparente).
    """

    def __init__(self, *saidas: str) -> None:
        self.saidas = saidas or ("",)
        self.chamadas: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> str:
        saida = self.saidas[min(len(self.chamadas), len(self.saidas) - 1)]
        self.chamadas.append(list(argv))
        return saida

    @property
    def ultimo_argv(self) -> list[str]:
        return self.chamadas[-1]


class ExecutorQueFalha:
    def __call__(self, argv: Sequence[str]) -> str:
        raise RuntimeError("comando docker falhou: No such container")


class _CursorFake:
    def __init__(self, linha: tuple[Any, ...]) -> None:
        self._linha = linha
        self.sql: str = ""
        self.params: Any = None

    def __enter__(self) -> _CursorFake:
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self.sql = sql
        self.params = params

    def fetchone(self) -> tuple[Any, ...]:
        return self._linha


class ConexaoFake:
    def __init__(self, linha: tuple[Any, ...]) -> None:
        self._cursor = _CursorFake(linha)

    def cursor(self) -> _CursorFake:
        return self._cursor


class _ShardFake:
    def __init__(self, collection: str, fila: int, status: str = "READY") -> None:
        self.collection = collection
        self.vector_queue_length = fila
        self.vector_indexing_status = status


class _NodeFake:
    def __init__(self, shards: list[_ShardFake]) -> None:
        self.shards = shards


class ClusterFake:
    """Espelha `client.cluster.nodes(...)` do weaviate-client 4.21."""

    def __init__(self, respostas: list[list[_ShardFake]]) -> None:
        self._respostas = respostas
        self.chamadas = 0

    def nodes(self, collection: str | None = None, *, output: str | None = None) -> list[_NodeFake]:
        i = min(self.chamadas, len(self._respostas) - 1)
        self.chamadas += 1
        return [_NodeFake(self._respostas[i])]


class ClienteWeaviateFake:
    def __init__(self, respostas: list[list[_ShardFake]]) -> None:
        self.cluster = ClusterFake(respostas)


@pytest.fixture(autouse=True)
def _sem_dormir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nenhum teste unitário pode gastar tempo de parede em `sleep`."""
    monkeypatch.setattr("lib.footprint.time.sleep", lambda _s: None)


# ---------------------------------------------------------------------------
# Parsers — funções puras
# ---------------------------------------------------------------------------


def test_parse_du_extrai_bytes_da_primeira_coluna() -> None:
    assert parse_du_bytes("626003482\t/qdrant/storage/collections/bench_a_100000\n") == 626003482


def test_parse_du_rejeita_saida_sem_numero() -> None:
    """`du` de caminho inexistente escreve erro em texto — não pode virar 0."""
    with pytest.raises(ValueError, match="du"):
        parse_du_bytes("du: cannot access '/x': No such file or directory\n")


def test_parse_mem_usage_converte_mebibytes() -> None:
    assert parse_mem_usage_bytes("26.56MiB / 15.3GiB") == round(26.56 * 1024**2)


def test_parse_mem_usage_converte_gibibytes() -> None:
    assert parse_mem_usage_bytes("1.5GiB / 15.3GiB") == round(1.5 * 1024**3)


def test_parse_mem_usage_converte_bytes_crus() -> None:
    assert parse_mem_usage_bytes("512B / 15.3GiB") == 512


def test_parse_mem_usage_rejeita_unidade_desconhecida() -> None:
    with pytest.raises(ValueError, match="unidade"):
        parse_mem_usage_bytes("26.56XiB / 15.3GiB")


def test_diretorio_weaviate_e_a_classe_em_minusculas() -> None:
    """O Weaviate materializa a classe `BenchA100000` em `bencha100000`."""
    assert diretorio_weaviate("BenchA100000") == "bencha100000"


# ---------------------------------------------------------------------------
# Coleta de disco
# ---------------------------------------------------------------------------


def test_disco_pgvector_usa_o_catalogo_do_proprio_banco() -> None:
    conn = ConexaoFake((370_925_568, 163_840_000, 207_011_840))

    medida = medir_disco_pgvector(conn, nome_tabela="bench_a_100000")

    assert medida == {
        "total_bytes": 370_925_568,
        "heap_bytes": 163_840_000,
        "indices_bytes": 207_011_840,
    }


def test_disco_pgvector_consulta_a_tabela_pedida() -> None:
    conn = ConexaoFake((1, 2, 3))

    medir_disco_pgvector(conn, nome_tabela="bench_b_500000")

    assert "pg_total_relation_size" in conn._cursor.sql
    assert "bench_b_500000" in str(conn._cursor.params)


def test_disco_qdrant_reporta_blocos_alocados_e_nao_tamanho_aparente() -> None:
    """O Qdrant pré-aloca arquivos esparsos de 32 MiB (WAL e `page_0.dat`).

    Medido com `--apparent-size`, `bench_a_200` — 200 vetores, ~300 KB de dado —
    aparecia com 560 MB, inflação de 450×. Espaço em disco é bloco alocado.
    """
    executar = ExecutorFake(
        "1276\t/qdrant/storage/collections/bench_a_200\n",
        "587471615\t/qdrant/storage/collections/bench_a_200\n",
    )

    medida = medir_disco_qdrant(executar, nome_colecao="bench_a_200")

    assert medida == {"total_bytes": 1276 * 1024, "aparente_bytes": 587_471_615}


def test_disco_qdrant_usa_du_sk_para_o_numero_comparavel() -> None:
    """`-sk` é o denominador comum: o `du` do Weaviate é BusyBox, sem `--block-size`."""
    executar = ExecutorFake("1276\tx\n", "587471615\tx\n")

    medir_disco_qdrant(executar, nome_colecao="bench_a_200")

    assert executar.chamadas[0] == [
        "docker",
        "exec",
        "ic-qdrant",
        "du",
        "-sk",
        "/qdrant/storage/collections/bench_a_200",
    ]
    assert "-sb" in executar.chamadas[1]


def test_disco_weaviate_mede_o_diretorio_em_minusculas_da_classe() -> None:
    executar = ExecutorFake(
        "312252\t/var/lib/weaviate/bencha100000\n",
        "319709452\t/var/lib/weaviate/bencha100000\n",
    )

    medida = medir_disco_weaviate(executar, nome_classe="BenchA100000")

    assert medida == {"total_bytes": 312_252 * 1024, "aparente_bytes": 319_709_452}
    assert executar.chamadas[0][-1] == "/var/lib/weaviate/bencha100000"


def test_parse_du_kib_converte_para_bytes() -> None:
    assert parse_du_kib_bytes("1276\t/x\n") == 1276 * 1024


def test_disco_qdrant_propaga_falha_em_vez_de_engolir() -> None:
    """Regressão da medição histórica, que reduzia erro de coleta a um log."""
    with pytest.raises(RuntimeError, match="No such container"):
        medir_disco_qdrant(ExecutorQueFalha(), nome_colecao="c")


# ---------------------------------------------------------------------------
# Memória residente
# ---------------------------------------------------------------------------


def test_rss_le_o_uso_do_docker_stats() -> None:
    executar = ExecutorFake("998MiB / 15.3GiB\n")

    assert medir_rss_bytes(executar, sistema="weaviate") == round(998 * 1024**2)


def test_rss_consulta_o_conteiner_do_sistema_pedido() -> None:
    executar = ExecutorFake("31.73MiB / 15.3GiB\n")

    medir_rss_bytes(executar, sistema="qdrant")

    assert "ic-qdrant" in executar.ultimo_argv
    assert "--no-stream" in executar.ultimo_argv


def test_rss_rejeita_sistema_desconhecido() -> None:
    with pytest.raises(ValueError, match="sistema"):
        medir_rss_bytes(ExecutorFake(), sistema="milvus")


# ---------------------------------------------------------------------------
# Weaviate — espera pela drenagem da fila de indexação
# ---------------------------------------------------------------------------


def test_espera_weaviate_ate_a_fila_drenar() -> None:
    cliente = ClienteWeaviateFake(
        [
            [_ShardFake("BenchA100000", fila=5_000, status="INDEXING")],
            [_ShardFake("BenchA100000", fila=120, status="INDEXING")],
            [_ShardFake("BenchA100000", fila=0, status="READY")],
        ]
    )

    aguardar_fila_weaviate(cliente, nome_classe="BenchA100000")

    assert cliente.cluster.chamadas == 3


def test_espera_weaviate_exige_status_ready_mesmo_com_fila_zerada() -> None:
    """Fila vazia com indexação em curso ainda é índice pela metade."""
    cliente = ClienteWeaviateFake(
        [
            [_ShardFake("BenchA100000", fila=0, status="INDEXING")],
            [_ShardFake("BenchA100000", fila=0, status="READY")],
        ]
    )

    aguardar_fila_weaviate(cliente, nome_classe="BenchA100000")

    assert cliente.cluster.chamadas == 2


def test_espera_weaviate_ignora_shards_de_outras_classes() -> None:
    """A instância hospeda várias classes; medir o vizinho falsearia o tempo."""
    cliente = ClienteWeaviateFake(
        [
            [
                _ShardFake("BenchA100000", fila=0, status="READY"),
                _ShardFake("BenchB500000", fila=90_000, status="INDEXING"),
            ]
        ]
    )

    aguardar_fila_weaviate(cliente, nome_classe="BenchA100000")

    assert cliente.cluster.chamadas == 1


def test_espera_weaviate_desiste_apos_o_limite() -> None:
    cliente = ClienteWeaviateFake([[_ShardFake("BenchA100000", fila=7, status="INDEXING")]])

    with pytest.raises(TimeoutError, match="fila"):
        aguardar_fila_weaviate(cliente, nome_classe="BenchA100000", tentativas=4)

    assert cliente.cluster.chamadas == 4


def test_espera_weaviate_levanta_se_a_classe_nao_aparece() -> None:
    """Classe ausente do relatório de nodes é erro, não fila drenada."""
    cliente = ClienteWeaviateFake([[_ShardFake("Outra", fila=0, status="READY")]])

    with pytest.raises(TimeoutError, match="fila"):
        aguardar_fila_weaviate(cliente, nome_classe="BenchA100000", tentativas=2)


# ---------------------------------------------------------------------------
# Cronometragem da indexação
#
# O relógio precisa parar quando o índice está utilizável, não quando a última
# escrita foi aceita: pgvector constrói o índice em operação bloqueante dentro
# da própria carga, enquanto Qdrant e Weaviate constroem em background. Parar no
# retorno do upsert favoreceria artificialmente os dois últimos.
# ---------------------------------------------------------------------------


class RelogioFalso:
    """Devolve, a cada chamada, o próximo instante da lista."""

    def __init__(self, instantes: list[float]) -> None:
        self._instantes = instantes
        self.chamadas = 0

    def __call__(self) -> float:
        valor = self._instantes[min(self.chamadas, len(self._instantes) - 1)]
        self.chamadas += 1
        return valor


def test_cronometra_pgvector_sem_separar_carga_de_indice() -> None:
    """Sem construção assíncrona, só existe o tempo até o índice ficar pronto."""
    carga, total = cronometrar_indexacao(
        "pgvector",
        carregar=lambda: None,
        relogio=RelogioFalso([0.0, 873.9]),
    )

    assert carga is None
    assert total == pytest.approx(873.9)


def test_cronometra_qdrant_separando_carga_da_espera() -> None:
    """A diferença entre os dois números é o custo da indexação em background."""
    carga, total = cronometrar_indexacao(
        "qdrant",
        carregar=lambda: None,
        aguardar_indice=lambda: None,
        relogio=RelogioFalso([0.0, 19.8, 42.1]),
    )

    assert carga == pytest.approx(19.8)
    assert total == pytest.approx(42.1)


def test_espera_do_indice_ocorre_depois_da_carga() -> None:
    ordem: list[str] = []
    cronometrar_indexacao(
        "weaviate",
        carregar=lambda: ordem.append("carga"),
        aguardar_indice=lambda: ordem.append("espera"),
        relogio=RelogioFalso([0.0, 1.0, 2.0]),
    )

    assert ordem == ["carga", "espera"]


def test_cronometrar_rejeita_sistema_desconhecido() -> None:
    with pytest.raises(ValueError, match="sistema"):
        cronometrar_indexacao("milvus", carregar=lambda: None)


# ---------------------------------------------------------------------------
# MedidaRecursos — o registro que vai ao JSON
# ---------------------------------------------------------------------------


def test_medida_deriva_criterio_e_instrumento_do_sistema() -> None:
    """Critério e instrumento não são redigitados no ponto de uso (Regra 2-A)."""
    medida = MedidaRecursos.para_sistema(
        "qdrant",
        disco={"total_bytes": 626_003_482},
        memoria_rss_bytes=33_268_531,
        tempo_carga_s=19.8,
        tempo_indice_utilizavel_s=42.1,
    )

    assert medida.criterio_indice_utilizavel == CRITERIO_INDICE_UTILIZAVEL["qdrant"]
    assert medida.instrumento_disco == INSTRUMENTO_DISCO["qdrant"]
    assert medida.container == CONTAINER_POR_SISTEMA["qdrant"]


def test_medida_e_imutavel() -> None:
    medida = MedidaRecursos.para_sistema("pgvector", disco={"total_bytes": 1})
    with pytest.raises(dataclasses.FrozenInstanceError):
        medida.sistema = "qdrant"  # type: ignore[misc]


def test_medida_rejeita_sistema_desconhecido() -> None:
    with pytest.raises(ValueError, match="sistema"):
        MedidaRecursos.para_sistema("milvus", disco={})


def test_medida_serializa_com_o_criterio_junto_do_numero() -> None:
    """Tempo de indexação sem o critério que parou o relógio é incomparável."""
    medida = MedidaRecursos.para_sistema(
        "weaviate",
        disco={"total_bytes": 319_709_452},
        tempo_indice_utilizavel_s=88.4,
    )

    dados = medida.para_json()

    assert dados["tempo_indice_utilizavel_s"] == 88.4
    assert dados["criterio_indice_utilizavel"] == "fila_vetorial_drenada"
    assert dados["instrumento_disco"] == "du_sk_diretorio_classe"
    assert dados["disco"]["total_bytes"] == 319_709_452


def test_medida_calcula_o_delta_de_memoria_sobre_a_linha_de_base() -> None:
    """RSS absoluto não é atribuível ao dado medido.

    O Weaviate mantém residente o grafo de **todas** as classes da instância —
    chegou a 6,1 GiB com oito coleções acumuladas, enquanto o Qdrant, que usa
    mmap, reportava 65 MiB. Comparar os absolutos mediria o histórico do
    contêiner, não o custo daquele conjunto de dados.
    """
    medida = MedidaRecursos.para_sistema(
        "weaviate",
        disco={},
        memoria_rss_baseline_bytes=1_000_000,
        memoria_rss_bytes=1_750_000,
    )

    assert medida.memoria_rss_delta_bytes == 750_000


def test_medida_sem_linha_de_base_nao_inventa_delta() -> None:
    medida = MedidaRecursos.para_sistema("qdrant", disco={}, memoria_rss_bytes=500)

    assert medida.memoria_rss_delta_bytes is None


def test_medida_admite_delta_negativo() -> None:
    """Liberação de memória durante a carga é fato observável, não erro a zerar."""
    medida = MedidaRecursos.para_sistema(
        "pgvector",
        disco={},
        memoria_rss_baseline_bytes=900,
        memoria_rss_bytes=400,
    )

    assert medida.memoria_rss_delta_bytes == -500


def test_medida_carrega_a_configuracao_que_governa_o_build() -> None:
    """Tempo de indexação sem os parâmetros do build não é reprodutível.

    `maintenance_work_mem` deixou de ser default herdado da imagem e passou a
    ser escolha declarada (2 GB), porque com 64 MB o grafo de 500 mil vetores
    não cabia em memória. O valor governa diretamente o tempo medido, então
    precisa viajar junto dele.
    """
    medida = MedidaRecursos.para_sistema(
        "pgvector",
        disco={},
        tempo_indice_utilizavel_s=812.0,
        configuracao={"maintenance_work_mem": "2GB", "max_parallel_maintenance_workers": "2"},
    )

    assert medida.para_json()["configuracao"]["maintenance_work_mem"] == "2GB"


def test_medida_sem_configuracao_grava_dicionario_vazio() -> None:
    assert MedidaRecursos.para_sistema("qdrant", disco={}).para_json()["configuracao"] == {}


def test_configuracao_pgvector_le_os_parametros_do_servidor() -> None:
    """Os valores vêm do servidor no momento da medição, não de constante no código."""
    conn = ConexaoFake(("2GB", "2", "128MB"))

    cfg = ler_configuracao_pgvector(conn)

    assert cfg == {
        "maintenance_work_mem": "2GB",
        "max_parallel_maintenance_workers": "2",
        "shared_buffers": "128MB",
    }
    assert "pg_settings" in conn._cursor.sql or "current_setting" in conn._cursor.sql


def test_medida_aceita_ausencia_de_coleta() -> None:
    """Medida parcial é registrável; o que não pode é número inventado."""
    dados = MedidaRecursos.para_sistema("pgvector", disco={}).para_json()

    assert dados["memoria_rss_bytes"] is None
    assert dados["tempo_indice_utilizavel_s"] is None
