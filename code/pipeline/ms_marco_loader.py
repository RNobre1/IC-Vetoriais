"""Loader determinístico de MS MARCO Passages.

Responsabilidades:
- Baixar `collection.tar.gz` (~1 GB) sob demanda, validando MD5.
- Lê o TSV resultante (ou um path arbitrário no mesmo formato) e produz subsets
  determinísticos por ordem ascendente de `passage_id` (top-N).

Justificativa do sampling top-N:
- O TSV oficial do MS MARCO Passages já vem ordenado por `passage_id` (0..N-1).
- Top-N é trivialmente reproduzível, hashable e independente de seed de RNG.
- Vide vault/decisões/2026-04-28-dataset-ms-marco.md.
"""

from __future__ import annotations

import hashlib
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# URL canônica em 2026-05-06 (header Content-MD5 do servidor consultado).
COLLECTION_URL = "https://msmarco.z22.web.core.windows.net/msmarcoranking/collection.tar.gz"
COLLECTION_MD5 = "87dd01826da3e2ad45447ba5af577628"

# Tamanho de leitura para o cálculo incremental de MD5.
_CHUNK_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class Passage:
    """Uma passage do MS MARCO: identificador inteiro e texto bruto."""

    id: int
    text: str


# ---------------------------------------------------------------------------
# Helpers (pequenos para serem mockáveis em testes)
# ---------------------------------------------------------------------------


def _md5_arquivo(path: Path) -> str:
    """MD5 hex de um arquivo, lido em chunks (arquivos de 1 GB+ não cabem na RAM)."""
    h = hashlib.md5()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK_BYTES):
            h.update(chunk)
    return h.hexdigest()


def _baixar_url(url: str, destino: Path) -> None:
    """Download HTTP/HTTPS direto para `destino`. Mockado em testes."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, destino)  # noqa: S310 — URL canônica fixada em constante


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def download_collection_targz(dest_dir: Path, *, force: bool = False) -> Path:
    """Garante que `dest_dir/collection.tar.gz` exista e tenha o MD5 esperado.

    - Se o arquivo já existe e o MD5 bate: retorna sem tocar a rede.
    - Se existe mas o MD5 diverge (download corrompido): rebaixa.
    - `force=True`: ignora cache local e rebaixa.
    - Após qualquer download, valida MD5; se não bater, levanta `ValueError`.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    alvo = dest_dir / "collection.tar.gz"

    if alvo.exists() and not force and _md5_arquivo(alvo) == COLLECTION_MD5:
        return alvo

    _baixar_url(COLLECTION_URL, alvo)

    md5_obtido = _md5_arquivo(alvo)
    if md5_obtido != COLLECTION_MD5:
        raise ValueError(
            f"MD5 do {alvo.name} pós-download diverge do esperado: "
            f"obtido={md5_obtido} esperado={COLLECTION_MD5}"
        )
    return alvo


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


def sample_passages(tsv_path: Path, n: int) -> list[Passage]:
    """Top-N passages por ordem ascendente de `passage_id` (que é a ordem do arquivo)."""
    if n <= 0:
        raise ValueError(f"n deve ser positivo, recebido: {n}")
    if not tsv_path.exists():
        raise FileNotFoundError(tsv_path)

    coletados: list[Passage] = []
    with tsv_path.open("r", encoding="utf-8") as fh:
        for linha in fh:
            stripped = linha.rstrip("\n").rstrip("\r")
            if not stripped.strip():
                continue
            # `split("\t", 1)` mantém qualquer TAB interno do texto preservado.
            campos = stripped.split("\t", 1)
            if len(campos) != 2:
                continue
            id_str, texto = campos
            try:
                pid = int(id_str)
            except ValueError:
                continue
            coletados.append(Passage(id=pid, text=texto))
            if len(coletados) >= n:
                return coletados

    if len(coletados) < n:
        raise ValueError(f"n={n} excede passages disponíveis ({len(coletados)}) em {tsv_path}")
    return coletados
