"""Testes unitários de formatação numérica no padrão brasileiro."""

from analise.formato import formato_escala, num


def test_num_trata_none_como_traco():
    assert num(None) == "---"
    assert num(None, 2) == "---"
    assert num(None, 0) == "---"


def test_num_valores_do_relatorio_parcial():
    # Valores literais citados no relatório parcial e na especificação
    assert num(1369.4, 1) == "1.369,4"
    assert num(0.90849, 4) == "0,9085"
    assert num(1271.885, 1) == "1.271,9"


def test_num_casas_zero_e_milhar():
    assert num(0, 0) == "0"
    assert num(1000, 0) == "1.000"
    assert num(1000000, 0) == "1.000.000"
    assert num(3709.2, 0) == "3.709"


def test_num_casas_decimais():
    assert num(0.5, 2) == "0,50"
    assert num(1.23456, 2) == "1,23"
    assert num(1.23556, 2) == "1,24"
    assert num(0.9996, 4) == "0,9996"
    assert num(1.0, 4) == "1,0000"


def test_num_inteiro_sem_casas():
    assert num(1000) == "1.000"
    assert num(42) == "42"


def test_num_negativo():
    assert num(-1234.5, 1) == "-1.234,5"


def test_formato_escala():
    assert formato_escala(5000) == "5k"
    assert formato_escala(100000) == "100k"
    assert formato_escala(500000) == "500k"
    assert formato_escala(1000000) == "1M"
