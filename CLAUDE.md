# IC — Bancos de Dados Vetoriais (UFOPA/IEG)

Você está dentro do diretório de trabalho de uma Iniciação Científica. Este arquivo é a fonte de verdade sobre o projeto. Leia inteiro antes da primeira ação.

## Identidade do projeto

- **Título:** Comparação de Desempenho de Soluções de Bancos de Dados Vetoriais para Busca Semântica: uma análise entre pgvector e Bancos de Dados Especializados.
- **Bolsista:** Rafael Nobre de Souza.
- **Orientador:** Prof. Dr. Celson Pantoja Lima (UFOPA/IEG).
- **Instituição:** UFOPA — Universidade Federal do Oeste do Pará / Instituto de Engenharia e Geociências, Santarém-PA.
- **Curso:** Bacharelado em Ciência da Computação.

## Objetivo

Comparar experimentalmente PostgreSQL+pgvector contra bancos vetoriais especializados (Qdrant, Weaviate) em cenários de busca semântica e RAG. Métricas: latência (p50/p95/p99), throughput (QPS), recall@K vs busca exata, footprint de memória/disco, tempo de indexação.

## Estrutura do diretório

```
.
├── CLAUDE.md           # este arquivo
├── vault/              # Obsidian — notas, fichamentos, drafts, logs
├── code/               # docker-compose, scripts Python, benchmarks
├── data/               # datasets baixados (gitignored)
└── docx/               # entregáveis: projeto LaTeX do relatório + arquivos legados
    ├── relatorio_parcial/   # projeto LaTeX (fonte canônica do parcial)
    │   ├── main.tex
    │   ├── refs.bib
    │   ├── secoes/01-08*.tex
    │   ├── Makefile         # targets pdf/watch/clean
    │   └── .gitignore       # artefatos LaTeX
    └── OFC- Planejamento... .docx   # legado, não tocar
```

Papéis bem separados — não misturar:

- **`vault/`** é o cérebro. Tudo que é leitura, decisão, draft, log de experimento mora aqui em markdown. Backlinks são parte da metodologia. Este vault é dedicado a este projeto — não há outros vaults Obsidian aqui.
- **`code/`** é onde os experimentos rodam. Docker Compose com 3 serviços (postgres+pgvector, qdrant, weaviate), pipeline de embeddings em Python (sentence-transformers), scripts de benchmark. Compose extra `docker-compose.ui.yml` para tooling de inspeção (Verba) — isolado por decisão metodológica (vide `vault/decisões/2026-05-05-isolamento-ui-vs-benchmark.md`).
- **`data/`** guarda datasets brutos. Em `.gitignore`. Volume grande, não versionar.
- **`docx/`** contém o **projeto LaTeX do relatório parcial** (`docx/relatorio_parcial/`, fonte canônica desde 2026-05-05) e arquivos `.docx` **legados** (e.g. planejamento original do edital). O nome do diretório é histórico — manter por enquanto pra preservar git history. PDF de saída (`main.pdf`) é o entregável; `.tex` é versionado e editado normalmente.

## Convenções do vault

### Tipos de nota

- **`vault/papers/`** — fichamentos de papers. Um arquivo por paper.
- **`vault/referência/`** — notas conceituais (HNSW, embeddings, VSM, RAG). Reusáveis e linkáveis a partir de papers e drafts.
- **`vault/decisões/`** — ADR-style (Architecture Decision Record). Cada decisão metodológica relevante = uma nota datada com contexto, opções, escolha e consequência.
- **`vault/experimentos/`** — log por execução de benchmark. Configuração, comando, resultados, observações.
- **`vault/drafts/`** — pedaços de texto destinados ao relatório. Linkam para papers e referência. Quando estabilizam, são copiados manualmente para `docx/`.
- **`vault/lições/`** — lições aprendidas e correções não-óbvias durante o trabalho (erros de citação, pegadinhas de configuração, ajustes de protocolo). Notas datadas, com causa raiz e regra de aplicação futura. Servem para não repetir o erro em sessões futuras.
- **`vault/sessões/`** — log condensado por sessão de trabalho. Onde paramos, o que foi entregue, decisões tomadas, próximo passo concreto. Alimenta o ritual de "início de sessão" (Regra 6).

### Frontmatter padrão para fichamentos

```yaml
---
tipo: paper
autores: ["Malkov, Y. A.", "Yashunin, D. A."]
ano: 2018
titulo: "Efficient and robust approximate nearest neighbor search using HNSW graphs"
venue: "IEEE TPAMI"
tags: [ann, hnsw, indexação]
citacao_abnt: "MALKOV, Y. A.; YASHUNIN, D. A. Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2018."
---
```

### Backlinks são parte do método

Ao escrever um fichamento, sempre linkar para as notas em `referência/` que o paper toca. Ao escrever um draft, sempre linkar para os papers que sustentam cada afirmação. Isso vira a base pra rastrear citações no momento da redação.

## Decisões metodológicas firmes

Não revisitar sem motivo técnico forte. Cada uma destas decisões tem uma nota em `vault/decisões/`.

- **Sistemas avaliados:** PostgreSQL+pgvector, Qdrant, Weaviate.
- **Índice principal:** HNSW nos três sistemas. Diferenças observadas refletem implementação e arquitetura, não algoritmo.
- **Modelo de embedding:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensões). Roda em CPU, viabiliza datasets grandes no hardware disponível.
- **Dataset textual:** subset de MS MARCO passages. Tem ground truth de relevância para cálculo de recall@K.
- **Tamanhos:** 100k, 500k, 1M embeddings.
- **Cenários:** A (busca pura), B (busca com filtros de metadados), C (carga mista RAG).
- **Inspiração metodológica:** ANN-Benchmarks (Aumüller, Bernhardsson & Faithfull, 2020). Reportar curvas recall × QPS, não números pontuais.
- **Orçamento bibliográfico:** 11 referências no parcial (já fechadas), ~20 no final. Não expandir sem necessidade clara.

## Cronograma comprimido (Mai-Dez 2026)

Cronograma original do edital era Jan-Dez. Execução começou em final de abril. Comprimimos:

- **Etapa 1 — Revisão e planejamento (Mai):** fundamentação teórica consolidada.
- **Etapa 2 — Ambiente + scripts (Mai-Jun):** docker-compose, pipeline de embeddings, scripts de benchmark.
- **Etapa 3 — Experimentos fase 1 (Jul):** cenários A e B em 100k e 500k.
- **▶ Relatório parcial entregue em Jul/2026** — fecha Etapas 1-3.
- **Etapa 4 — Experimentos fase 2 (Ago-Out):** datasets de 1M, cenário C, possível execução no Cluster HPC do IEG/UFOPA (condicional).
- **Etapa 5 — Análise e redação final (Nov-Dez).**
- **▶ Relatório final entregue em Dez/2026** — fecha Etapas 4-5.

## Hardware

Notebook Dell G15 5530, Fedora Linux. Intel i5-13450HX (10c/16t, até 4.6 GHz), 16 GiB DDR5 4800 MHz, NVMe Kingston 1 TB, NVIDIA RTX 3050 6 GB.

Possível extensão para Cluster HPC do IEG/UFOPA na etapa final, condicionada a viabilidade técnica e disponibilidade de acesso.

## Estilo de trabalho

- **Pair programming Akita/XP estrito.** O bolsista pilota e decide rumo. Você executa incrementalmente.
- **Em divergência técnica:** argumente com motivo + custo em 2-3 frases. Não capitule sem razão. Não bajule.
- **Sem postâmbulo** resumindo o que acabou de ser feito — o bolsista lê o diff.
- **PT-BR em tudo:** notas, código (variáveis técnicas em inglês quando padrão), commits, docstrings.
- **Commits pequenos e atômicos.** Mensagens em PT-BR no imperativo: "adiciona pipeline de embedding", "corrige cálculo de recall".
- **Trade-offs sempre como recomendação + motivo + custo**, não lista neutra.

## Limites operacionais

- Trabalhe **apenas neste diretório**. Não toque em vaults Obsidian externos, dotfiles do usuário, ou qualquer coisa fora deste projeto.
- **Não execute o Obsidian** via shell tooling. O vault é só uma pasta de markdown — escreva e leia arquivos diretamente.
- **Antes de criar nota nova no vault**, verifique se já existe template em `vault/_templates/` para esse tipo. Se sim, siga.
- **Antes de alterar uma decisão metodológica firme** (lista acima), pare e pergunte. Mudanças metodológicas têm custo de retrabalho alto.
- **Não edite arquivos `.docx` legados** (regra dura). Aplica a quaisquer `.docx` binários que sobreviveram à migração para LaTeX (e.g. `docx/OFC- Planejamento Rafael Nobre - 2026.docx`). Quando alteração em `.docx` legado for necessária, **gere um prompt pronto em PT-BR**, num bloco de código, para o Rafael copiar e enviar ao Claude da nuvem (que recebe o `.docx` como anexo) — nunca toque no arquivo. Leitura programática read-only (via `python-docx`) é permitida para informar o prompt; escrita não.
- **`.tex` em `docx/relatorio_parcial/` é editável normalmente.** Desde 2026-05-05 o relatório parcial migrou para LaTeX (vide `vault/decisões/2026-05-05-migracao-relatorio-para-latex.md`). Edits, refactor de seções, ajuste de bibliografia em `refs.bib`, mudanças em macros — tudo via Edit/Write como qualquer outro arquivo de código. Antes de mexer no `main.tex` ou seções, ler `docx/relatorio_parcial/README.md` que documenta convenções (macros `\todo`, `\code`, estilos de citação `\cite` e `\citeonline`).
- **Antes de rodar benchmarks, garantir ambiente limpo.** Executar `make ui-down` (Verba off) e confirmar via `docker compose ps` que só os 3 SGBDs alvo estão rodando. Vide `vault/decisões/2026-05-05-isolamento-ui-vs-benchmark.md`.

## O que fazer ao iniciar uma sessão

1. Confirme que está no diretório certo (`pwd`).
2. Olhe `vault/decisões/` para o estado atual de decisões.
3. Olhe a última nota em `vault/experimentos/` se houver — entende onde paramos.
4. Leia `git log --oneline -20` para o estado de código.
5. Espere o piloto definir o foco da sessão. Não comece nada sozinho.
