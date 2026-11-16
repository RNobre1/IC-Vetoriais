"""Carregamento, filtragem temporal e classificação dos resultados da sessão.

Cada sessão de medição (ex.: scripts/sessao_final.sh) define uma janela temporal
delimitada pelos marcos registrados em `marcos.jsonl`. Os arquivos de resultado
em `results/` cujo timestamp pertença à janela são carregados e classificados por:
- Cenário e condição:
  - "A": Cenário A executado pelo protocolo novo (com `protocolo == "sessao-2026-11"`)
  - "A_ponte": Cenário A executado na mesma sessão pelo protocolo anterior
  - "B_padrao": Cenário B na condição padrão (`equalizado == False`)
  - "B_eq": Cenário B na condição equalizada (`equalizado == True`)
  - "C": Cenário C (taxa sustentada sob escrita concorrente)
- Sistema (pgvector, qdrant, weaviate)
- Escala N (100k, 500k, 1M, etc.)

Tentativas repetidas para o mesmo par (condição, sistema, N) mantêm o arquivo mais
recente e registram aviso informativo para auditoria da sessão. Arquivos corrompidos
também emitem aviso informativo em vez de falharem silenciosamente.
"""

from __future__ import annotations

import glob
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def normalizar_timestamp(ts: str) -> datetime:
    """Converte representações ISO 8601 em datetime UTC com timezone.

    Suporta variações comuns nos nomes de arquivo e registros:
    - Com traços na hora (slug seguro para filesystem): "2026-11-15T14-51-40Z"
    - Padrão ISO 8601 com dois pontos: "2026-11-15T14:46:57.252Z"
    """
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1]
    if "T" in s:
        data_str, hora_str = s.split("T", 1)
        # Substitui traços por dois pontos nos campos de tempo (hora-minuto-segundo)
        partes_hora = hora_str.replace("-", ":")
        s = f"{data_str}T{partes_hora}"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


@dataclass(frozen=True)
class ArquivoSessao:
    """Registro indexado de um arquivo de resultado da sessão."""

    caminho: Path
    cenario: str
    sistema: str
    n: int
    condicao: str
    timestamp_utc: str
    dados: dict[str, Any]

    @property
    def pontos(self) -> list[dict[str, Any]]:
        return self.dados.get("pontos", [])

    @property
    def recursos(self) -> dict[str, Any]:
        return self.dados.get("recursos", {})


@dataclass
class Sessao:
    """Conjunto de resultados classificados e marcos de uma sessão experimental."""

    arquivos: dict[tuple[str, str, int], ArquivoSessao] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)
    marcos: list[dict[str, Any]] = field(default_factory=list)
    inicio_utc: str | None = None
    fim_utc: str | None = None

    def obter(self, condicao: str, sistema: str, n: int) -> ArquivoSessao | None:
        """Busca arquivo indexado pela chave (condição, sistema, escala)."""
        return self.arquivos.get((condicao, sistema.lower(), n))

    @property
    def escalas(self) -> list[int]:
        """Lista ordenada de escalas presentes na sessão."""
        return sorted({arq.n for arq in self.arquivos.values()})

    @property
    def sistemas(self) -> list[str]:
        """Lista ordenada de sistemas presentes na sessão."""
        return sorted({arq.sistema for arq in self.arquivos.values()})


def classificar_condicao(dados: dict[str, Any], *, permite_ponte: bool = True) -> str:
    """Determina a condição do arquivo ("A", "A_ponte", "B_padrao", "B_eq", "C")."""
    cenario = dados.get("cenario", "")
    pontos = dados.get("pontos", [])
    primeiro_ponto = pontos[0] if pontos else {}
    amb = primeiro_ponto.get("ambiente") or dados.get("ambiente") or {}

    if cenario == "A":
        if not permite_ponte:
            return "A"
        if amb.get("protocolo") == "sessao-2026-11":
            return "A"
        return "A_ponte"
    if cenario == "B":
        if amb.get("equalizado") is True:
            return "B_eq"
        return "B_padrao"
    if cenario == "C":
        return "C"
    return cenario


def carregar_sessao(
    results_dir: str | Path,
    marcos: str | Path | Sequence[dict[str, Any]],
) -> Sessao:
    """Lê marcos e indexa os arquivos JSON cujo timestamp cai na janela da sessão."""
    results_path = Path(results_dir)
    marcos_lista: list[dict[str, Any]] = []
    avisos: list[str] = []

    if isinstance(marcos, str | Path):
        p = Path(marcos)
        if p.is_dir():
            p = p / "marcos.jsonl"
        if not p.is_file():
            raise FileNotFoundError(f"Arquivo de marcos não encontrado: {p}")
        for idx_l, linha in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
            linha_s = linha.strip()
            if linha_s:
                try:
                    marcos_lista.append(json.loads(linha_s))
                except json.JSONDecodeError as e:
                    avisos.append(f"Linha {idx_l} corrompida ignorada em {p.name}: {e}")
    else:
        marcos_lista = list(marcos)

    if not marcos_lista:
        raise ValueError("Lista de marcos vazia — impossível determinar janela da sessão.")

    tempos = [normalizar_timestamp(m["ts_utc"]) for m in marcos_lista if "ts_utc" in m]
    if not tempos:
        raise ValueError("Nenhum marco possui campo 'ts_utc' válido.")

    t_inicio = min(tempos)
    t_fim = max(tempos)

    arquivos: dict[tuple[str, str, int], ArquivoSessao] = {}

    for caminho_json in sorted(results_path.glob("cenario_*.json")):
        try:
            dados = json.loads(caminho_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            avisos.append(
                f"Arquivo JSON corrompido ou ilegível ignorado: {caminho_json.name} ({e})"
            )
            continue

        ts_raw = dados.get("timestamp_utc")
        if not ts_raw:
            continue

        ts_dt = normalizar_timestamp(ts_raw)
        if not (t_inicio <= ts_dt <= t_fim):
            continue

        cenario = dados.get("cenario")
        sistema = dados.get("sistema", "").lower()
        n = dados.get("n")
        if not cenario or not sistema or n is None:
            continue

        condicao = classificar_condicao(dados, permite_ponte=True)
        chave = (condicao, sistema, int(n))
        novo = ArquivoSessao(
            caminho=caminho_json,
            cenario=cenario,
            sistema=sistema,
            n=int(n),
            condicao=condicao,
            timestamp_utc=ts_raw,
            dados=dados,
        )

        if chave in arquivos:
            antigo = arquivos[chave]
            ts_antigo = normalizar_timestamp(antigo.timestamp_utc)
            if ts_dt >= ts_antigo:
                avisos.append(
                    f"Chave {chave} repetida: usando {caminho_json.name} ({ts_raw}) "
                    f"e descartando {antigo.caminho.name} ({antigo.timestamp_utc})"
                )
                arquivos[chave] = novo
            else:
                avisos.append(
                    f"Chave {chave} repetida: mantendo {antigo.caminho.name} ({antigo.timestamp_utc}) "
                    f"e descartando mais antigo {caminho_json.name} ({ts_raw})"
                )
        else:
            arquivos[chave] = novo

    return Sessao(
        arquivos=arquivos,
        avisos=avisos,
        marcos=marcos_lista,
        inicio_utc=t_inicio.isoformat(),
        fim_utc=t_fim.isoformat(),
    )


def carregar_arquivos(
    paths: Sequence[str | Path] | str,
    *,
    eh_anterior: bool = True,
) -> Sessao:
    """Carrega arquivos específicos sem marcos (ex.: sessão anterior de 23/08)."""
    arquivos: dict[tuple[str, str, int], ArquivoSessao] = {}
    avisos: list[str] = []

    lista_paths: list[Path] = []
    if isinstance(paths, str):
        for pattern in paths.split():
            for m in glob.glob(pattern):
                lista_paths.append(Path(m))
    else:
        for item in paths:
            if isinstance(item, str) and ("*" in item or "?" in item):
                for m in glob.glob(item):
                    lista_paths.append(Path(m))
            else:
                lista_paths.append(Path(item))

    for p in sorted(lista_paths):
        if not p.is_file():
            continue
        try:
            dados = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            avisos.append(f"Arquivo JSON corrompido ou ilegível ignorado: {p.name} ({e})")
            continue

        cenario = dados.get("cenario")
        sistema = dados.get("sistema", "").lower()
        n = dados.get("n")
        ts_raw = dados.get("timestamp_utc", "")
        if not cenario or not sistema or n is None:
            continue

        condicao = classificar_condicao(dados, permite_ponte=not eh_anterior)
        chave = (condicao, sistema, int(n))
        novo = ArquivoSessao(
            caminho=p,
            cenario=cenario,
            sistema=sistema,
            n=int(n),
            condicao=condicao,
            timestamp_utc=ts_raw,
            dados=dados,
        )

        if chave in arquivos:
            antigo = arquivos[chave]
            ts_novo = normalizar_timestamp(ts_raw) if ts_raw else datetime.min.replace(tzinfo=UTC)
            ts_ant = (
                normalizar_timestamp(antigo.timestamp_utc)
                if antigo.timestamp_utc
                else datetime.min.replace(tzinfo=UTC)
            )
            if ts_novo >= ts_ant:
                avisos.append(
                    f"Chave {chave} repetida: usando {p.name} em vez de {antigo.caminho.name}"
                )
                arquivos[chave] = novo
        else:
            arquivos[chave] = novo

    return Sessao(arquivos=arquivos, avisos=avisos)
