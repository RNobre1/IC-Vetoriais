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
- **O relatório foi corrigido (2026-05-19) e agora é honesto:** removidos os overclaims — o Resumo, Resultados e Considerações **não afirmam mais** que a fase 100k/500k foi concluída nem que há resultados preliminares; a Seção 5 está com `\todo` explícitos e a Seção 6 não conclui nada (depende dos resultados). Se perguntarem pelos números: *"O ambiente e os scripts dos Cenários A e B estão prontos, testados (175 testes) e validados em smoke ponta-a-ponta nos três sistemas; a execução em escala 100k/500k é o passo imediato da Etapa 3. A seção de resultados está com os placeholders demarcando exatamente o que será preenchido."* Honestidade > fingir.
- **Cenário B — relatório já alinhado ao implementado (2026-05-19):** a Seção 4 agora descreve o que de fato existe — o filtro categórico (categoria/área/data) entra como **motivação** de RAG corporativo, e a **operacionalização experimental** é o predicado de seletividade controlada (atributo numérico uniforme, `seletor < p`, varredura 1/10/50/100%, GT filtrado por seletividade), citando ACORN. Não há mais contradição texto×código. A justificativa de por que seletividade numérica está em Q7.

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
| 8 | **Cenário B: atributo numérico `seletor` uniforme + `seletor < p`; GT filtrado por seletividade** | Filtro categórico (área/data); reusar GT global do Cenário A | Numérico uniforme decorrelacionado dá **seletividade exata e parametrizável** (1/10/50/100%) sem re-seedar, alinhado a ACORN/Big-ANN. GT tem que ser o **top-K exato dentro do subconjunto filtrado** — comparar com o GT global puniria o sistema por excluir corretamente o que o filtro remove. ADR `2026-05-19-cenario-b-seletividade-gt-filtrado`. **(Relatório já alinhado a isto na Seção 4; ver Q7.)** |
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

**Q7. "Como exatamente é o filtro do Cenário B? Por que numérico e não por área/data?"**
R: *"A motivação é o filtro de metadados típico de RAG corporativo (categoria, área, data). Mas o que governa o desempenho da busca vetorial sob filtro não é a natureza semântica do atributo e sim a **seletividade** do predicado — a fração da base que passa. Isso é o caráter predicate-agnostic mostrado pelo ACORN (Patel et al., 2024). Por isso operacionalizamos o filtro de forma controlada: um atributo numérico sintético uniforme e o predicado `seletor < p`, varrendo seletividade em 1%, 10%, 50% e 100%. Assim isolamos o efeito da seletividade, o que um filtro 'área/data' concreto não permitiria de forma limpa. O recall é medido contra a busca exata restrita ao subconjunto que passa o filtro, calculada por nível de seletividade."* Isso é ponto a favor (rigor experimental). O relatório (Seção 4) já está alinhado a essa descrição; ADR `2026-05-19-cenario-b-seletividade-gt-filtrado`.

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

## Parte 5 — Glossário completo (sem pontas soltas)

> Tudo que pode cair na conversa, com exemplo numérico onde a definição sozinha não basta. Se você só decorar esta parte, já se vira.

### A) Representação de texto
- **Embedding:** vetor de números (denso) que representa o *significado* de um texto. No projeto: 384 números por passage. Textos de sentido parecido → vetores próximos no espaço.
- **Vetor denso vs. esparso:** *esparso* = quase tudo zero, dimensão = tamanho do vocabulário (VSM/TF-IDF). *Denso* = todas as dimensões com valor, poucas centenas de dimensões (embeddings). Denso captura sinônimo; esparso não.
- **Dimensionalidade:** quantidade de números no vetor. MiniLM = 384; mpnet = 768; BGE-large = 1024. Maior = mais expressivo, porém mais memória/disco e similaridade mais cara.
- **Normalização L2:** dividir o vetor pelo seu comprimento, deixando-o com "tamanho" 1. Consequência usada no projeto: com vetores L2-normalizados, **produto interno = similaridade de cosseno** (a operação mais rápida serve para os dois).
- **Similaridade de cosseno:** cosseno do ângulo entre dois vetores = (A·B)/(‖A‖‖B‖). Vale de −1 a 1; 1 = mesma direção (muito similar). Mede orientação, ignora tamanho.
- **Produto interno (dot product):** soma dos produtos coordenada a coordenada (A·B). Se os vetores são unitários (L2), é igual ao cosseno.
- **Distância vs. similaridade:** distância grande = pouco similar. pgvector usa o operador `<=>` (distância de cosseno = 1 − similaridade).
- **VSM (Vector Space Model):** modelo clássico de recuperação de informação (Salton, Wong & Yang, 1975). Documento e consulta viram vetores de termos; relevância = proximidade. Raiz conceitual dos embeddings.
- **TF-IDF:** esquema de peso do VSM. TF = frequência do termo no documento; IDF = raridade do termo no corpus (termo comum pesa pouco). Peso = TF × IDF.
- **Sinonímia / polissemia / vocabulary mismatch:** as três fraquezas do VSM clássico. Sinonímia = palavras diferentes, mesmo sentido (carro/automóvel). Polissemia = mesma palavra, sentidos diferentes (banco). Vocabulary mismatch = consulta e documento usam palavras diferentes para a mesma ideia. Embeddings densos atenuam as três.
- **Sentence-BERT / rede siamesa:** Reimers & Gurevych (2019). Dois encoders BERT idênticos (pesos compartilhados = "siamesa") treinados para que o cosseno entre os embeddings reflita similaridade — viabiliza comparar milhões de sentenças rápido. É a família do `all-MiniLM-L6-v2`.
- **BERT / LLM:** BERT = modelo de linguagem que entende contexto; base do Sentence-BERT. LLM = *Large Language Model* (modelo de linguagem grande, e.g. GPT/Llama) — o gerador no RAG.

### B) Busca e índices
- **k-NN (K vizinhos mais próximos):** dado um vetor de consulta, os K vetores mais similares da base. K=10 no projeto.
- **Busca exata:** compara a consulta com **todos** os N vetores. Resultado perfeito, custo linear (lento em milhões). É o nosso **ground truth**.
- **ANN (Approximate Nearest Neighbor):** busca *aproximada* — abre mão de achar exatamente os K certos em troca de ser muito mais rápida, mantendo recall alto.
- **HNSW (Hierarchical Navigable Small World):** Malkov & Yashunin (2018). Índice ANN em grafo de várias camadas: camadas de cima (poucos nós, saltos longos) levam rápido para perto; camadas de baixo (densas) refinam. Índice principal nos 3 SGBDs.
- **M:** nº de conexões (vizinhos) por nó no grafo HNSW. Maior M → melhor recall, mais memória, indexação mais lenta. (= parâmetro *M* do paper; no código exposto como `m`.)
- **ef_construction:** tamanho da lista de candidatos durante a **construção** do índice. Maior → índice melhor, build mais lento.
- **ef_search (ef):** tamanho da fila de candidatos durante a **busca**. Maior ef → mais recall, mais latência. **É o parâmetro que varremos** para traçar a curva recall×QPS.
- **IVFFlat:** outro índice ANN (clusteriza e busca nos clusters perto). pgvector também oferece; **não usamos** (padronizamos HNSW).
- **FAISS:** biblioteca da Meta para busca vetorial. Usamos só o `IndexFlatIP` (produto interno exato) para gerar o ground truth — não como sistema avaliado.
- **`IndexFlatIP`:** índice FAISS de produto interno **exato** (Flat = sem aproximação, IP = inner product). Com L2-norm, dá o cosseno exato → referência de ouro do recall.
- **Ground truth (verdade de referência):** o resultado da busca **exata**. Mede-se o recall dos SGBDs comparando com ele. No Cenário B há um ground truth por nível de seletividade.

### C) Métricas (com exemplo numérico)
- **recall@K:** dos K vizinhos que o sistema retornou, **quantos estão entre os K verdadeiros** (do ground truth exato), em média sobre as consultas. Fórmula por consulta: |retornados⋂verdadeiros| / K.
  - **Exemplo recall@10:** a busca exata diz que os 10 vizinhos certos da consulta são os ids {2,5,7,9,11,14,20,33,40,52}. O SGBD (HNSW) retornou {2,5,7,9,11,14,20,33,40,**99**} — acertou 9, errou 1 (trocou o 52 pelo 99). recall@10 = 9/10 = **0,90**. Médiando sobre todas as consultas tem-se o recall@10 do sistema. recall@10 = 1,0 significa busca aproximada idêntica à exata.
- **Precision vs. recall (se perguntarem):** aqui retornamos exatamente K, então precision@K = recall@K (mesmo denominador). Por isso só reportamos recall@K.
- **Latência:** tempo de uma consulta. Reportada em milissegundos, por consulta, descartando o warmup.
- **p50 / p95 / p99 (percentis de latência):** ordene as latências; **p50** = mediana (metade das consultas foi mais rápida que isso — caso típico); **p95** = 95% foram mais rápidas (5% piores); **p99** = a cauda (1% pior). 
  - **Exemplo:** 100 consultas, latências ordenadas. A 50ª = 4 ms → p50=4 ms. A 95ª = 11 ms → p95=11 ms. A 99ª = 28 ms → p99=28 ms. Interpretação: o usuário típico espera 4 ms, mas 1 em 100 espera 28 ms. p99 alto = experiência ruim sob carga, mesmo com p50 bom.
- **QPS (Queries Per Second) / throughput:** quantas consultas o sistema atende por segundo sob carga. Quanto maior, melhor.
- **Curva recall × QPS:** o resultado principal (estilo ANN-Benchmarks). Variando ef_search, cada ponto é um par (recall, QPS). A **curva inteira** é comparada, não um número solto — permite comparar sistemas "a recall igual, qual tem mais QPS?".
- **Trade-off recall × latência:** subir ef → recall sobe mas latência sobe (QPS cai). Não dá para maximizar os dois; a curva mostra o compromisso.
- **Footprint:** consumo de recurso — memória RAM do índice e espaço em disco por tamanho de dataset. (Ainda não medido — Etapa 3+.)
- **Tempo de indexação:** quanto leva para construir o índice HNSW após inserir os vetores. (Ainda não medido.)
- **Warmup (aquecimento):** primeiras consultas descartadas da medição (cache frio, JIT). Padrão 50; registrado no resultado.
- **Queries held-out:** vetores de consulta que **não** estão na base indexada. Mede generalização real; evita o trivial "achar a si mesmo". Estilo ANN-Benchmarks.

### D) Filtro / Cenário B
- **Metadado:** atributo associado ao vetor (categoria, data, autor…). No Cenário B, o filtro é sobre metadado.
- **Seletividade:** fração da base que **passa** o predicado do filtro. Seletividade 1% = só 1% dos vetores são elegíveis; 100% = ninguém é filtrado (= Cenário A).
  - **Exemplo:** base de 100.000 vetores, predicado `seletor < 0,10` → seletividade 10% → ~10.000 elegíveis; a busca vetorial só pode retornar entre esses.
- **`seletor`:** atributo numérico sintético, uniforme em [0,1), que cada vetor recebe no Cenário B. Predicado = `seletor < p`. Variar `p` (0,01 / 0,10 / 0,50 / 1,0) varia a seletividade de forma exata e controlada.
- **Predicate-agnostic:** propriedade (mostrada pelo ACORN) de que o desempenho da busca filtrada depende da **seletividade**, não do tipo semântico do atributo. É o que justifica usar um atributo numérico sintético em vez de "área/data".
- **Pré-filtragem / pós-filtragem / filtragem inline:** *pré* = filtra antes, busca só no subconjunto. *Pós* = busca vetorial, depois descarta o que não passa. *Inline* = aplica o filtro durante a navegação no grafo HNSW (ACORN mostra ser o mais eficiente). Os 3 SGBDs fazem de jeitos diferentes — daí esperar comportamentos distintos.
- **ACORN (Patel et al., 2024):** trabalho que sistematiza filtragem + busca vetorial e propõe a abordagem inline predicate-agnostic. Base teórica do Cenário B.

### E) Sistemas e infraestrutura
- **VDBMS:** *Vector Database Management System* — sistema para guardar/indexar/consultar vetores em escala. Pan, Wang & Li (2023) dividem em **especializados** vs. **extensões de SGBD**.
- **pgvector:** extensão do PostgreSQL que adiciona tipo `vector` e índices ANN (HNSW, IVFFlat). Representa "extensão de relacional".
- **Qdrant:** banco vetorial especializado, escrito em Rust; HNSW nativo; filtro por *payload*. Representa "especializado".
- **Weaviate:** banco vetorial especializado; esquema tipado, GraphQL. Rodado com `DEFAULT_VECTORIZER_MODULE=none` (vetor vem só do nosso pipeline). Representa "especializado".
- **Payload (Qdrant) / propriedade (Weaviate) / coluna (pgvector):** onde cada sistema guarda o metadado (inclui o `seletor`).
- **REST / gRPC:** protocolos de API dos serviços (HTTP REST e o binário gRPC). Weaviate v4 exige gRPC (porta 50051).
- **Docker / Docker Compose:** containerização. Compose sobe os 3 SGBDs juntos com um comando, versões fixas, isolados.
- **Healthcheck:** sonda que diz se o container está pronto (`pg_isready`, TCP, `/v1/.well-known/ready`). Evita medir antes do sistema aceitar conexão.
- **Snapshot de versões:** versões fixadas das imagens (pgvector 0.8.2-pg18, Qdrant 1.17.1, Weaviate 1.37.2) — reprodutibilidade; nunca `:latest`.

### F) RAG e dados
- **RAG (Retrieval-Augmented Generation):** Lewis et al. (2020). Consulta → embedding → recupera trechos similares no banco vetorial → injeta como contexto no LLM → resposta fundamentada. Reduz alucinação.
- **Alucinação:** quando o LLM inventa informação não fundamentada. RAG mitiga trazendo contexto real.
- **Passage / chunk:** trecho de texto indexado (no MS MARCO, um *passage* ≈ um parágrafo). Não fazemos re-chunking — usamos o passage como vem.
- **MS MARCO Passages:** dataset público (~8,8M passages) com licença de pesquisa e *qrels*. Fonte dos textos.
- **qrels (query relevance judgments):** anotações humanas de quais passages são relevantes para cada consulta. Permitem métricas de qualidade quando aplicável.
- **Subset determinístico:** recorte reprodutível — ordena por `passage_id`, pega os N primeiros. Qualquer pessoa obtém exatamente os mesmos dados.

### G) Engenharia / método
- **Reprodutibilidade:** qualquer pessoa repete o experimento e obtém o mesmo resultado. Garantida por versões pinadas, seeds fixos, amostragem determinística, ground truth exato.
- **Seed (semente):** número fixo que torna o "aleatório" repetível (e.g. permutação do `seletor`, seed 42).
- **Determinístico:** mesma entrada → sempre a mesma saída (sem variação por execução).
- **TDD (Test-Driven Development):** escrever o teste **antes** do código de produção. O projeto tem 175 testes (150 unitários + 25 de integração).
- **Smoke test:** teste rápido que valida que o pipeline roda ponta-a-ponta (não mede desempenho, só "não está quebrado").
- **Teste unitário vs. integração:** unitário = isolado, sem Docker (lógica pura). Integração = contra os 3 SGBDs reais rodando.
- **Lint:** verificação automática de estilo/erros do código (`ruff`). Roda no CI.
- **CI (Integração Contínua):** GitHub Actions roda lint + testes unitários a cada push. Integração roda local (decisão registrada).
- **ADR (Architecture Decision Record):** nota datada que registra uma decisão metodológica — contexto, opções, escolha, consequência. Ficam em `vault/decisões/`.
- **Protocolo / adaptador:** padrão de código — a medição fala com uma interface comum; cada SGBD é um adaptador. Permite testar sem Docker.
- **Pareto / fronteira:** num gráfico recall×QPS, a "fronteira" são os pontos não dominados (não dá para melhorar recall sem perder QPS). Forma de comparar sistemas.

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
