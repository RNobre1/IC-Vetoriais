---
tipo: referência
conceito: "Embeddings densos"
tags: [embeddings, deep-learning, sentence-transformers]
---

# Embeddings densos

## Definição
Representações vetoriais de baixa dimensionalidade (tipicamente 128–1024) aprendidas por modelos neurais. Cada coordenada é um valor real (denso), e a proximidade no espaço captura **similaridade semântica** — frases com significado próximo ficam próximas geometricamente, mesmo sem compartilhar tokens superficiais.

## Formalização
Um modelo de embedding é uma função f: T → ℝᵈ, com T = conjunto de textos de entrada e d = dimensão fixa. Para um corpus C = {x₁, ..., xₙ}, o conjunto de embeddings é E = {f(x₁), ..., f(xₙ)} ⊂ ℝᵈ.

Similaridade típica é o cosseno (após normalização L2, equivale a produto interno):

sim(x, y) = (f(x) · f(y)) / (‖f(x)‖ · ‖f(y)‖)

Treinamento: tipicamente contrastivo. Pares positivos (x, x⁺) são puxados; pares negativos (x, x⁻) são afastados — frequentemente com perda InfoNCE ou Multiple Negatives Ranking.

## Variantes
- **Word embeddings estáticos:** Word2Vec (Mikolov et al., 2013), GloVe — um vetor por palavra, sem contexto.
- **Embeddings contextuais:** BERT, RoBERTa — embeddings de tokens dependentes do contexto da frase.
- **Sentence embeddings:** Sentence-BERT (Reimers & Gurevych, 2019) — embeddings de frases/passages com pooling treinado especificamente para tarefas de similaridade.
- **Cross-encoder vs. bi-encoder:** cross-encoder processa par (q, d) e retorna um score conjunto (alta qualidade, não escalável); bi-encoder produz f(q) e f(d) independentes (escalável para retrieval em larga escala).

## Onde aparece neste estudo
Seção §3.2. O modelo escolhido é `sentence-transformers/all-MiniLM-L6-v2` (384 dim) — ver [[decisões/2026-04-28-modelo-embedding-minilm]]. Embeddings são o **insumo** dos três sistemas avaliados; a IC mede como cada SGBD lida com esse insumo, não como o modelo é construído.

## Papers canônicos
- [[papers/Reimers-Gurevych-2019-Sentence-BERT]]

## Pegadinhas
- Modelos de embedding são **caros para gerar** (uma passada do encoder por texto); são **rápidos para consultar** se já estiverem em memória.
- Normalização L2 antes de indexar permite usar produto interno como proxy de cosseno (mais rápido).
- Dimensão fixa (não depende do tamanho do vocabulário). Mas ainda assim, "alta dimensionalidade" para fins de indexação — a maldição da dimensionalidade afeta busca exata mesmo em 384 dim.
- Modelos diferentes produzem embeddings em **espaços incompatíveis**: f_A(x) e f_B(x) não são comparáveis. **Não misturar embeddings de modelos diferentes na mesma coleção.**
- Truncar dimensões ad hoc (e.g. usar só as primeiras 128 de um modelo de 384) **não funciona** sem treinamento Matryoshka específico.
