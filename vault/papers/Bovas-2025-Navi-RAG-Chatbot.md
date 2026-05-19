---
tipo: paper
autores: ["Bovas, A. P.", "Joy, M.", "Santo, N. C.", "Borde, S. R.", "Deshpande, V. V."]
ano: 2025
titulo: "Navi: RAG-Powered LLM Chatbot for Academic Institutions"
venue: "International Journal for Research in Applied Science and Engineering Technology (IJRASET), v. 13, n. 11"
tags: [rag, aplicação, chatbot, educação, minilm, faiss]
citacao_abnt: "BOVAS, A. P. et al. Navi: RAG-powered LLM chatbot for academic institutions. International Journal for Research in Applied Science and Engineering Technology, v. 13, n. 11, p. 2339-2346, nov. 2025. DOI: 10.22214/ijraset.2025.75655."
arquivo_local: "Navi_ RAG-Powered LLM Chatbot for Academic_Institutions.pdf"
---

# Navi: RAG-Powered LLM Chatbot for Academic Institutions

> **Status do fichamento:** **verificado contra o PDF** em 2026-05-20 (leitura integral das 9 páginas). Números e fatos abaixo conferem com o texto-fonte. Ressalva registrada na seção Limitações sobre inconsistências internas do próprio paper entre tabelas.

## Síntese
Apresenta o *Navi*, assistente virtual acadêmico que combina um LLM (Mistral-7B-Instruct) com pipeline RAG sobre uma base vetorial FAISS, para responder consultas institucionais (admissão, currículo, docentes, administrativo) de forma factual e com baixa alucinação. Avaliação por consultas simuladas indica *relevance score* médio entre 0,7 e 0,85.

## Contribuições
- Arquitetura RAG aplicada a domínio acadêmico, ponta-a-ponta (ingestão → *chunking* → *embedding* → FAISS → recuperação top-k → LLM).
- Evidência empírica de que RAG sobre LLM reduz alucinação e eleva relevância/satisfação versus LLM puro, em ambiente **CPU-only**.

## Método
- **Embedding:** `all-MiniLM-L6-v2` (Sentence-Transformers, via Hugging Face) — **o mesmo modelo desta IC**.
- **Banco vetorial:** FAISS (não usa pgvector/Qdrant/Weaviate). LLM gerador: Mistral-7B-Instruct; backend Flask.
- **Chunking:** segmentos de ~500–800 tokens, com id único por chunk.
- **Recuperação:** top-k com **k=5**; query e documentos no mesmo espaço de embedding.
- **Avaliação:** sessões simuladas; relevância pontuada em escala 0–1 sobre 100 consultas diversas (Results menciona também conjunto de 500 consultas de domínio); métricas: retrieval accuracy, response relevance, informativeness, latência, taxa de alucinação.

## Resultados-chave
- **Relevance score médio entre 0,7 e 0,85** (afirmado no resumo, na introdução e em §III.G; tabela de Resultados: Response Score (0–1) — mín. 0,70; máx. 0,85; **média 0,78**). **É o número citado no relatório parcial (§1.1 e §3.5).**
- Retrieval accuracy sobe de ~78% (LLM puro) para ~92% (RAG completo) na Figura 1; tabela resumo reporta média 79,2% (mín. 68 / máx. 88) — ver ressalva.
- Taxa de alucinação cai de 41,0% (LLM puro) para 22,5% (LLM+RAG).
- Satisfação do usuário sobe de 3,2 para 4,4 (escala /5); relevância média 3,8→4,6 numa Likert 5 pontos.

## Limitações
- **Do sistema (paper):** acurácia depende da cobertura/atualidade da base; consultas fora do escopo geram respostas de baixa confiança; *deployment* CPU-only limita velocidade.
- **Do paper (registro crítico — rigor):** há **inconsistências internas** entre tabelas — a "Average Relevance Score" aparece como 0,61→0,78 numa tabela e como 0,70/0,85/0,78 (mín/máx/média) noutra; "Average Retrieval Accuracy" aparece como 79,2 e como 92%. O intervalo **0,7–0,85** que usamos é o único valor reportado de forma **consistente** (resumo, introdução, §III.G e tabela mín/máx) — por isso é seguro citá-lo; não citar os números conflitantes sem ressalva.

## Relevância para a IC
**Sustenta §1.1 (Contexto) e §3.5 (RAG)** do relatório parcial — exemplo concreto de aplicação RAG em contexto acadêmico análogo, com *relevance score* 0,7–0,85, reforçando a motivação prática da IC. Reforço extra: o Navi usa **o mesmo embedding (`all-MiniLM-L6-v2`) em CPU** que esta IC, corroborando a decisão [[decisões/2026-04-28-modelo-embedding-minilm]]. Contraponto útil: o Navi usa FAISS (busca exata/biblioteca), não um SGBD vetorial — exatamente a lacuna que esta IC investiga ([[decisões/2026-04-28-cenarios-A-B-C|cenários A, B, C]]).

## Citáveis
> "Performance evaluation through simulated academic queries indicates improved response accuracy, coherence, and informativeness, achieving an average relevance score between 0.7–0.85." (Resumo)
> "Each response was scored on a 0–1 scale for relevance across 100 diverse test queries, producing an average score between 0.7 and 0.85." (§III.G)

## Backlinks
- [[referência/rag-retrieval-augmented-generation]]
- [[papers/Lewis-2020-RAG]]
- [[papers/Pawlik-2025-LLM-Selection-Vector-DB-Tuning]]
- [[papers/Reimers-Gurevych-2019-Sentence-BERT]]
- [[decisões/2026-04-28-modelo-embedding-minilm]]
