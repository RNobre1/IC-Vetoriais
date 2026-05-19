---
tipo: paper
autores: ["Jing, Z.", "Su, Y.", "Han, Y.", "Yuan, B.", "Xu, H.", "Liu, C.", "Chen, K.", "Zhang, M."]
ano: 2024
titulo: "When Large Language Models Meet Vector Databases: A Survey"
venue: "arXiv:2402.01763 (Cornell University)"
tags: [survey, llm, vdbms, rag]
citacao_abnt: "JING, Z. et al. When Large Language Models Meet Vector Databases: A Survey. arXiv:2402.01763 (Cornell University), 2024."
arquivo_local: "When Large Language Models Meet Vector Databases_ A Survey.pdf"
---

# When Large Language Models Meet Vector Databases: A Survey

> **Status do fichamento:** **verificado contra o PDF** em 2026-05-20 (lidas p. 1–2: autores, resumo, introdução e background; arXiv:2402.01763, v1 fev. 2024 / v4 jun. 2025). Coautores conferidos: Zhi Jing, Yongye Su, Yikun Han, Bo Yuan, Haiyun Xu, Chunjiang Liu, Kehai Chen, Min Zhang (CMU, Purdue, U. Michigan, HIT-Shenzhen, CAS, SDUT).

## Síntese
Survey da interseção LLMs × *Vector Databases* (VecDBs). Argumenta que VecDBs são solução para limitações dos LLMs — alucinação, conhecimento desatualizado, custo comercial, memória — ao oferecerem armazenamento/recuperação eficiente das representações vetoriais intrínsecas às operações de LLM.

## Contribuições
- Delineia princípios fundamentais de LLMs e VecDBs e analisa criticamente a integração entre eles.
- Mapeia papéis da VecDB junto ao LLM: base de conhecimento externa (RAG), memória de diálogo por usuário, e cache semântico.

## Método
Survey de literatura (sem experimento próprio); revisão de fundamentos de LLM (PLM, Transformer, scaling laws) e de VecDB, e da literatura de integração.

## Resultados-chave
- Três desafios centrais dos LLMs puros endereçáveis por VecDB: **alucinação** (geração plausível mas factualmente incorreta), conhecimento estático/desatualizado, e custo computacional/comercial.
- VecDB como **memória externa** resolve esses problemas "de forma transparente" (incorporada como base de conhecimento externa, memória de chat, ou cache semântico).

## Limitações
Survey de momento (fev. 2024); campo evolui rápido; sem avaliação empírica própria.

## Relevância para a IC
**Sustenta §1.1 e §3.5** do relatório ([[referência/bancos-de-dados-vetoriais]], [[referência/rag-retrieval-augmented-generation]]). **Verificação:** o relatório afirma "bancos de dados vetoriais funcionam como memória externa para LLMs, permitindo acessar e sintetizar grandes volumes sem reciclagem constante" (§1.1) e "reduzindo alucinações e aumentando a precisão factual" (§3.5) — ambas conferem com resumo/introdução do paper. Complementa [[papers/Pan-Wang-Li-2023-Survey-VDBMS]] pelo lado das aplicações de LLM.

## Citáveis
> "VecDBs emerge as a compelling solution to these [hallucinations, outdated knowledge, prohibitive cost, memory issues] by offering an efficient means to store, retrieve, and manage the high-dimensional vector representations intrinsic to LLM operations." (Resumo)
> "VecDBs can either be incorporated as an external knowledge base for LLMs, a memory for LLMs saving previous related chat contents [...], or a semantic cache [...]." (§1)

## Backlinks
- [[referência/bancos-de-dados-vetoriais]]
- [[referência/rag-retrieval-augmented-generation]]
- [[papers/Pan-Wang-Li-2023-Survey-VDBMS]]
- [[papers/Lewis-2020-RAG]]
