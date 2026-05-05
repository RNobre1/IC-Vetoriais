---
tipo: decisão
data: 2026-04-28
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [metodologia, embeddings, modelo]
---

# Modelo de embedding: sentence-transformers/all-MiniLM-L6-v2 (384 dim)

## Contexto
A geração dos embeddings é a primeira etapa do pipeline e precisa rodar de ponta a ponta no hardware-alvo (notebook Dell G15: i5-13450HX, 16 GiB DDR5, RTX 3050 6 GB). Modelos maiores (e.g. mpnet-base 768 dim, BGE-large 1024 dim) elevam custo de geração, dimensionalidade e RAM dos índices, sem ganho proporcional para a pergunta deste estudo (que é sobre os SGBDs vetoriais, não sobre qualidade do embedding).

## Opções consideradas
1. **all-MiniLM-L6-v2** (384 dim) — escolhida
   - Prós: 22M parâmetros, roda em CPU em poucos minutos para 1M de passages. Permite reprodução sem GPU. Amplamente usado como baseline na literatura recente (Reimers & Gurevych, 2019; Pawlik, 2024).
   - Contras: qualidade de retrieval inferior a modelos maiores.
2. **all-mpnet-base-v2** (768 dim)
   - Prós: melhor qualidade de retrieval (~3-5% recall@10 a mais em MS MARCO).
   - Contras: ~2x dimensão → 2x memória do índice; ~3x tempo de geração. RTX 3050 com 6 GB já fica apertada para batches grandes em fp16.
3. **BGE-large-en-v1.5** (1024 dim)
   - Prós: estado da arte open-weight em retrieval inglês.
   - Contras: 335M parâmetros. Geração de 1M passages no hardware disponível leva horas. Aumenta complexidade sem responder à pergunta da IC.

## Decisão
**Escolhida:** opção 1 — `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensões.

## Justificativa
- Pergunta da IC é sobre **comportamento dos SGBDs**, não sobre qualidade absoluta do retrieval. O modelo precisa apenas produzir embeddings densos válidos e reproduzíveis.
- 384 dimensões são suficientes para diferenciar HNSW efetivo de busca exata em curvas recall × QPS. ANN-Benchmarks usa modelos de dimensão similar (e até menor) sem prejuízo da metodologia.
- Reprodutibilidade no hardware do bolsista: um terceiro com notebook qualquer consegue replicar a geração sem GPU.
- Modelo é determinístico dada a versão dos pesos (vamos pinar versão exata em `requirements.txt`).

## Consequência
- Todos os experimentos usam vetores de 384 dim, normalizados (cosseno).
- Distância: cosseno (equivalente a dot-product após normalização L2).
- O **modelo não é variável independente** da IC. Não vamos comparar MiniLM vs. mpnet — isso seria outra pesquisa.
- Tempo de geração entra como métrica de "tempo de indexação inicial" no relatório.

## Critério de revisão
Reabrir se: (a) recall@10 com MiniLM ficar abaixo de ~0.6 em busca exata para MS MARCO subset (sinal de que o modelo não consegue separar os documentos do dataset), ou (b) o orientador requisitar comparação entre modelos para o relatório final.

## Backlinks
- [[papers/Reimers-Gurevych-2019-Sentence-BERT]]
- [[papers/Pawlik-2025-LLM-Selection-Vector-DB-Tuning]]
- [[referência/embeddings-densos]]
