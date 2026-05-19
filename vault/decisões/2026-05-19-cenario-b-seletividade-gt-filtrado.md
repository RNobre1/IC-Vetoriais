---
tipo: decisão
data: 2026-05-19
status: aceita
autores: ["Rafael Nobre", "Celson Lima"]
tags: [cenário-b, seletividade, filtro, ground-truth, recall, metodologia]
---

# Cenário B: predicado de seletividade por atributo numérico + recall@K contra ground truth filtrado

## Contexto
O Cenário B (busca com filtro de metadados, [[2026-04-28-cenarios-A-B-C]]) precisa medir o impacto da **seletividade do filtro** (fração da base que satisfaz o predicado: 1%, 10%, 50%, 100%) sobre latência/QPS/recall nos 3 SGBDs. Duas decisões metodológicas estavam abertas e travavam o TDD: (1) qual mecanismo de predicado o seed grava e a busca filtra; (2) contra qual ground truth o recall@K é medido quando há filtro. Cenário A já fechado ([[2026-05-10-cenario-a-queries-warmup]]) — B reusa sua estrutura (queries held-out, warmup+descarte, sweep efSearch).

## Opções consideradas

### Decisão 1 — mecanismo do predicado
1. **Atributo numérico uniforme + predicado de range** — seed grava `seletor` ∈ [0,1) determinístico; filtro `seletor < p`.
   - Prós: seletividade exata (±1/N); `p` é parâmetro de runtime (varia sem re-seedar); 1 único atributo; mapeia direto para `WHERE`/`Filter(Range)`/`Filter.less_than` nos 3 SGBDs; alinhado a filtered-ANN (ACORN, Big-ANN filtered track).
   - Contras: predicado de range é menos típico que igualdade categórica em RAG por tags (registrado como limitação/trabalho futuro).
2. **Coluna categórica + igualdade** — `categoria ∈ {c01,c10,c50}` com proporções fixas; filtro `categoria = cX`.
   - Prós: mais próximo do filtro de tag típico de RAG.
   - Contras: seletividades cravadas no seed (mudar p ⇒ re-seedar tudo); 100% exige caso especial; proporções exatas dependem de arredondamento por N.

### Decisão 2 — ground truth sob filtro
1. **Top-K exato dentro do subconjunto filtrado** — para cada `p`, FAISS exato só sobre os vetores que passam `seletor < p`.
   - Prós: é o ótimo atingível sob o filtro; denominador do recall = K; padrão Big-ANN filtered / ACORN.
   - Contras: 1 ground truth por nível de seletividade (4 `.npz`).
2. **Top-K global mascarado** — top-K do Cenário A, mantendo só os que passam o filtro.
   - Contras: denominador variável (<K), interpretação ambígua, penaliza o sistema por itens corretamente excluídos; metodologicamente fraco.

## Decisão
**Decisão 1: Opção 1** (atributo numérico `seletor` uniforme + predicado de range `seletor < p`).
**Decisão 2: Opção 1** (recall@K contra top-K exato calculado **dentro do subconjunto filtrado**, um ground truth por nível de seletividade).

Escolha do piloto (2026-05-19), ambas as recomendações técnicas.

## Justificativa
- **`seletor` uniforme determinístico decorrelacionado:** `rng = np.random.default_rng(42)`; `seletor = rng.permutation(N).astype(float64) / N`. Valores em `{0, 1/N, …, (N-1)/N}` — únicos, uniformes, **decorrelacionados do id e do conteúdo do vetor** (a permutação quebra qualquer correlação com a ordem de inserção do MS MARCO). `seletor < p` seleciona exatamente `ceil(p·N)` linhas (seletividade = `p` a menos de ±1/N; documentado). `p = 1.0` ⇒ todos passam ⇒ âncora de sanidade que deve reproduzir o Cenário A.
- **Ground truth filtrado é o único recall correto sob filtro:** o sistema só pode/deve retornar itens que passam o predicado; comparar com o top-K global puniria o sistema por exclusões corretas do filtro. O ótimo é o top-K *entre os elegíveis*. Os ids retornados pelo FAISS sobre o subconjunto são remapeados para os ids originais `0..N-1` (consistentes com os seeders).
- **Borda |subconjunto| < K:** com `p` pequeno e `N` de smoke, o subconjunto filtrado pode ter menos que `K` vetores. `recall_at_k` já é set-based (`np.intersect1d`); o ground truth filtrado terá `min(K, |subconjunto|)` colunas e o recall continua bem definido. Validar `K ≤ ceil(p·N)` nos tamanhos reais (100k/500k: 1% de 100k = 1000 ≥ K=10, ok).

## Consequência
- **Ground truth:** novo `ground_truth.exact_search.top_k_exato_filtrado(base, queries, *, seletor, p, k)` → `(scores, ids_originais)`. 1 `.npz` por seletividade (nome inclui `p`).
- **Seeders:** os 3 passam a gravar um campo numérico `seletor` quando presente no `metadata` (pgvector `real`, Qdrant payload float, Weaviate `DataType.NUMBER`). `metadata=None` ⇒ sem `seletor` ⇒ Cenário A intacto (compat retroativa obrigatória; testes do A permanecem verdes).
- **Adaptadores:** novo Protocol `BuscadorFiltravel(BuscadorVetorial)` com `buscar_uma_filtrada(query, k, *, p_max)`; `BuscadorVetorial` do Cenário A **não muda** (Protocol já testado).
- **Orquestração:** `benchmarks/cenario_b.medir_sistema_filtrado` varre `seletividades × efSearch`; `cenario="B"`; `parametros` inclui `seletividade`. `salvar_curva` reusado.
- **Fora de escopo:** filtro categórico de igualdade e predicados compostos (AND/OR de tags) — possível trabalho futuro / Etapa 4; registrar como limitação no relatório.

## Critério de revisão
Reabrir se: (a) o orientador exigir filtro categórico/igualdade por aderência a um caso de uso RAG específico; (b) algum SGBD não suportar range filter sobre HNSW de forma comparável (forçaria normalizar o predicado); (c) nos tamanhos reais `K > ceil(p·N)` para o menor `p` escolhido (revisar grade de seletividades ou K).

## Backlinks
- [[2026-04-28-cenarios-A-B-C]]
- [[2026-05-10-cenario-a-queries-warmup]]
- [[../../docs/tasks/etapa-2-preparacao-ambiente]]
- [[../referência/metodologia-benchmarking-ann]]
