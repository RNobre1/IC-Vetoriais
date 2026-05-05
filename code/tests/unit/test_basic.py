"""Smoke unitário do Dia 1 — mantém o pipeline de CI vivo enquanto módulos reais não existem.

Substituir por testes unitários reais conforme `pipeline/`, `lib/`, `ground_truth/` forem implementados nos Dias 2–4.
"""

import sys


def test_python_minimo():
    """Garante que rodamos em Python ≥ 3.11 (target_version do ruff e da CI)."""
    assert sys.version_info >= (3, 11)


def test_ambiente_basico():
    """Smoke unitário: ambiente Python responde, aritmética funciona."""
    assert 1 + 1 == 2
