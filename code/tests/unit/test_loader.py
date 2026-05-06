"""Testes do `pipeline.ms_marco_loader` (TDD — escritos antes da implementação).

Cobre:
- Constantes (URL e MD5) baseadas no header Content-MD5 do servidor MS MARCO em 2026-05-06.
- Sampling determinístico por ordem de `passage_id` (top-N).
- Robustez a passages com tabs no texto.
- Lógica de skip-download quando o arquivo já existe e MD5 bate (sem tocar rede).

Os testes que envolveriam o tarball real (~1 GB) são marcados como `slow` e ficam fora
do alvo padrão `make test-unit` para manter o feedback rápido.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pipeline.ms_marco_loader import (
    COLLECTION_MD5,
    COLLECTION_URL,
    Passage,
    download_collection_targz,
    sample_passages,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------


def test_url_aponta_para_msmarco_oficial() -> None:
    assert COLLECTION_URL.startswith("https://msmarco.")
    assert COLLECTION_URL.endswith("collection.tar.gz")


def test_md5_constante_correta() -> None:
    """MD5 oficial do header `Content-MD5` em base64 = `h90Bgm2j4q1FRHulr1d2KA==`.

    Decodificado para hex em 2026-05-06; ver vault/sessões/2026-05-06.md.
    """
    assert COLLECTION_MD5 == "87dd01826da3e2ad45447ba5af577628"


# ---------------------------------------------------------------------------
# Passage
# ---------------------------------------------------------------------------


def test_passage_dataclass_imutavel() -> None:
    p = Passage(id=42, text="Lorem ipsum")
    assert p.id == 42
    assert p.text == "Lorem ipsum"
    # `frozen=True` no dataclass torna a instância imutável.
    with pytest.raises((AttributeError, Exception)):
        p.id = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# sample_passages
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_tsv(tmp_path: Path) -> Path:
    """TSV pequeno no formato MS MARCO (`<id>\\t<text>`), IDs ordenados 0..9."""
    f = tmp_path / "collection.tsv"
    linhas = [f"{i}\tpassage_{i}_text" for i in range(10)]
    f.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return f


def test_sample_passages_tamanho_exato(mock_tsv: Path) -> None:
    assert len(sample_passages(mock_tsv, n=5)) == 5


def test_sample_passages_determinismo(mock_tsv: Path) -> None:
    a = sample_passages(mock_tsv, n=5)
    b = sample_passages(mock_tsv, n=5)
    assert [(p.id, p.text) for p in a] == [(p.id, p.text) for p in b]


def test_sample_passages_ids_distintos(mock_tsv: Path) -> None:
    out = sample_passages(mock_tsv, n=10)
    ids = [p.id for p in out]
    assert len(ids) == len(set(ids))


def test_sample_passages_top_n_por_id(mock_tsv: Path) -> None:
    """Sampling determinístico = primeiras N linhas em ordem ascendente de passage_id."""
    out = sample_passages(mock_tsv, n=3)
    assert [p.id for p in out] == [0, 1, 2]


def test_sample_passages_le_texto_corretamente(mock_tsv: Path) -> None:
    out = sample_passages(mock_tsv, n=2)
    assert out[0].text == "passage_0_text"
    assert out[1].text == "passage_1_text"


def test_sample_passages_robusto_a_tabs_no_texto(tmp_path: Path) -> None:
    """Se o text contém TAB, mantém TUDO após o primeiro TAB como text inteiro.

    Algumas passages do MS MARCO contêm tabs internos; dividir em mais que 2 campos
    perderia conteúdo silenciosamente — bug clássico que TDD precisa cobrir.
    """
    f = tmp_path / "tab.tsv"
    f.write_text("0\tword1\tword2\tword3\n", encoding="utf-8")
    out = sample_passages(f, n=1)
    assert out[0].id == 0
    assert out[0].text == "word1\tword2\tword3"


def test_sample_passages_n_excessivo_levanta(mock_tsv: Path) -> None:
    with pytest.raises(ValueError, match="(excede|disponíveis|disponiveis)"):
        sample_passages(mock_tsv, n=10_000)


def test_sample_passages_n_zero_ou_negativo_levanta(mock_tsv: Path) -> None:
    with pytest.raises(ValueError, match="positivo"):
        sample_passages(mock_tsv, n=0)
    with pytest.raises(ValueError, match="positivo"):
        sample_passages(mock_tsv, n=-1)


def test_sample_passages_arquivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        sample_passages(tmp_path / "nao-existe.tsv", n=1)


def test_sample_passages_robusto_a_linhas_em_branco(tmp_path: Path) -> None:
    """Linhas em branco no TSV não devem virar Passage(id=??, text='')."""
    f = tmp_path / "blanks.tsv"
    f.write_text("0\ttexto_a\n\n1\ttexto_b\n   \n2\ttexto_c\n", encoding="utf-8")
    out = sample_passages(f, n=3)
    assert [p.id for p in out] == [0, 1, 2]
    assert [p.text for p in out] == ["texto_a", "texto_b", "texto_c"]


# ---------------------------------------------------------------------------
# download_collection_targz — só lógica de skip; rede mocada
# ---------------------------------------------------------------------------


def test_download_pula_se_arquivo_existe_e_md5_correto(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Se o tar já existe localmente e o MD5 bate, não toca a rede."""
    from pipeline import ms_marco_loader as loader

    conteudo = b"conteudo qualquer pra simular tar"
    fake_tar = tmp_path / "collection.tar.gz"
    fake_tar.write_bytes(conteudo)

    monkeypatch.setattr(loader, "COLLECTION_MD5", hashlib.md5(conteudo).hexdigest())

    def boom(*_a: object, **_kw: object) -> None:
        raise AssertionError("rede não deve ser chamada quando tar local com MD5 correto existe")

    monkeypatch.setattr(loader, "_baixar_url", boom)

    resultado = download_collection_targz(tmp_path, force=False)
    assert resultado == fake_tar


def test_download_rebaixa_se_md5_local_diverge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Se já existe um tar mas MD5 não bate (download corrompido), rebaixa."""
    from pipeline import ms_marco_loader as loader

    fake_tar = tmp_path / "collection.tar.gz"
    fake_tar.write_bytes(b"conteudo corrompido")

    chamadas: list[tuple[str, Path]] = []

    def fake_baixar(url: str, destino: Path) -> None:
        chamadas.append((url, destino))
        destino.write_bytes(b"conteudo correto")

    monkeypatch.setattr(loader, "_baixar_url", fake_baixar)
    monkeypatch.setattr(loader, "COLLECTION_MD5", hashlib.md5(b"conteudo correto").hexdigest())

    resultado = download_collection_targz(tmp_path, force=False)
    assert len(chamadas) == 1
    assert resultado == fake_tar
    assert fake_tar.read_bytes() == b"conteudo correto"


def test_download_force_rebaixa_mesmo_com_md5_correto(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`force=True` força redownload mesmo se o MD5 local bate."""
    from pipeline import ms_marco_loader as loader

    conteudo = b"conteudo correto"
    fake_tar = tmp_path / "collection.tar.gz"
    fake_tar.write_bytes(conteudo)
    monkeypatch.setattr(loader, "COLLECTION_MD5", hashlib.md5(conteudo).hexdigest())

    chamou = {"n": 0}

    def fake_baixar(url: str, destino: Path) -> None:
        chamou["n"] += 1
        destino.write_bytes(conteudo)

    monkeypatch.setattr(loader, "_baixar_url", fake_baixar)
    download_collection_targz(tmp_path, force=True)
    assert chamou["n"] == 1


def test_download_md5_pos_download_diverge_levanta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Se baixa e o MD5 não bate, levanta erro claro."""
    from pipeline import ms_marco_loader as loader

    def fake_baixar(url: str, destino: Path) -> None:
        destino.write_bytes(b"conteudo errado")

    monkeypatch.setattr(loader, "_baixar_url", fake_baixar)
    monkeypatch.setattr(loader, "COLLECTION_MD5", "0" * 32)

    with pytest.raises(ValueError, match="MD5"):
        download_collection_targz(tmp_path, force=True)
