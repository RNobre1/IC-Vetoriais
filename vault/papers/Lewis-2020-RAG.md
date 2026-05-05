---
tipo: paper
autores: ["Lewis, P.", "Perez, E.", "Piktus, A.", "Petroni, F.", "Karpukhin, V.", "Goyal, N.", "Küttler, H.", "Lewis, M.", "Yih, W.", "Rocktäschel, T.", "Riedel, S.", "Kiela, D."]
ano: 2020
titulo: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
venue: "Advances in Neural Information Processing Systems (NeurIPS)"
tags: [rag, llm, retrieval, generation, foundational]
citacao_abnt: "LEWIS, P. et al. Retrieval-augmented generation for knowledge-intensive NLP tasks. In: Advances in Neural Information Processing Systems 33 (NeurIPS 2020), 2020. p. 9459–9474."
arquivo_local: "Retrieval-Augmented Generation for_Knowledge-Intensive NLP Tasks.pdf"
---

# Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

> **Status do fichamento:** preenchido a partir de conhecimento prévio + título e citação. Verificar números (datasets, métricas) contra o PDF.

## Síntese
Paper que introduz **RAG (Retrieval-Augmented Generation)** como arquitetura híbrida combinando um recuperador denso (DPR) com um gerador seq2seq (BART). O modelo trata o índice de embeddings como uma "memória externa" diferenciável, permitindo que o gerador condicione cada resposta em passages recuperados em tempo de inferência. Estabelece a base conceitual sobre a qual sistemas RAG modernos (incluindo a motivação aplicada desta IC) operam.

## Contribuições
- Arquitetura unificada que combina retrieval denso + geração com modelo BART.
- Duas variantes do gerador: **RAG-Sequence** (mesma evidência condiciona toda a resposta) e **RAG-Token** (a evidência pode mudar token a token).
- Treinamento end-to-end onde o retriever é fine-tunado conjuntamente com o gerador.
- Demonstração empírica de superioridade sobre baselines paramétricos puros em tarefas knowledge-intensive.

## Método
- **Retriever:** DPR (Dense Passage Retrieval) com índice FAISS sobre embeddings de Wikipedia.
- **Gerador:** BART-large pré-treinado, fine-tunado com o sinal de geração.
- **Tarefas avaliadas:** Open-domain QA (Natural Questions, TriviaQA, WebQuestions, CuratedTrec), Jeopardy question generation, abstractive QA, fact verification (FEVER).
- **Top-K:** tipicamente K=5 a 10 passages recuperados por query.

*[Detalhar hiperparâmetros, dimensão dos embeddings DPR, tamanho do índice — verificar no PDF.]*

## Resultados-chave
- Estado da arte em várias tarefas de Open-domain QA na época.
- RAG-Token superior a RAG-Sequence quando a resposta combina informações de múltiplos passages.
- *[Números específicos — extrair do PDF.]*

## Limitações
- Wikipedia como única fonte de conhecimento.
- Custo computacional do retrieval em tempo de inferência (acesso a um índice de milhões de passages).
- Performance dependente da qualidade do retriever (DPR) — gargalo de upstream.

## Relevância para a IC
**Sustenta §3.5 do relatório parcial** — paper canônico para definir RAG. É a **motivação aplicada principal** da IC: a busca vetorial em produção é o componente cuja latência e throughput este estudo mede. O **Cenário C** ([[decisões/2026-04-28-cenarios-A-B-C]]) simula carga RAG mista (busca concorrente com inserção), inspirado no comportamento descrito por Lewis et al.

## Citáveis
> *[Selecionar frase definindo RAG e relação retriever-gerador para citar em §3.5.]*

## Backlinks
- [[referência/rag-retrieval-augmented-generation]]
- [[papers/Bovas-2025-Navi-RAG-Chatbot]]
- [[papers/Pawlik-2025-LLM-Selection-Vector-DB-Tuning]]
