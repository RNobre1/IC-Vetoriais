"""Cenário C — carga mista RAG (**esqueleto**; execução real na Etapa 4).

Objetivo (Etapa 4): medir o impacto da **taxa de inserção concorrente**
(0, 10, 100, 1000 ins/s) sobre a latência p99 de *leitura* — um produtor
insere vetores enquanto um consumidor faz buscas, simulando um índice vetorial
sob escrita contínua num pipeline RAG.

Por que só esqueleto agora: o Cenário C pressupõe escala de 1M
([[../../vault/decisões/2026-04-28-tamanhos-100k-500k-1m]]); rodá-lo no
notebook-alvo com os 3 SGBDs simultâneos estoura RAM (risco 1 do plano da
Etapa 2). A estrutura nasce aqui, em TDD, para a Etapa 4 só preencher o
produtor/consumidor — sem rodar carga real nesta etapa (`executar` recusa).

Decisões herdadas: queries held-out / warmup
([[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]]).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

TAXAS_INSERCAO_PADRAO = [0, 10, 100, 1000]  # inserções por segundo


@dataclass(frozen=True, slots=True)
class ConfigC:
    """Configuração do Cenário C. Campos estáveis; corpo do run vem na Etapa 4."""

    n_base: int = 500_000
    n_queries: int = 1_000
    k: int = 10
    taxas_insercao: list[int] = field(default_factory=lambda: list(TAXAS_INSERCAO_PADRAO))
    duracao_s: int = 60
    sistemas: list[str] = field(default_factory=lambda: ["pgvector", "qdrant", "weaviate"])


def intervalo_entre_insercoes(taxa_ins_por_s: float) -> float:
    """Segundos entre inserções consecutivas para uma `taxa` (ins/s).

    `taxa == 0` ⇒ leitura pura (baseline), intervalo `inf` (nenhuma inserção).
    `taxa > 0` ⇒ `1 / taxa`. `taxa < 0` é inválida.

    Lógica pura do escalonamento do produtor — testável sem Docker, reusável
    pelo run real da Etapa 4.
    """
    if taxa_ins_por_s < 0:
        raise ValueError(f"taxa inválida: {taxa_ins_por_s} (esperado >= 0).")
    if taxa_ins_por_s == 0:
        return math.inf
    return 1.0 / taxa_ins_por_s


def executar(cfg: ConfigC) -> list:
    """Ponto de entrada do Cenário C — **não implementado nesta etapa**.

    O produtor concorrente de inserções + consumidor de buscas e a medição
    de p99 de leitura sob carga serão escritos na Etapa 4 (escala de 1M),
    reusando `intervalo_entre_insercoes`, os adaptadores `BuscadorVetorial`
    e o `lib.reporting`. Recusa rodar carga real agora por restrição de
    hardware (risco 1 do plano da Etapa 2).
    """
    raise NotImplementedError(
        "Cenário C (carga mista RAG) roda na Etapa 4 — esqueleto apenas na "
        "Etapa 2. Vide benchmarks/cenario_c.py e o plano da Etapa 2."
    )
