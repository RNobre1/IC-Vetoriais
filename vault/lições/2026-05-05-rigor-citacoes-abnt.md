---
tipo: lição-aprendida
data: 2026-05-05
contexto: criação inicial dos fichamentos de papers do vault
tags: [rigor, citações, abnt, fichamento]
---

# Não fabricar metadados de citação

## Situação
Em 2026-05-05, ao criar fichamentos para 13 papers do `vault/papers/` em duas levas (Onda 3 da sessão), o assistente preencheu alguns campos de citação ABNT a partir de **conhecimento prévio** do paper ou **expectativa razoável** sobre formato/venue, sem conferir contra a fonte canônica (a lista de Referências do `docx/relatorio_parcial.docx`).

## Divergências encontradas
9 dos 13 fichamentos tinham erros de citação:

- **Bovas (Navi RAG Chatbot):** ano `2024` → na verdade `2025`; venue genérico `"International Journal [verificar]"` → na verdade `"International Journal for Research in Applied Science and Engineering Technology"`.
- **Pawlik (LLM Selection):** ano `2024` → na verdade `2025`; faltava volume/número/página `v. 15, n. 20, p. 10886`.
- **Patel (ACORN):** venue `"Proceedings of the ACM SIGMOD International Conference on Management of Data"` → na verdade `"Proceedings of the ACM on Management of Data (PACMMOD), v. 2, n. 3, art. 120, p. 1–27"`.
- **Pan (Survey VDBMS):** autor inicial `"J. J. Pan"` → na verdade `"J. Pan"`; arXiv ID `arXiv:2310.14021` adicionado por suposição → não está no docx, removido.
- **Costa (Semantic Enrichment):** instituição `[verificar]` → na verdade `Universidade Nova de Lisboa, Lisboa`.
- **Paiva (Semantic Relations Extraction):** ano vazio + tipo desconhecido → na verdade `2014, Dissertação de Mestrado, Universidade Nova de Lisboa, Lisboa`.
- **Aerospike:** URL `https://aerospike.com/blog/database-benchmarking-best-practices` (chutado) → na verdade `https://www.aerospike.com/blog/best-practices-for-database-benchmarking/`; data de acesso vazia → na verdade `9 dez. 2025`.
- **Lewis (RAG):** formato `"Advances in NeurIPS, v. 33, p. 9459–9474, 2020"` → no docx é `"Advances in NeurIPS 33 (NeurIPS 2020), 2020. p. 9459–9474"`.
- **Malkov (HNSW):** assistente adicionou volume/páginas `v. 42, n. 4, p. 824–836` (corretos pelo TPAMI mas não presentes no docx) → docx tem só `2018`. Manter alinhamento ao docx.

Os outros 4 (Salton, Aumüller, Reimers, Jing) coincidiram suficientemente.

## Causa raiz
Generalização a partir de papers conhecidos do treino do modelo, sem verificação contra a **fonte primária deste projeto** (`docx/relatorio_parcial.docx`). Mesmo quando os números reconstruídos eram tecnicamente plausíveis, a divergência da fonte canônica do projeto é falha de rigor científico — são dois trabalhos com referências diferentes.

## Correção aplicada
1. Lido programaticamente o `docx/relatorio_parcial.docx` (read-only, via python-docx) para extrair o texto exato das 13 entradas de Referências.
2. Identificadas as 9 divergências.
3. Editado cada fichamento via `Edit` para alinhar o campo `citacao_abnt` (e `ano`, `venue`, `autores` quando aplicável) ao texto do docx.
4. Renomeados arquivos cujo ano de filename ficava inconsistente com o ano corrigido (`Bovas-2024-...` → `Bovas-2025-...`; `Pawlik-2024-...` → `Pawlik-2025-...`), com atualização dos backlinks em todo o vault.

## Aplicação a futuro
- Antes de gravar `citacao_abnt` em qualquer fichamento, **ler a entrada exata na lista de Referências do `docx/relatorio_parcial.docx`** e copiar literalmente.
- Quando o docx ainda não tem a entrada (paper novo, ainda não citado no relatório), marcar o campo com `[verificar contra docx ao ser citado]` em vez de chutar.
- A regra vale para qualquer artefato com componente bibliográfico: fichamentos, drafts, citações inline em ADRs. **A fonte canônica é a lista de Referências do `docx/`. O vault espelha o docx, não o contrário.**
- Vale também para metadados estruturais: nome do venue exato, ordem de iniciais dos autores (e.g. "J." vs. "J. J."), volume/número/páginas, tipo de tese, instituição.

## Memória global associada
Esta lição reforça e detalha o feedback `feedback_rigor_cientifico` registrado na memória do Claude para este projeto.

## Backlinks
- [[../decisões/2026-04-28-sistemas-avaliados]]
- [[../papers/Bovas-2025-Navi-RAG-Chatbot]]
- [[../papers/Pawlik-2025-LLM-Selection-Vector-DB-Tuning]]
