---
tipo: paper
autores: ["Pawlik, L."]
ano: 2025
titulo: "LLM Selection and Vector Database Tuning: A Methodology for Enhancing RAG Systems"
venue: "Applied Sciences (MDPI), v. 15, n. 20"
tags: [rag, metodologia, vdbms, tuning, llm, qdrant]
citacao_abnt: "PAWLIK, L. LLM Selection and Vector Database Tuning: A Methodology for Enhancing RAG Systems. Applied Sciences, v. 15, n. 20, art. 10886, 2025. DOI: 10.3390/app152010886."
arquivo_local: "Pawlik-2025-LLM-Selection-Vector-DB-Tuning.pdf"
---

# LLM Selection and Vector Database Tuning: A Methodology for Enhancing RAG Systems

> **Status do fichamento:** **verificado contra o PDF** em 2026-05-20 (lidas p. 1–3 de 19: resumo, introdução, trabalhos relacionados e dataset; *Applied Sciences* 2025, 15, 10886, MDPI, DOI 10.3390/app152010886; autor único Lukasz Pawlik, Kielce University of Technology, Polônia). PDF renomeado para `Pawlik-2025-LLM-Selection-Vector-DB-Tuning.pdf` (nome original continha quebra de linha).

## Síntese
Propõe uma metodologia abrangente para **medir e otimizar** sistemas RAG, analisando o impacto conjunto de parâmetros-chave — tamanho de *chunk*, modelo de *embedding* e escolha do LLM — sobre a eficácia do sistema. Experimentos num RAG sobre dataset biográfico longo, armazenado em **Qdrant**.

## Contribuições
- Metodologia integrada (não isolada) que avalia a dependência *retriever–generator*: parâmetros do banco vetorial (chunking, embedding) otimizados em conjunto com a seleção do LLM.
- Orientação prática para engenheiros sobre configuração de RAG em contexto corporativo com texto longo.

## Método
- RAG experimental sobre dataset público do Kaggle (PII External Dataset, 4434 linhas; ensaios biográficos: média 352 tokens, 96–607; 1975 caracteres). Colunas: "biographical essay" (conteúdo) e "full name" (metadado).
- Banco vetorial: **Qdrant**. Avaliação da eficácia usando LLMs como juízes; varia chunk size, embedding model e LLM.

## Resultados-chave
- Otimizar RAG exige considerar múltiplos fatores (janela de contexto do LLM, poder computacional, custos de processamento).
- **A seleção de parâmetros e LLM ótimos é um *trade-off* entre qualidade da resposta, custo computacional e limitações de hardware** — alinhado ao trade-off central desta IC.

## Limitações
Dataset único (biográfico) e de texto longo; generalização para outros domínios não garantida (declarado pelo autor como contexto específico). [Detalhes nas §9–10, não lidas em profundidade.]

## Relevância para a IC
**Sustenta §1.3 e §3.5** do relatório. Verificação: o paper demonstra que a **configuração/tuning da camada vetorial (chunking, embedding) impacta a eficácia e a qualidade de resposta do RAG**, como *trade-off* com custo/hardware. **Ressalva de rigor:** o relatório dizia "precisão e **robustez**"; o paper não mede "robustez" — usa "accuracy/efficiency/effectiveness/response quality". O texto do relatório (§1.3 e §3.5) foi ajustado para "qualidade das respostas e eficiência", termos efetivamente sustentados. Contraste útil para Trabalhos Relacionados: Pawlik trata o embedding como variável a tunar; **esta IC fixa o modelo** para isolar o efeito do SGBD ([[decisões/2026-04-28-modelo-embedding-minilm]]). Nota: Pawlik usa Qdrant — um dos sistemas desta IC.

## Citáveis
> "The selection of optimal parameters and LLM is a trade-off between response quality, computational cost, and hardware limitations." (Resumo)
> "...a systematic methodology for simultaneously tuning and evaluating the retriever–generator dependency, where the vector database parameters (chunking strategy, embedding model) are jointly optimized with the LLM selection..." (§2)

## Backlinks
- [[referência/rag-retrieval-augmented-generation]]
- [[decisões/2026-04-28-modelo-embedding-minilm]]
- [[papers/Lewis-2020-RAG]]
- [[papers/Bovas-2025-Navi-RAG-Chatbot]]
