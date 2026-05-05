---
tipo: paper
autores: ["Reimers, N.", "Gurevych, I."]
ano: 2019
titulo: "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks"
venue: "EMNLP-IJCNLP 2019"
tags: [embeddings, sentence-transformers, siamese, bert, foundational]
citacao_abnt: "REIMERS, N.; GUREVYCH, I. Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In: Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing (EMNLP), 2019."
arquivo_local: ""
---

# Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks

> **Status do fichamento:** PDF **não disponível localmente** em `vault/papers/`. Preenchido a partir de conhecimento difundido (a biblioteca `sentence-transformers` deriva diretamente deste paper). Baixar PDF (acesso aberto via ACL Anthology) e revisar antes de citar no relatório final.

## Síntese
Paper que adapta o BERT para produzir **embeddings de frase úteis para similaridade**. O BERT padrão produz embeddings de tokens excelentes para classificação supervisionada, mas é inadequado para retrieval em larga escala porque exige processar pares (q, d) pelo cross-encoder a cada consulta — O(N) avaliações por query, inviável. Sentence-BERT resolve isso com uma rede **siamese**: duas torres BERT compartilhando pesos, treinadas para que o cosseno entre embeddings de frases similares seja alto. Resultado: embeddings reusáveis, indexáveis, e a base prática de toda a família `sentence-transformers/*` usada na indústria.

## Contribuições
- Arquitetura siamese BERT com pooling (mean, max, ou CLS) para gerar um vetor por frase.
- Loss functions específicas para tarefas de similaridade: classification (NLI), regression (STS), triplet (MNR).
- Demonstração de qualidade competitiva com BERT cross-encoder em STS, com **redução drástica do custo de inferência** ao operar como bi-encoder.
- Disponibilização da biblioteca `sentence-transformers` que se tornou padrão de fato.

## Método
- Treinamento em dois estágios: (1) NLI (SNLI + MultiNLI) com classification loss, (2) STSb com regression loss para fine-tuning final.
- Pooling: experimentalmente, mean pooling supera CLS e max para a maioria das tarefas.
- Avaliação em 7 benchmarks STS, SentEval e Argument Facet Similarity.

## Resultados-chave
- Sentence-BERT supera GloVe, InferSent e Universal Sentence Encoder em correlação Spearman em STS.
- Cosseno entre embeddings de frases passa a ter significado semântico calibrado.
- Custo de retrieval cai de O(N) avaliações de cross-encoder para O(N) cosines pré-computáveis (ou O(log N) com ANN).

## Limitações
- Treinamento original em inglês; modelos multilíngues vêm de fine-tuning posterior (paraphrase-multilingual-MiniLM, etc.).
- Qualidade depende da tarefa: bi-encoders perdem para cross-encoders em re-ranking de top-K.
- Truncamento por comprimento máximo do BERT (~512 tokens) — passages longos precisam de chunking.

## Relevância para a IC
**Sustenta §3.2 do relatório parcial** ([[referência/embeddings-densos]]) e a [[decisões/2026-04-28-modelo-embedding-minilm|escolha do modelo all-MiniLM-L6-v2]] (que é uma destilação do Sentence-BERT em uma rede menor). Sem este paper, não haveria a biblioteca que viabiliza o pipeline desta IC com custo computacional realista no hardware disponível.

## Citáveis
> *[Citar a definição de bi-encoder vs. cross-encoder e a justificativa de custo computacional para escolher bi-encoders em retrieval.]*

## Backlinks
- [[referência/embeddings-densos]]
- [[decisões/2026-04-28-modelo-embedding-minilm]]
- [[papers/Lewis-2020-RAG]]
