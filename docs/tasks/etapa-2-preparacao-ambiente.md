# Plano da Etapa 2 — Preparação de dados e ambiente

> **Status:** plano definido em 2026-05-05; executado ao longo de 2026-05-05 → 2026-05-10 (datas reais de execução; vide `vault/sessões/`).
> **Cronograma canônico:** Etapa 2 = **Mar–Abr** (tabela do relatório parcial, `docx/relatorio_parcial/secoes/08-cronograma.tex`, fonte de verdade). As datas `2026-05-*` abaixo são o log factual de execução, não o cronograma de planejamento.

## Objetivo
Entregar um ambiente experimental reproduzível com os 3 SGBDs vetoriais, pipeline de embeddings determinístico e scripts de benchmark prontos para a **Etapa 3** (cenários A e B em 100k/500k).

## Decisões metodológicas que governam esta etapa
Cada item da Etapa 2 deve respeitar literalmente estas ADRs. Não revisitar sem motivo técnico forte registrado em nova ADR.

- [[../../vault/decisões/2026-04-28-sistemas-avaliados]] — pgvector + Qdrant + Weaviate
- [[../../vault/decisões/2026-04-28-índice-hnsw-em-todos]] — HNSW nos três
- [[../../vault/decisões/2026-04-28-modelo-embedding-minilm]] — `sentence-transformers/all-MiniLM-L6-v2`, 384 dim, normalizado L2
- [[../../vault/decisões/2026-04-28-dataset-ms-marco]] — subset reproduzível de MS MARCO passages
- [[../../vault/decisões/2026-04-28-tamanhos-100k-500k-1m]] — três escalas; 1M só na Etapa 4
- [[../../vault/decisões/2026-04-28-cenarios-A-B-C]] — A pura, B com filtros, C carga mista RAG

## Arquitetura proposta

### Stack
- Python 3.11+
- Docker Compose (3 serviços principais + extras de teste)
- Pacotes: `sentence-transformers`, `psycopg[binary,pool]` (com `pgvector`), `qdrant-client`, `weaviate-client`, `faiss-cpu` (ground truth), `pytest`, `httpx`, `numpy`, `python-dotenv`
- Comandos uniformes via `Makefile`
- Reprodutibilidade: versões **pinadas** em `requirements.txt` (sem ranges)

### Layout em `code/`
```
code/
├── docker-compose.yml          # 3 SGBDs + healthchecks + volumes
├── pyproject.toml              # metadados do projeto
├── requirements.txt            # versões pinadas
├── Makefile                    # comandos uniformes
├── README.md                   # como rodar (em PT-BR)
├── .env.example                # variáveis de configuração
├── pipeline/
│   ├── __init__.py
│   ├── ms_marco_loader.py      # download + sampling determinístico
│   └── embeddings.py           # geração + cache local em data/
├── seeders/
│   ├── __init__.py
│   ├── pgvector_seeder.py
│   ├── qdrant_seeder.py
│   └── weaviate_seeder.py
├── ground_truth/
│   ├── __init__.py
│   └── exact_search.py         # FAISS IndexFlatIP para recall@K
├── benchmarks/
│   ├── __init__.py
│   ├── cenario_a.py            # busca pura
│   ├── cenario_b.py            # busca com filtros
│   └── cenario_c.py            # esqueleto p/ Etapa 4
├── lib/
│   ├── __init__.py
│   ├── metrics.py              # p50/p95/p99, QPS, recall@K
│   └── reporting.py            # JSON normalizado + (opcional) plot Pareto
└── tests/
    ├── conftest.py
    ├── unit/                   # rápidos, sem Docker
    └── integration/            # contra Docker rodando
```

### Reprodutibilidade
- Versões pinadas em `requirements.txt` e tags Docker imutáveis (não usar `:latest`).
- Seeds fixos para sampling, particionamento, shuffle.
- Embeddings cached em `data/embeddings/<dataset>-<model>-<version>.npy` com hash determinístico.
- Subsets de MS MARCO determinísticos (ordenação por `passage_id`, slice top-N).
- Hardware documentado em cada nota de [[../../vault/experimentos/]].

## Cronograma diário (4 dias)

### Dia 1 — 2026-05-05 ✅ CONCLUÍDO
**Foco: esqueleto de `code/`, docker-compose dos 3 sistemas, smoke test em TDD e CI mínimo no ar.**

Entregáveis:
- [x] Esqueleto do projeto Python em `code/`:
  - `pyproject.toml` (com config de `ruff` para lint+format e `pytest` markers)
  - `requirements.txt` com versões pinadas + `requirements.lock` (transitivos resolvidos)
  - `Makefile` (alvos: `up`, `down`, `smoke`, `test`, `test-unit`, `test-integration`, `lint`, `fmt`, `clean`, `deps`, `logs`, `help`)
  - `README.md` (esqueleto em PT-BR com troubleshooting)
  - `.env.example`
- [x] `code/docker-compose.yml` com:
  - `postgres-pgvector` (`pgvector/pgvector:0.8.2-pg18-bookworm` — Postgres 18.3 + pgvector 0.8.2; *bumpado em 2026-05-06*)
  - `qdrant` (`qdrant/qdrant:v1.17.1` — *bumpado em 2026-05-06*)
  - `weaviate` (`semitechnologies/weaviate:1.37.2` — *bumpado em 2026-05-06*)
  - Healthchecks (TCP/HTTP/`pg_isready`) com `start_period` e retries adequados
  - Named volumes gerenciados pelo Docker
  - Porta gRPC 50051 do Weaviate exposta (necessária para o cliente v4)
- [x] **Smoke test em TDD** (escrito antes do `docker compose up`):
  - `tests/integration/test_smoke.py` — 6 cenários cobrindo conexão + CREATE + INSERT + SEARCH nos 3 sistemas
  - `tests/unit/test_basic.py` — mantém o pipeline de CI vivo
  - **Resultado:** 6/6 integrados verde, 2/2 unitários verde após `docker compose up -d --wait`.
- [x] **CI mínimo no GitHub Actions** (`.github/workflows/test.yml`):
  - Lint via `ruff check` + `ruff format --check`
  - Testes unitários via `pytest tests/unit`
  - Cache de pip
  - Executa em push/PR para `main`
- [x] **ADR**: [[../../vault/decisões/2026-05-05-versoes-imagens-docker]] (versões fixadas — *superseded em 2026-05-06* por [[../../vault/decisões/2026-05-06-bump-versoes-sgbds]] que atualizou as 3 imagens para o snapshot atual).
- [x] **Lição**: [[../../vault/lições/2026-05-05-armadilhas-dia-1-etapa-2]] (3 armadilhas corrigidas: httpx vs weaviate, psycopg sem wheel py3.14, gRPC do Weaviate).

**Estado de infraestrutura ao final do Dia 1:** containers `ic-pgvector`, `ic-qdrant`, `ic-weaviate` de pé e healthy; venv `code/.venv` instalado; `code/.env` aplicado.

### Dia 2 — 2026-05-06 ✅ CONCLUÍDO
**Foco: pipeline de embeddings + seeders dos 3 sistemas.**

> Antes do Dia 2 propriamente, abrimos a sessão com o **bump das versões dos SGBDs** (vide [[../../vault/decisões/2026-05-06-bump-versoes-sgbds]] e [[../../vault/sessões/2026-05-06]]). Smoke seguiu 6/6 verde após o bump.

Entregáveis:
- [x] `pipeline/ms_marco_loader.py`:
  - `download_collection_targz(dest, *, force)` — baixa em `data/ms_marco/` (gitignored), valida MD5 (`87dd01826da3e2ad45447ba5af577628`, header oficial), pula se cache local correto.
  - `sample_passages(tsv, n)` — top-N por `passage_id` ascendente; robusto a TABs internos e linhas em branco.
- [x] `tests/unit/test_loader.py`: 17 testes (constantes, Passage imutável, sampling determinístico, casos de erro, lógica de skip-download mockada).
- [x] `pipeline/embeddings.py`:
  - `gerar_embeddings(textos, *, modelo_nome, cache_dir, batch_size, encoder_factory)` com cache em `data/embeddings/<sha256>.npy`.
  - Encoder injetável via factory (Protocol) — `SentenceTransformer` real é lazy-import; testes injetam `FakeEncoder`.
  - Lista vazia retorna `np.zeros((0, 384), float32)` sem instanciar encoder.
- [x] `tests/unit/test_embeddings.py`: 15 testes (constantes do modelo, determinismo da chave de cache, shape, norma L2, cache hit/miss, reprodutibilidade entre execuções, isolamento por `modelo_nome`).
- [x] `seeders/pgvector_seeder.py`, `seeders/qdrant_seeder.py`, `seeders/weaviate_seeder.py`:
  - Assinatura uniforme `seed_X(*, vetores, metadata, <cliente>, nome, m, ef_construction)`.
  - Cria tabela/coleção/classe com índice HNSW; insere com IDs determinísticos (0..N-1, ordem de entrada).
  - Parâmetro `M` do paper HNSW exposto como `m` (PEP 8) — semântica preservada em docstring.
- [x] `tests/integration/test_seeders.py`: 6 testes (1000 vetores 384-D normalizados, seed=42; metadata sintético cat-A/cat-B 50/50). Cada sistema valida `count == 1000` e `top-1(vetor[0]) → id 0`.
- [x] Download de MS MARCO em background (`collection.tar.gz` ~1 GB, ~3 GB descompactado) — disparado no início do dia, valida MD5 ao concluir.

**Resultado da suíte ao final do Dia 2:** 46/46 testes verde (34 unit + 12 integration). Lint+format limpos.

### Pré-Dia 3 — 2026-05-10 ✅ CONCLUÍDO
**Foco: habilitar geração real de embeddings antes do ground truth.**

> Não estava no plano original; inserido porque o Dia 2 fechou com `sentence-transformers` ainda não instalado (apenas o `FakeEncoder` nos testes). Vide [[../../vault/sessões/2026-05-10]].

Entregáveis:
- [x] MD5 de `data/ms_marco/collection.tar.gz` conferido (`87dd01826da3e2ad45447ba5af577628`); `collection.tsv` descompactado.
- [x] `sentence-transformers==5.4.1` + `torch==2.11.0+cpu` pinados com `--extra-index-url` CPU-only do PyTorch. `requirements.lock` regenerado (39 → 70 entries).
- [x] `tests/integration/test_embeddings_real.py` (4 testes, marker `slow`) — encoder real, cache, subset MS MARCO.
- [x] **Experimento**: [[../../vault/experimentos/2026-05-10-validacao-embeddings-100-passages]] — 100 passages, shape `(100,384)`, norma L2 `1.0 ± 1.2e-7`, determinismo confirmado.
- [x] **Lição**: [[../../vault/lições/2026-05-10-torch-cpu-only-vs-cuda]] (pip puxa build CUDA ~3 GB sem `--extra-index-url`; disco estourou).
- [x] **Lição**: [[../../vault/lições/2026-05-10-fake-encoder-hash-flake]] (flake preexistente do Dia 2: `hash()` Python no `FakeEncoder` → SHA-256).

### Dia 3 — 2026-05-10 / 2026-05-19 ✅ CONCLUÍDO
**Foco: ground truth + Cenário A + Cenário B.**

> Datado 2026-05-07 no plano original; executado em 2026-05-10/2026-05-19 (datas reais). **Dia 3 CONCLUÍDO:** `ground_truth` (+`top_k_exato_filtrado`), `lib/metrics`, `lib/reporting` (+`salvar_curva`), **Cenário A completo** e **Cenário B completo** (GT filtrado + seeders com `seletor` + adaptadores `BuscadorFiltravel` + orquestração + CLI `make bench-B` + smoke real, em TDD) + 2 ADRs metodológicas.

Entregáveis:
- [x] `ground_truth/exact_search.py`:
  - FAISS `IndexFlatIP` (produto interno, vetores já normalizados). API: `top_k_exato(base, queries, k) -> (scores, ids)`.
  - ⚠️ Retorna em memória; **persistência em `data/ground_truth/` ainda não** — será feita junto com `lib/reporting.py` / `cenario_a.py`.
- [x] `tests/unit/test_ground_truth.py`: 12 testes (recall vs. si = 1.0, determinismo bit-a-bit, 6 validações de borda).
- [x] `lib/metrics.py`: p50/p95/p99 (via `numpy.percentile`), QPS, recall@K (consome `top_k_exato`).
- [x] `tests/unit/test_metrics.py`: 21 testes (percentis em distribuição conhecida, recall em casos de canto e bordas).
- [x] `lib/reporting.py`: JSON normalizado em `code/results/` (inclui persistir o ground truth em `data/ground_truth/`).
  - `ResultadoBenchmark` (dataclass `frozen/slots`); `salvar_resultado` (JSON `sort_keys` + `ensure_ascii=False`, nome determinístico); `salvar_ground_truth`/`carregar_ground_truth` (`.npz` round-trip).
- [x] `tests/unit/test_reporting.py`: 11 testes (imutabilidade, padrão do nome, determinismo do JSON, acentos sem escape, round-trip semântico, round-trip do `.npz`, validações de shape/2-D).
- [x] `benchmarks/cenario_a.py` — **Cenário A completo (orquestração + adaptadores + CLI + smoke real)**:
  - [x] Decisões metodológicas fixadas em ADR [[../../vault/decisões/2026-05-10-cenario-a-queries-warmup]]: queries = passages held-out (ANN-Bench); warmup descartado (default 50, registrado no JSON); escopo Etapa 2 = script + smoke N pequeno.
  - [x] Protocol `BuscadorVetorial` (`nome`, `configurar_ef_search`, `buscar_uma`) — desacopla orquestração da API de cada SGBD.
  - [x] `medir_sistema(...)`: varre `efSearch`, warmup+descarte, mede latência por query, calcula p50/p95/p99 + QPS + recall@k (consome `lib.metrics` + `lib.reporting`). 1 `ResultadoBenchmark` por ef.
  - [x] `tests/unit/test_cenario_a.py`: 12 testes (estrutura, ordem dos ef, warmup descartado, recall 1.0/0.0, métricas plausíveis, 4 validações de borda).
  - [x] Adaptadores concretos `PgvectorBuscador` / `QdrantBuscador` / `WeaviateBuscador` em `benchmarks/buscadores.py` (`configurar_ef_search`: `SET hnsw.ef_search` / `SearchParams(hnsw_ef=)` / `Reconfigure.Vectors.update`).
  - [x] Smoke de integração ponta-a-ponta `tests/integration/test_buscadores.py`: seed pequeno (N=300) + queries held-out + ground truth FAISS + `medir_sistema` real nos 3 SGBDs com sweep `efSearch ∈ {16,64}`. 3/3 verde. Pegadinha Weaviate registrada em [[../../vault/lições/2026-05-10-weaviate-config-update-vector-config]].
  - [x] CLI `benchmarks/run_cenario_a.py` + alvo `make bench-A` (vars `N Q K EF WARMUP SYS`): pipeline → split held-out → ground truth → seed idempotente → `medir_sistema` nos 3 SGBDs → `salvar_curva`. Partes puras (`parse_args`, `split_embeddings`, `timestamp_utc`) com 10 testes unitários.
  - [x] `lib/reporting.salvar_curva`: 1 JSON por sistema com a curva inteira (corrige perda de ponto em sweep). 6 testes.
  - [x] **Smoke real validado**: `make bench-A N=200 Q=20 EF=16,64 WARMUP=2` gravou 3 curvas em `results/`. Weaviate exibiu `ef↑ → recall↑` (0.905→1.0), provando o controle de efSearch ponta-a-ponta. 3 bugs encontrados e corrigidos no caminho — [[../../vault/lições/2026-05-10-smoke-cli-cenario-a-make-or-e-colisao-nome]].
- [x] `benchmarks/cenario_b.py` — **Cenário B completo (GT filtrado + seeders + adaptadores + orquestração + CLI + smoke real)**:
  - [x] Decisões metodológicas em ADR [[../../vault/decisões/2026-05-19-cenario-b-seletividade-gt-filtrado]]: predicado = atributo numérico `seletor` uniforme decorrelacionado (`seletor < p`); recall@K contra GT **filtrado por seletividade** (não o GT global do A); p=1.0 = âncora sem filtro.
  - [x] `ground_truth.exact_search.top_k_exato_filtrado(base, queries, *, seletor, p, k)` — FAISS no subconjunto filtrado, ids remapeados para os originais, `k` clampado se `|subconjunto|<k`. +10 testes (22/22 em `test_ground_truth.py`).
  - [x] Seeders gravam `seletor`: pgvector coluna `real`, Weaviate `DataType.NUMBER`, Qdrant payload + **índice de payload** condicional (filtered-ANN comparável). Cenário A intacto (`metadata=None`). +3 testes integração (9/9 em `test_seeders.py`).
  - [x] `BuscadorFiltravel` (Protocol estende `BuscadorVetorial`) + `buscar_uma_filtrada(query, k, *, p_max)` nos 3 adaptadores (`WHERE seletor<%s` / Qdrant `Filter(Range(lt))` / Weaviate `Filter.less_than`). Smoke `tests/integration/test_buscadores_filtrado.py` 3/3 verde.
  - [x] `cenario_b.medir_sistema_filtrado(...)`: varre `seletividade × efSearch`, recall vs `gt_por_seletividade[p]`, `cenario="B"`, padding `-1` p/ subconjunto < k. `tests/unit/test_cenario_b.py`: 15 testes.
  - [x] CLI `benchmarks/run_cenario_b.py` + alvo `make bench-B` (vars `N Q K EF WARMUP SYS SEL`): pipeline → `sintetizar_seletor` (permutação determinística decorrelacionada) → GT por p → seed idempotente com `seletor` → `medir_sistema_filtrado` → `salvar_curva`. Partes puras com 10 testes.
  - [x] **Smoke real validado** (2 runs consecutivos, idempotente): `make bench-B N=200 Q=20 EF=16,64 WARMUP=2 SEL=0.1,1.0` gravou 3 curvas + GT npz por seletividade; recall ponta-a-ponta nos 3 SGBDs. Diferenciação real virá em 100k/500k (Etapa 3).

### Dia 4 — 2026-05-08
**Foco: Cenário C esqueleto, ferramental, README.**

Entregáveis:
- [ ] `benchmarks/cenario_c.py`:
  - **Esqueleto apenas** — não rodar carga real (1M fica para Etapa 4)
  - Estrutura: produtor concorrente de inserções + consumidor de buscas
  - Mede impacto de taxa de inserção (0, 10, 100, 1000 ins/s) em latência p99 de leitura
- [ ] `Makefile` estendido com `seed`, `bench-A`, `bench-B`, `bench-C-dryrun` (alvos básicos `up`, `down`, `smoke`, `test*`, `lint`, `fmt`, `clean` já vieram do Dia 1)
- [ ] `code/README.md` finalizado em PT-BR com:
  - Pré-requisitos (Docker ≥ 24, Python 3.11+, ~8 GB livres em disco, ~12 GB RAM em pico)
  - Comandos (mesmos do Makefile)
  - Troubleshooting (porta ocupada, container saudável mas Python falha conectar, etc.)
- [ ] CI estendido (decisão pendente — avaliar Dia 4): ampliar workflow para rodar testes de integração com `services:` do GitHub Actions. Custo: workflow mais frágil, runners gratuitos limitados. Recomendação atual: **manter integração local**, só ampliar se o orientador requisitar.
- [ ] Smoke completo de validação: `make up && make seed N=10000 && make bench-A` produz JSON em `code/results/`

## Definição de "pronto" para a Etapa 2
1. `make up` sobe os 3 containers em ≤ 60 s; `make smoke` passa.
2. `make seed N=100000` carrega 100k embeddings em cada um dos 3 sistemas em ≤ 30 min (notebook-alvo).
3. `make bench-A` produz `code/results/cenario_a_<sistema>_<N>_<timestamp>.json` para cada um dos 3 sistemas.
4. Cobertura de testes:
   - Unitários: ≥ 80 % de linhas em `pipeline/`, `lib/`, `ground_truth/`
   - Integração: ≥ 1 teste por seeder, ≥ 1 teste por cenário (A e B)
5. `code/README.md` permite a um terceiro sem contexto reproduzir `make up && make smoke` em ≤ 15 min.
6. Toda decisão técnica nova surgida durante a execução vira ADR em `vault/decisões/`.

## Riscos & mitigações
1. **Hardware apertado em 1M.** 16 GB RAM com 3 SGBDs simultâneos é justo. *Mitigação:* na Etapa 2 não rodar 1M; deixar a infra preparada e validar isoladamente um sistema por vez quando chegar a Etapa 4.
2. **Download do MS MARCO (~3 GB).** Pode falhar em conexões instáveis. *Mitigação:* iniciar cedo no Dia 2; validar MD5; permitir retomada incremental.
3. **Drivers Python (psycopg, qdrant-client, weaviate-client).** Versões podem quebrar entre minor releases. *Mitigação:* pinar versões testadas; documentar em `requirements.txt`.
4. **Tentação de pular TDD para "ganhar tempo".** Bugs silenciosos em scripts de benchmark contaminam todos os experimentos da Etapa 3. *Mitigação:* TDD inegociável (Regra 2 do docs/metodologia.md). Cada peça de código nasce com teste.
5. **Cluster HPC do IEG não confirmado.** Se viabilizar, parte da Etapa 2 precisará revisão. *Mitigação:* manter scripts portáveis (sem dependência forte do `docker compose` específico do notebook).

## Pendências decisórias durante a execução
A registrar como ADR no momento em que a decisão for tomada:

- Versões exatas das imagens Docker (Dia 1).
- Estratégia de chunking (passage = parágrafo do MS MARCO sem chunking adicional, ou re-chunking?). Default: usar passage como vem.
- Ampliação do CI para integração via `services:` do GitHub Actions (avaliação no Dia 4).

## Backlinks
- [[../../vault/decisões/2026-04-28-sistemas-avaliados]]
- [[../../vault/decisões/2026-04-28-cenarios-A-B-C]]
- [[../../vault/decisões/2026-04-28-modelo-embedding-minilm]]
- [[../../vault/lições/2026-05-05-rigor-citacoes-abnt]]
- [[../../vault/referência/metodologia-benchmarking-ann]]
