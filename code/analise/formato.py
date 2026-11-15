"""Formatação numérica no padrão brasileiro para tabelas e texto do relatório.

Em relatórios técnicos e acadêmicos em língua portuguesa, adota-se o ponto (.)
como separador de milhar e a vírgula (,) como separador decimal.

Arredondamento:
Utiliza-se arredondamento aritmético simétrico / half-up (`ROUND_HALF_UP` do módulo
`decimal`), onde frações 0,5 arredondam para cima (afastando-se de zero).
Zeros negativos (ex.: -0,00001 arredondado para 2 casas) são explicitamente
normalizados para "0,00" para evitar a exibição de "-0,0" ou "-0,0000".

Valores ausentes (None) são representados convencionalmente por travessão ("---").
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def num(x: float | int | Decimal | None, casas: int | None = None) -> str:
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
            d = Decimal(x)
            return f"{d:,}".replace(",", ".")
        casas = 2

    # Converte para Decimal preservando representação exata
    d = Decimal(str(x)) if not isinstance(x, Decimal) else x
    q = Decimal("10") ** -casas if casas > 0 else Decimal("1")
    arredondado = d.quantize(q, rounding=ROUND_HALF_UP)

    # Evita zero negativo
    if arredondado == 0:
        arredondado = Decimal("0")

    if casas == 0:
        val_int = int(arredondado)
        return f"{val_int:,}".replace(",", ".")

    texto = f"{arredondado:,.{casas}f}"
    # Inverte vírgula e ponto via substituição intermediária
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def formato_escala(n: int) -> str:
    """Converte escala inteira (ex.: 100000, 1000000) em formato curto ("100k", "1M")."""
    if n >= 1_000_000 and n % 1_000_000 == 0:
        return f"{n // 1_000_000}M"
    if n >= 1_000 and n % 1_000 == 0:
        return f"{n // 1_000}k"
    return str(n)
