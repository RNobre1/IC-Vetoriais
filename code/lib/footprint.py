"""Coleta de uso de recursos e tempo de indexação por SGBD.

O §4.4 do relatório lista "uso de recursos (memória, disco) e tempo de
indexação" entre as métricas do trabalho. Na Etapa 3 esses valores só foram
impressos no console, o que os tornou não verificáveis a posteriori. Este
módulo produz a medida em formato persistível, para que ela viaje junto da
curva recall×QPS no mesmo JSON.

Cada SGBD contabiliza armazenamento de forma diferente, então o número sozinho
não é interpretável: o registro carrega sempre **qual instrumento** produziu o
valor e **qual critério** parou o relógio da indexação. Vide
`vault/decisões/2026-08-22-medicao-de-footprint-e-tempo-de-indexacao`.

Duas escolhas de projeto valem explicação:

- **Colaboradores injetados.** A execução de `docker` entra como um callable,
  o que torna a coleta testável com dublês e mantém o módulo livre de I/O na
  suíte unitária.
- **Falha levanta.** A medição histórica de `experimentos/` embrulhava a coleta
  num `try/except` que reduzia o erro a uma linha de log, produzindo ausência
  silenciosa. Aqui, coleta que falha interrompe: número ausente é recuperável,
  número errado entra em tabela.
"""

from __future__ import annotations

import dataclasses
import re
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

SISTEMAS = ("pgvector", "qdrant", "weaviate")

CONTAINER_POR_SISTEMA = {
    "pgvector": "ic-pgvector",
    "qdrant": "ic-qdrant",
    "weaviate": "ic-weaviate",
}

# Onde cada SGBD materializa os dados de uma coleção dentro do contêiner.
# `pgvector` não tem diretório por tabela — é medido pelo catálogo.
CAMINHO_COLECAO = {
    "qdrant": "/qdrant/storage/collections",
    "weaviate": "/var/lib/weaviate",
}

# O que parou o relógio da indexação. pgvector constrói o índice em operação
# única e bloqueante; Qdrant e Weaviate constroem em background, e parar no
# retorno da última escrita os favoreceria artificialmente.
CRITERIO_INDICE_UTILIZAVEL = {
    "pgvector": "create_index_retornou",
    "qdrant": "colecao_status_green",
    "weaviate": "fila_vetorial_drenada",
}

# Como o valor de disco foi obtido. Instrumentos distintos medem a mesma
# grandeza física (bytes persistidos para este conjunto de dados), mas a
# diferença precisa estar declarada no arquivo.
INSTRUMENTO_DISCO = {
    "pgvector": "pg_total_relation_size",
    "qdrant": "du_diretorio_colecao",
    "weaviate": "du_diretorio_classe",
}

# 1800 × 2 s = 1 h. Backstop contra fila que nunca drena, não expectativa de
# duração: o seed de 500 mil no Weaviate roda em minutos.
TENTATIVAS_PADRAO = 1800
INTERVALO_PADRAO = 2.0

Executor = Callable[[Sequence[str]], str]

_UNIDADES_MEM = {
    "B": 1,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
    "TiB": 1024**4,
}
_PADRAO_MEM = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)\s*$")


# ---------------------------------------------------------------------------
# Execução de comando
# ---------------------------------------------------------------------------


def executar_docker(argv: Sequence[str]) -> str:
    """Roda `argv` e devolve o stdout. Levanta `RuntimeError` em saída não-zero."""
    proc = subprocess.run(list(argv), capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"comando falhou ({' '.join(argv)}): {proc.stderr.strip()}")
    return proc.stdout


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_du_bytes(saida: str) -> int:
    """Extrai a contagem de bytes da primeira coluna de `du -sb`.

    `du` escreve erro em texto e ainda assim pode sair com status zero em
    alguns cenários; sem esta checagem, "cannot access" viraria footprint 0.
    """
    campos = saida.strip().split()
    if not campos or not campos[0].isdigit():
        raise ValueError(f"saída de `du` sem contagem de bytes: {saida.strip()!r}")
    return int(campos[0])


def parse_mem_usage_bytes(campo: str) -> int:
    """Converte o campo `MemUsage` do `docker stats` ("26.56MiB / 15.3GiB") em bytes."""
    usado = campo.split("/")[0]
    casado = _PADRAO_MEM.match(usado)
    if casado is None:
        raise ValueError(f"campo de memória ilegível: {campo!r}")
    valor, unidade = casado.group(1), casado.group(2)
    if unidade not in _UNIDADES_MEM:
        raise ValueError(f"unidade desconhecida em {campo!r}: {unidade!r}")
    return round(float(valor) * _UNIDADES_MEM[unidade])


def diretorio_weaviate(nome_classe: str) -> str:
    """Nome do diretório em que o Weaviate materializa a classe (minúsculas)."""
    return nome_classe.lower()


def _validar_sistema(sistema: str) -> str:
    if sistema not in SISTEMAS:
        raise ValueError(f"sistema desconhecido: {sistema!r}. Válidos: {SISTEMAS}.")
    return sistema


# ---------------------------------------------------------------------------
# Coleta de disco
# ---------------------------------------------------------------------------


def medir_disco_pgvector(conn: Any, *, nome_tabela: str) -> dict[str, int]:
    """Bytes da tabela pelo catálogo: total, heap e índices.

    `pg_total_relation_size` soma heap, TOAST e todos os índices — inclusive o
    HNSW e o B-tree opcional do Cenário B equalizado. É a contabilidade do
    próprio servidor sobre os arquivos daquela tabela.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pg_total_relation_size(%s::regclass), "
            "pg_relation_size(%s::regclass), "
            "pg_indexes_size(%s::regclass)",
            (nome_tabela, nome_tabela, nome_tabela),
        )
        total, heap, indices = cur.fetchone()
    return {
        "total_bytes": int(total),
        "heap_bytes": int(heap),
        "indices_bytes": int(indices),
    }


def medir_disco_qdrant(executar: Executor, *, nome_colecao: str) -> dict[str, int]:
    """Bytes do diretório da coleção dentro do contêiner do Qdrant."""
    caminho = f"{CAMINHO_COLECAO['qdrant']}/{nome_colecao}"
    saida = executar(["docker", "exec", CONTAINER_POR_SISTEMA["qdrant"], "du", "-sb", caminho])
    return {"total_bytes": parse_du_bytes(saida)}


def medir_disco_weaviate(executar: Executor, *, nome_classe: str) -> dict[str, int]:
    """Bytes do diretório da classe dentro do contêiner do Weaviate."""
    caminho = f"{CAMINHO_COLECAO['weaviate']}/{diretorio_weaviate(nome_classe)}"
    saida = executar(["docker", "exec", CONTAINER_POR_SISTEMA["weaviate"], "du", "-sb", caminho])
    return {"total_bytes": parse_du_bytes(saida)}


# ---------------------------------------------------------------------------
# Memória residente
# ---------------------------------------------------------------------------


def medir_rss_bytes(executar: Executor, *, sistema: str) -> int:
    """Memória em uso pelo contêiner do `sistema`, via `docker stats`.

    Medida pontual do processo no instante da coleta, não atribuível apenas ao
    conjunto de dados medido — o valor inclui estruturas de servidor e cache.
    O mesmo instrumento é aplicado aos três contêineres.
    """
    container = CONTAINER_POR_SISTEMA[_validar_sistema(sistema)]
    saida = executar(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container])
    return parse_mem_usage_bytes(saida)


# ---------------------------------------------------------------------------
# Weaviate — espera pela drenagem da fila de indexação
# ---------------------------------------------------------------------------


def aguardar_fila_weaviate(
    client: Any,
    *,
    nome_classe: str,
    tentativas: int = TENTATIVAS_PADRAO,
    intervalo: float = INTERVALO_PADRAO,
) -> None:
    """Bloqueia até os shards de `nome_classe` ficarem `READY` com fila zerada.

    O `batch` retorna quando os objetos foram aceitos, não quando o HNSW
    terminou de indexá-los. Só os shards **desta** classe contam: a instância
    hospeda várias ao mesmo tempo, e olhar a fila global mediria o vizinho.

    Levanta `TimeoutError` se a fila não drenar — inclusive quando a classe não
    aparece no relatório de nodes, caso em que não há evidência de índice
    pronto.
    """
    pendente = "classe ausente do relatório de nodes"
    for tentativa in range(tentativas):
        shards = [
            shard
            for no in client.cluster.nodes(collection=nome_classe, output="verbose")
            for shard in no.shards
            if shard.collection == nome_classe
        ]
        if shards and all(
            shard.vector_queue_length == 0 and shard.vector_indexing_status == "READY"
            for shard in shards
        ):
            return
        if shards:
            pendente = ", ".join(
                f"{s.name if hasattr(s, 'name') else '?'}="
                f"{s.vector_queue_length}/{s.vector_indexing_status}"
                for s in shards
            )
        if tentativa < tentativas - 1:
            time.sleep(intervalo)
    raise TimeoutError(
        f"fila de indexação da classe {nome_classe!r} não drenou após {tentativas} "
        f"consultas (situação: {pendente}); índice HNSW ainda em construção"
    )


# ---------------------------------------------------------------------------
# Registro persistível
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MedidaRecursos:
    """Uso de recursos e tempo de indexação de um sistema, pronto para o JSON.

    `criterio_indice_utilizavel` e `instrumento_disco` acompanham os números
    porque sem eles o valor não é comparável entre sistemas — são derivados dos
    mapas do módulo, nunca redigitados no ponto de uso (Regra 2-A).
    """

    sistema: str
    container: str
    instrumento_disco: str
    criterio_indice_utilizavel: str
    disco: dict[str, int] = field(default_factory=dict)
    memoria_rss_bytes: int | None = None
    tempo_carga_s: float | None = None
    tempo_indice_utilizavel_s: float | None = None

    @classmethod
    def para_sistema(
        cls,
        sistema: str,
        *,
        disco: dict[str, int],
        memoria_rss_bytes: int | None = None,
        tempo_carga_s: float | None = None,
        tempo_indice_utilizavel_s: float | None = None,
    ) -> MedidaRecursos:
        """Monta a medida derivando contêiner, instrumento e critério do sistema."""
        _validar_sistema(sistema)
        return cls(
            sistema=sistema,
            container=CONTAINER_POR_SISTEMA[sistema],
            instrumento_disco=INSTRUMENTO_DISCO[sistema],
            criterio_indice_utilizavel=CRITERIO_INDICE_UTILIZAVEL[sistema],
            disco=dict(disco),
            memoria_rss_bytes=memoria_rss_bytes,
            tempo_carga_s=tempo_carga_s,
            tempo_indice_utilizavel_s=tempo_indice_utilizavel_s,
        )

    def para_json(self) -> dict[str, Any]:
        """Dicionário serializável — a forma que entra no JSON da curva."""
        return dataclasses.asdict(self)
