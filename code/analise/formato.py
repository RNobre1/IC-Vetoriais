"""Formatação numérica no padrão brasileiro para tabelas e texto do relatório.

Em relatórios técnicos e acadêmicos em língua portuguesa, adota-se o ponto (.)
como separador de milhar e a vírgula (,) como separador decimal.

Arredondamento:
Utiliza-se o arredondamento comum de formatação de ponto flutuante do Python
(`format`), alinhado aos números apresentados nas tabelas preliminares do
relatório parcial (ex.: 1271.885 com 1 casa vira "1.271,9"). O arredondamento
bancário/half-even (típico de Decimal) não é aplicado aqui para preservar a
compatibilidade exata com as tabelas pré-existentes.

Valores ausentes (None) são representados convencionalmente por travessão ("---").
"""

from __future__ import annotations


def num(x: float | int | None, casas: int | None = None) -> str:
    """Formata número com separador de milhar '.' e decimal ','.

    Args:
        x: Valor numérico ou None.
        casas: Quantidade de casas decimais. Se None, inteiros não recebem
            casas decimais e floats recebem 2 casas por padrão.
            Se 0, arredonda para inteiro e omite a vírgula decimal.

    Returns:
        String formatada em padrão PT-BR ou "---" se x for None.
    """
    if x is None:
        return "---"

    if casas is None:
        if isinstance(x, int):
            return f"{x:,}".replace(",", ".")
        casas = 2

    if casas == 0:
        val = round(x)
        return f"{val:,}".replace(",", ".")

    texto = f"{x:,.{casas}f}"
    # Inverte vírgula e ponto via substituição intermediária
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def formato_escala(n: int) -> str:
    """Converte escala inteira (ex.: 100000, 1000000) em formato curto ("100k", "1M")."""
    if n >= 1_000_000 and n % 1_000_000 == 0:
        return f"{n // 1_000_000}M"
    if n >= 1_000 and n % 1_000 == 0:
        return f"{n // 1_000}k"
    return str(n)
