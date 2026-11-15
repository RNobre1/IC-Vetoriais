"""Configuração canônica para geração dos artefatos oficiais do relatório.

Fonte única de verdade compartilhada entre o Makefile e o teste de frescor.
"""

from __future__ import annotations

from pathlib import Path

# Raiz do repositório (4 níveis acima de analise/config_oficial.py: code/analise -> code -> repo)
REPO_ROOT = Path(__file__).resolve().parents[2]

RESULTS_DIR = REPO_ROOT / "code" / "results"
# Sessão oficial atual (substituível quando houver sessão completa)
SESSAO_DIR = RESULTS_DIR / "sessoes" / "oficial"
ANTERIOR_PATHS = str(RESULTS_DIR / "cenario_*_2026-08-23T*.json")
SAIDA_TABELAS = REPO_ROOT / "docx" / "relatorio_parcial" / "gerado"
SAIDA_FIGURAS = REPO_ROOT / "docx" / "relatorio_parcial" / "figuras"
