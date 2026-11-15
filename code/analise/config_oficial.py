"""Configuração canônica para geração dos artefatos oficiais do relatório.

Fonte única de verdade compartilhada entre o Makefile e o teste de frescor.
"""

from __future__ import annotations

from pathlib import Path

# Raiz do repositório (4 níveis acima de analise/config_oficial.py: code/analise -> code -> repo)
REPO_ROOT = Path(__file__).resolve().parents[2]

RESULTS_DIR = REPO_ROOT / "code" / "results"
# Sessão de medição vigente do relatório final (vide
# vault/decisões/2026-11-15-protocolo-da-sessao-final.md).
SESSAO_ID = "2026-11-15-final"
SESSAO_DIR = RESULTS_DIR / "sessoes" / SESSAO_ID
ANTERIOR_PATHS = str(RESULTS_DIR / "cenario_*_2026-08-23T*.json")
SAIDA_TABELAS = REPO_ROOT / "docx" / "relatorio_parcial" / "gerado"
SAIDA_FIGURAS = REPO_ROOT / "docx" / "relatorio_parcial" / "figuras"
