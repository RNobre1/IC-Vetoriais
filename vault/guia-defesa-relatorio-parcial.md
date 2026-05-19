---
tipo: guia-de-estudo
data: 2026-05-19
contexto: Preparação para reunião com o orientador (Prof. Dr. Celson Pantoja Lima) em 2026-05-20 sobre o relatório parcial. Cobre conceitos da bibliografia, decisões metodológicas e o porquê de cada escolha, estado atual e perguntas prováveis.
tags: [defesa, relatório-parcial, estudo, bibliografia, decisões]
---

# Guia de defesa do relatório parcial

> Como usar: leia a Parte 0 e a Parte 4 primeiro (são as que salvam na reunião). As Partes 1–3 são profundidade. Toda afirmação aqui é rastreável ao relatório, às ADRs em `decisões/` ou aos fichamentos em `papers/`. **Não invente número** — se não temos, a resposta honesta está escrita aqui.

---

## Parte 0 — O essencial (decore isto)

### Pitch de 60 segundos
"O trabalho compara experimentalmente três formas de guardar e buscar embeddings para busca semântica e RAG: PostgreSQL com a extensão pgvector (um relacional estendido) contra dois bancos vetoriais especializados, Qdrant e Weaviate. Os três usam o mesmo índice (HNSW), então as diferenças que medirmos refletem implementação e arquitetura, não algoritmo. Medimos latência (p50/p95/p99), throughput (QPS), recall@K contra busca exata e consumo de recursos, em três cenários: busca pura (A), busca com filtro de metadados (B) e carga mista RAG (C). A metodologia é inspirada no ANN-Benchmarks: reportamos curvas recall×QPS, não números soltos. Esta parcial fecha a fundamentação teórica e o ambiente experimental reproduzível; os experimentos em escala são a próxima etapa."

### Estado honesto (não seja pego nisto)
- **Pronto e sólido:** fundamentação teórica (11 referências fechadas); ambiente Docker dos 3 SGBDs reproduzível; pipeline de embeddings determinístico; ground truth exato (FAISS); Cenários A e B **implementados em TDD** (175 testes verde) com smoke real ponta-a-ponta nos 3 sistemas; esqueleto do C.
- **Ainda NÃO existe:** resultados em 100k/500k (latência/QPS/recall reais), footprint de memória/disco, tempo de indexação, Cenário C executado. Só rodamos smoke com N=200/300 para validar o pipeline.
- **Cuidado — o texto do relatório está adiantado em relação à execução:** o Resumo e as Considerações afirmam que a "primeira fase de experimentos (100k/500k)" foi concluída e que "resultados preliminares já permitem observar diferenças". **Isso ainda não é verdade.** Se perguntarem pelos números: *"O ambiente e os scripts dos Cenários A e B estão prontos, testados e validados em smoke ponta-a-ponta nos três sistemas; a execução em escala 100k/500k é o passo imediato da Etapa 3 e entra na versão final da parcial. O texto da seção de resultados está com os placeholders a preencher com esses números."* Honestidade > fingir.
- **Divergência relatório × código no Cenário B:** o relatório (Seção 4) descreve filtros de "categoria/área/data/curso". O implementado é um atributo numérico sintético `seletor ∈ [0,1)` com predicado `seletor < p`, variando a **seletividade** (1%, 10%, 50%, 100%). Resposta pronta na Parte 4, item Q7.

---

## Parte 1 — Conceitos da bibliografia

Para cada um: **o que é · por que está no trabalho · pergunta provável + resposta**.

### 1.1 Vector Space Model — VSM (Salton, Wong & Yang, 1975)
- **O que é:** modelo clássico de recuperação de informação. Documentos e consultas viram vetores num espaço onde cada dimensão é um termo do vocabulário. Relevância = proximidade angular (similaridade de cosseno). Pesos via TF-IDF.
- **TF-IDF:** *term frequency* (frequência do termo no documento) × *inverse document frequency* (raridade do termo no corpus — termos comuns pesam menos). Captura "este termo é frequente aqui e raro no geral, logo discrimina".
- **Similaridade de cosseno:** cosseno do ângulo entre dois vetores = (A·B)/(‖A‖‖B‖). Mede orientação, não magnitude — bom para texto (documento longo não fica "mais perto" só por ser longo).
- **Limitações (decore — vão perguntar):** vetores **esparsos** e de dimensão = tamanho do vocabulário; não captura **sinonímia** (carro/automóvel em dimensões independentes), **polissemia** (banco financeiro vs. de rio), nem *vocabulary mismatch* (consulta e documento usam palavras diferentes para o mesmo conceito).
- **Por que está no trabalho:** é a raiz conceitual. Embeddings densos são a evolução do VSM — mesma ideia (texto→vetor, similaridade geométrica), mas representação densa aprendida em vez de esparsa por contagem.

### 1.2 Enriquecimento semântico / ontologias — SENSE (Costa, 2014) e Paiva (2014)
- **O que é:** o framework SENSE estende o VSM clássico incorporando relações de uma **ontologia de domínio** (relações explícitas entre conceitos) à representação, melhorando o recall ao capturar significado além da palavra literal.
- **Por que está no trabalho:** é a **ponte histórica** VSM → embeddings. Argumento: a necessidade de "capturar semântica além de palavras explícitas" já estava em SENSE (resolvida com engenharia manual de ontologia); RAG/embeddings resolvem o mesmo problema com aprendizado automático sobre grandes corpora. Justifica por que a camada vetorial é decisiva.
- **Pergunta provável:** *"Por que citar trabalho de ontologia num estudo de banco vetorial?"* → Para mostrar continuidade do problema de pesquisa (qualidade da representação semântica) e ancorar a justificativa; não usamos ontologias, usamos embeddings densos como evolução dessa linha.

### 1.3 Embeddings densos / Sentence-BERT (Reimers & Gurevych, 2019)
- **O que é:** Sentence-BERT adapta o BERT com **redes siamesas** (dois encoders idênticos com pesos compartilhados) para produzir embeddings de sentença comparáveis diretamente por cosseno/produto interno — sem precisar passar todo par de frases pelo modelo (o que era inviável em escala com BERT puro).
- **Denso vs. esparso:** centenas de dimensões, **todas ativas**; textos de significado próximo caem em regiões próximas mesmo sem palavra em comum. Resolve sinonímia/mismatch que o VSM não resolvia.
- **Por que no trabalho:** é a família do modelo escolhido (`all-MiniLM-L6-v2`, 384 dim). A dimensionalidade impacta diretamente armazenamento, memória do índice e custo de similaridade — variável metodológica fixada para isolar o efeito do SGBD.

### 1.4 Busca aproximada de vizinhos (ANN) e HNSW (Malkov & Yashunin, 2018)
- **Problema:** busca exata dos K vizinhos = comparar com todos os N vetores → custo linear, proibitivo com latência interativa em centenas de milhares/milhões de vetores.
- **ANN:** abre mão da garantia de exatidão em troca de tempo, mantendo **recall alto** vs. exato.
- **HNSW:** grafo de **múltiplas camadas**. Camadas superiores: poucos nós, arestas longas → salta rápido entre regiões distantes. Camadas inferiores: densas → refina perto do alvo. É *navigable small world* hierárquico.
- **Parâmetros (decore):**
  - **M** = nº de conexões (vizinhos) por nó no grafo. Maior M → grafo mais conectado, melhor recall, mais memória e indexação mais lenta.
  - **ef_construction** = tamanho da lista de candidatos **na construção** do índice. Maior → índice melhor, build mais lento.
  - **ef_search (ef)** = tamanho da fila de candidatos **na busca**. Maior ef → mais recall, mais latência. **É o parâmetro que varremos** para traçar a curva recall×QPS.
- **Por que no trabalho:** os 3 SGBDs usam HNSW como índice principal. Decisão deliberada (ADR `2026-04-28-índice-hnsw-em-todos`): fixar o algoritmo para que diferenças observadas sejam de **implementação/arquitetura**, não de algoritmo.

### 1.5 Bancos de dados vetoriais — taxonomia (Pan, Wang & Li, 2023)
- **VDBMS:** sistemas para armazenar, indexar e consultar vetores densos por similaridade em escala. Pan et al. dividem em duas categorias:
  - **(i) Especializados** — projetados desde o início para vetores (índices nativos, otimizações). Ex.: Qdrant, Weaviate, Milvus, Pinecone.
  - **(ii) Extensões de SGBD existente** — adicionam tipo vetorial + operadores a um banco maduro. Ex.: PostgreSQL + pgvector.
- **Trade-off central do trabalho:** integrada (menos complexidade de stack, reaproveita o Postgres e junta filtro relacional + vetor no mesmo plano) **vs.** especializada (otimizada para o caso vetorial, mas é mais um sistema para operar). O estudo quantifica esse compromisso.
- **Os três sistemas:**
  - **pgvector:** extensão do PostgreSQL; tipo `vector`, índices HNSW e IVFFlat; vetor e metadado estruturado no mesmo banco.
  - **Qdrant:** especializado, escrito em Rust; HNSW nativo; filtros por *payload* arbitrário; REST/gRPC.
  - **Weaviate:** especializado; camada de esquema tipado, GraphQL; rodado **sem** módulo de vetorização interno (`DEFAULT_VECTORIZER_MODULE=none`) para que todos os vetores venham do mesmo pipeline externo.

### 1.6 Filtros + busca vetorial — ACORN (Patel et al., 2024)
- **O problema:** combinar busca vetorial com predicado estruturado ("similar a X **e** categoria=Y"). Três estratégias:
  - **Pré-filtragem:** filtra primeiro, busca vetorial só no subconjunto. Bom em filtro seletivo; ruim se subconjunto grande/índice não restringível.
  - **Pós-filtragem:** busca vetorial, depois descarta os que não passam o filtro. Pode precisar buscar muito além de K se o filtro corta muito.
  - **Filtragem inline / durante a navegação no grafo HNSW:** aplica o predicado enquanto percorre o grafo. ACORN mostra ganho expressivo de throughput a recall fixo com essa abordagem predicate-agnostic.
- **Por que no trabalho:** é a base teórica do **Cenário B**. Os três SGBDs implementam filtragem de formas diferentes — daí esperar diferenças de comportamento sob filtro, e por isso variamos a **seletividade** do predicado.

### 1.7 RAG — Retrieval-Augmented Generation (Lewis et al., 2020; Jing 2024; Pawlik 2025; Bovas 2025)
- **O que é (Lewis 2020):** LLM + recuperação. Consulta → embedding → recupera trechos similares do banco vetorial → injeta como contexto no LLM → resposta fundamentada. Acessa conhecimento atualizado/de domínio sem retreinar; reduz alucinação.
- **Por que a camada vetorial importa (Pawlik 2025):** contexto ruim na recuperação degrada a resposta mesmo com bom gerador; configuração/tuning da camada vetorial impacta precisão e robustez do RAG.
- **Evidência aplicada (Bovas 2025 — NAVI):** chatbot RAG acadêmico com scores de relevância 0,7–0,85 condicionados à qualidade dessa camada.
- **Survey (Jing 2024):** LLMs + bancos vetoriais como memória externa.
- **Por que no trabalho:** motiva os cenários — A e B são os perfis de recuperação típicos de RAG; C simula RAG em produção (escrita concorrente com leitura).

### 1.8 Metodologia de benchmarking (Aümuller, Bernhardsson & Faithfull, 2020; Aerospike, 2025)
- **ANN-Benchmarks (Aümuller 2020):** referência para avaliar implementações ANN. Fixa datasets, **varre o espaço de parâmetros** do índice e reporta a **curva recall × QPS** — explicita o trade-off em vez de um número pontual.
- **Aerospike 2025:** boas práticas gerais de benchmark de banco — workload claro, ambiente controlado, medição reproduzível.
- **Por que no trabalho (decisão metodológica firme):** **reportamos curvas recall×QPS, não números pontuais** — variamos ef_search e plotamos. É o que dá rigor comparativo.

---

## Parte 2 — Decisões metodológicas e por que NÃO a alternativa

Cada uma tem ADR datada em `vault/decisões/`. Formato: **decisão · alternativa rejeitada · porquê**.

| # | Decisão | Alternativa rejeitada | Por quê |
|---|---------|----------------------|---------|
| 1 | **Avaliar pgvector + Qdrant + Weaviate** | Incluir Milvus/Pinecone | Cobre os dois lados do trade-off (extensão vs. especializado) com 2 especializados open-source representativos; Pinecone é fechado/SaaS (não reproduzível, custo); Milvus agrega complexidade operacional sem mudar a pergunta de pesquisa. Escopo de IC. ADR `2026-04-28-sistemas-avaliados`. |
| 2 | **HNSW nos três** | Comparar algoritmos diferentes (IVF, etc.) | Fixar o algoritmo isola a variável: diferença observada = implementação/arquitetura, não algoritmo. Comparar algoritmos diferentes confundiria as causas. ADR `2026-04-28-índice-hnsw-em-todos`. |
| 3 | **`all-MiniLM-L6-v2` (384d)** | `all-mpnet-base-v2` (768d), BGE-large (1024d) | (i) roda em CPU no notebook-alvo, viabiliza 1M sem GPU; (ii) reprodutível por terceiros sem placa; (iii) suficiente — avaliamos o SGBD, não a qualidade absoluta do retrieval. Modelo fixo controla a variável embedding. ADR `2026-04-28-modelo-embedding-minilm`. |
| 4 | **Subset MS MARCO Passages, amostragem determinística** | Dataset sintético; outro corpus | MS MARCO: escala (~8,8M passages), licença de pesquisa, **qrels** (julgamentos de relevância) disponíveis. Amostragem = ordenar por passage_id e pegar os N primeiros → reprodutível bit-a-bit. ADR `2026-04-28-dataset-ms-marco`. |
| 5 | **Escalas 100k / 500k / 1M** | Só um tamanho | Traçar comportamento em ordens de grandeza distintas e ver onde cada arquitetura se diferencia. **1M só na Etapa 4** (risco de RAM: 16 GiB com 3 SGBDs simultâneos é justo). ADR `2026-04-28-tamanhos-100k-500k-1m`. |
| 6 | **Cenários A (puro) / B (filtro) / C (carga mista)** | Só busca pura | Cobrem os perfis reais de RAG: recuperação simples, recuperação filtrada (RAG corporativo), e produção (escrita concorrente). ADR `2026-04-28-cenarios-A-B-C`. |
| 7 | **Queries = passages held-out; warmup descartado** | Reusar vetores da base como query; medir warmup | Query held-out = não está na base seedada → mede generalização real (estilo ANN-Benchmarks), não trivial "achar a si mesmo". Warmup descartado tira efeito de cache frio/JIT. ADR `2026-05-10-cenario-a-queries-warmup`. |
| 8 | **Cenário B: atributo numérico `seletor` uniforme + `seletor < p`; GT filtrado por seletividade** | Filtro categórico (área/data); reusar GT global do Cenário A | Numérico uniforme decorrelacionado dá **seletividade exata e parametrizável** (1/10/50/100%) sem re-seedar, alinhado a ACORN/Big-ANN. GT tem que ser o **top-K exato dentro do subconjunto filtrado** — comparar com o GT global puniria o sistema por excluir corretamente o que o filtro remove. ADR `2026-05-19-cenario-b-seletividade-gt-filtrado`. **(Ver Q7 na Parte 4 — o relatório ainda descreve filtro categórico.)** |
| 9 | **Ground truth: FAISS `IndexFlatIP`** | Implementar busca exata à mão; usar índice aproximado como referência | `IndexFlatIP` = produto interno exato (sem aproximação). Como os embeddings são **normalizados L2**, produto interno ≡ cosseno → mesma métrica dos SGBDs, referência de ouro correta para recall@K. |
| 10 | **Reportar curvas recall×QPS** | Números pontuais (um p95, um recall) | Número pontual esconde o trade-off; a curva é o padrão ANN-Benchmarks e permite comparação justa a recall fixo. Decisão firme do docs/metodologia.md. |
| 11 | **Versões fixadas + bump para snapshot maio/2026** | `:latest`; versões antigas | `:latest` quebra reprodutibilidade; versões antigas não refletem o estado-da-arte. Snapshot estável contemporâneo. ADRs `2026-05-05-versoes-imagens-docker`, `2026-05-06-bump-versoes-sgbds`. |
| 12 | **Isolar ferramenta de inspeção (Verba) do benchmark** | Deixar UI rodando junto | UI consome recurso e contamina medição; compose separado, desligado nos benchmarks. ADR `2026-05-05-isolamento-ui-vs-benchmark`. |
| 13 | **CI só lint+unit; integração local** | CI com os 3 SGBDs via `services:` | Runners gratuitos não aguentam 3 SGBDs + MS MARCO (~3 GB); fragiliza o pipeline. Rede de segurança = smoke local obrigatório antes de cada commit de cenário. ADR `2026-05-19-ci-integracao-local`. |
| 14 | **Relatório em LaTeX** | Manter `.docx` | Versionável, diff limpo, bibliografia gerenciada. ADR `2026-05-05-migracao-relatorio-para-latex`. |
| 15 | **Cronograma canônico = tabela do relatório (Etapa 2 Mar–Abr, 3 Mai–Jun)** | Cronograma "comprimido" interno | Documento entregável é a fonte única; datas reais de execução ficam no log factual do vault. Decisão do piloto. ADR `2026-05-19-cronograma-canonico-relatorio`. |

---

## Parte 3 — Estado atual, arquitetura e métricas

### 3.1 Arquitetura do `code/` (saiba descrever o fluxo)
`pipeline/` (carrega subset MS MARCO determinístico → gera embeddings com cache determinístico) → `seeders/` (insere nos 3 SGBDs com índice HNSW; grava `seletor` no Cenário B) → `ground_truth/` (FAISS: top-K exato, e top-K exato **filtrado** por seletividade) → `benchmarks/buscadores.py` (um adaptador por SGBD, contrato comum `BuscadorVetorial`/`BuscadorFiltravel`) → `benchmarks/cenario_a|b|c.py` (orquestração da medição, varre ef e seletividade) → `lib/metrics.py` (p50/p95/p99, QPS, recall@K) + `lib/reporting.py` (curva em JSON normalizado) → CLIs `run_cenario_a|b`, `run_seed` + `Makefile` (`make bench-A`, `bench-B`, `seed`, `bench-C-dryrun`).

- **Desacoplamento por Protocol:** a orquestração fala com uma interface (`BuscadorVetorial`), cada SGBD é um adaptador. Permite testar a lógica de medição **sem Docker**.
- **TDD estrito:** teste antes do código de produção. **175 testes verde** (150 unitários sem Docker + 25 de integração contra os 3 SGBDs reais). Lint/format limpos.
- **Smoke real validado:** `make bench-A`/`bench-B` rodaram ponta-a-ponta nos 3 sistemas (N pequeno), 2 execuções consecutivas (idempotência). Gravam curva JSON + ground truth.

### 3.2 As métricas (saiba definir cada uma)
- **Latência p50/p95/p99:** percentis do tempo de resposta por consulta. p50 = mediana (caso típico); p99 = cauda (pior caso que 99% das consultas batem) — crítico para experiência sob carga. Medimos por query, em ms, descartando warmup.
- **Throughput (QPS):** consultas atendidas por segundo sob carga controlada.
- **Recall@K:** dos K vizinhos retornados pelo SGBD, quantos estão entre os K verdadeiros (busca exata FAISS). É qualidade da recuperação aproximada. Set-based: |obtidos ∩ exatos| / K.
- **Footprint:** memória e disco por tamanho de dataset; tempo de indexação inicial. **(ainda não medido — Etapa 3+)**
- **Curva recall × QPS:** variando ef_search, cada ponto é (recall, QPS). A curva inteira é o resultado, não um ponto.

### 3.3 O que está pronto vs. pendente (tabela honesta)
| Item | Estado |
|------|--------|
| Fundamentação teórica (11 refs) | ✅ consolidada |
| Ambiente Docker 3 SGBDs reproduzível | ✅ |
| Pipeline embeddings determinístico | ✅ |
| Ground truth exato (FAISS) + filtrado | ✅ |
| Cenário A (código + smoke) | ✅ implementado e testado |
| Cenário B (código + smoke) | ✅ implementado e testado |
| Cenário C | 🟡 só esqueleto (Etapa 4) |
| **Resultados 100k/500k (números reais)** | ❌ **não executado** |
| Footprint memória/disco, tempo indexação | ❌ não medido |
| Seção 5 do relatório (Resultados) | ❌ placeholders `\todo` |

---

## Parte 4 — Perguntas difíceis prováveis (com resposta pronta)

**Q1. "Cadê os resultados de 100k/500k que o relatório menciona?"**
R: Honesto — *"A engenharia dos Cenários A e B está completa, testada em TDD (175 testes) e validada em smoke ponta-a-ponta nos três sistemas. A execução em escala 100k/500k é o passo imediato da Etapa 3; os números entram na versão a ser entregue. A seção de resultados está com os placeholders demarcando exatamente o que será preenchido."* Não minta que existem.

**Q2. "Por que três sistemas só? Por que não Milvus/Pinecone?"**
R: Escopo de IC + reprodutibilidade. pgvector representa "extensão de relacional", Qdrant e Weaviate "especializados" open-source. Pinecone é SaaS fechado (sem reprodutibilidade, custo). Cobre o trade-off central com profundidade > amplitude.

**Q3. "Se os três usam HNSW, o que exatamente você está comparando?"**
R: Implementação e arquitetura: como cada um implementa HNSW, integra com o resto do sistema, gerencia memória, faz filtragem (pré/pós/inline), persiste e atualiza. Fixar o algoritmo é o que torna a comparação interpretável (Malkov & Yashunin para o algoritmo; Pan et al. para a taxonomia).

**Q4. "Por que MiniLM e não um modelo melhor?"**
R: Avaliamos o SGBD, não a qualidade do retrieval. MiniLM (384d) roda em CPU, viabiliza 1M sem GPU e é reprodutível por terceiros. Fixo em todos os experimentos → variável controlada. Modelo melhor mudaria custo de armazenamento/memória sem mudar a pergunta.

**Q5. "Como você garante reprodutibilidade?"**
R: Versões pinadas (`requirements.txt` + `.lock`), imagens Docker em tag fixa (não `:latest`), amostragem determinística do MS MARCO (ordena por passage_id, pega N), embeddings com cache determinístico, seeds fixos, ground truth exato como referência, hardware documentado. Qualquer pessoa roda `make up && make smoke`.

**Q6. "Como o recall é calculado se a busca é aproximada?"**
R: Referência de ouro = busca **exata** com FAISS `IndexFlatIP` (produto interno, sem aproximação). Embeddings normalizados L2 → produto interno = cosseno, mesma métrica dos SGBDs. recall@K = fração dos K verdadeiros que o SGBD recuperou.

**Q7. "Como exatamente é o filtro do Cenário B?" / "O relatório fala em área e data, mas..."**
R (transparente): *"Na implementação consolidamos o filtro como um atributo numérico sintético com seletividade controlada — variamos a fração da base que passa o predicado em 1%, 10%, 50% e 100%. Isso dá controle exato e parametrizável da seletividade (alinhado ao ACORN e ao Big-ANN filtered track) e permite isolar o efeito da seletividade sobre latência/recall, o que um filtro 'área/data' não daria de forma limpa. O texto da Seção 4 ainda descreve o exemplo motivacional categórico e será alinhado a essa decisão (registrada em ADR `2026-05-19-cenario-b-seletividade-gt-filtrado`)."* — Isso vira ponto a favor (mostra rigor), não contra, se você assumir e explicar.

**Q8. "Por que o recall sob filtro não usa o mesmo ground truth do Cenário A?"**
R: Porque sob filtro o sistema só pode retornar itens que passam o predicado. O ótimo é o top-K exato **dentro do subconjunto filtrado**. Comparar com o top-K global puniria o sistema por excluir corretamente o que o filtro remove — recall artificialmente baixo e sem sentido. Por isso geramos um ground truth exato por nível de seletividade.

**Q9. "O cronograma diz Etapa 1 em Jan–Fev, mas o projeto começou depois."**
R: A tabela do relatório segue o planejamento original do edital e é a referência canônica do documento. As datas reais de execução estão registradas no diário de bordo do projeto. Decisão consciente de manter o cronograma do edital como referência de planejamento (ADR `2026-05-19-cronograma-canonico-relatorio`).

**Q10. "Por que não usar a GPU (RTX 3050) para os embeddings?"**
R: Reprodutibilidade por terceiros sem GPU e estabilidade. 6 GB de VRAM é apertado; CPU com MiniLM gera 1M em tempo aceitável. A GPU não muda a comparação entre SGBDs (o gargalo medido é o banco, não a geração de embeddings, que é feita uma vez e cacheada).

**Q11. "Ameaças à validade?"** (mostra maturidade se você levantar isso sozinho)
R: (a) hardware único (notebook) — mitigado documentando e, possivelmente, Cluster HPC do IEG na Etapa 4; (b) um único modelo de embedding — controlado de propósito, mas limita generalização; (c) N=200/300 no smoke não diferencia sistemas — por isso 100k/500k/1M na sequência; (d) configurações default como baseline — ajuste controlado de parâmetros é trabalho previsto; (e) filtro sintético (seletividade) não é um filtro de negócio real — escolha por controle experimental, limitação a declarar.

**Q12. "Qual a contribuição original disto?"**
R: Comparação **sistemática e reproduzível** dos três sistemas sob o mesmo algoritmo (HNSW), com metodologia ANN-Benchmarks (curvas recall×QPS) e três cenários que mapeiam perfis reais de RAG, incluindo o eixo de **seletividade de filtro** — lacuna apontada na própria introdução (faltam estudos comparativos sistemáticos pgvector × especializados em condições controladas).

---

## Parte 5 — Glossário relâmpago (1 linha)
- **Embedding:** vetor denso que representa o significado de um texto.
- **ANN:** busca aproximada de vizinhos — troca exatidão por velocidade.
- **HNSW:** índice de grafo hierárquico; parâmetros M (conexões) e ef (esforço de busca).
- **recall@K:** fração dos K verdadeiros vizinhos que o sistema recuperou.
- **QPS:** consultas por segundo (throughput).
- **p95/p99:** latência que 95%/99% das consultas não ultrapassam.
- **RAG:** LLM + recuperação de contexto num banco vetorial.
- **VSM:** modelo vetorial clássico de RI (Salton 1975); raiz dos embeddings.
- **TF-IDF:** esquema de peso termo-frequência × raridade no corpus.
- **Seletividade:** fração da base que passa o filtro (1%/10%/50%/100% no Cenário B).
- **Ground truth:** resultado da busca exata, referência para medir recall.
- **Pré/pós/inline-filtering:** quando o filtro é aplicado em relação à busca vetorial (ACORN).
- **VDBMS:** sistema de gerenciamento de banco vetorial (Pan et al. 2023).

## Parte 6 — Checklist da véspera
- [ ] Sei o pitch de 60s sem ler.
- [ ] Sei dizer o que **não** temos ainda (Q1) sem gaguejar.
- [ ] Sei explicar M vs. ef e por que varremos ef.
- [ ] Sei justificar cada escolha pela alternativa rejeitada (Parte 2).
- [ ] Tenho a resposta do Cenário B / seletividade na ponta da língua (Q7, Q8).
- [ ] Sei a diferença especializado vs. extensão (Pan et al.) e o trade-off.
- [ ] Consigo desenhar o fluxo do `code/` num quadro.
- [ ] Levo, de propósito, as ameaças à validade (Q11) — passa maturidade.

## Backlinks
- [[decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]
- [[decisões/2026-05-10-cenario-a-queries-warmup]]
- [[decisões/2026-05-19-cronograma-canonico-relatorio]]
- [[referência/vector-space-model]]
- [[referência/busca-aproximada-vizinhos-proximos]]
- [[referência/bancos-de-dados-vetoriais]]
- [[referência/rag-retrieval-augmented-generation]]
- [[referência/metodologia-benchmarking-ann]]
- [[sessões/2026-05-19]]
