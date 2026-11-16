# IC — Bancos de Dados Vetoriais

> Iniciação Científica · UFOPA / IEG · 2026

**TL;DR (English):** Undergraduate research project comparing PostgreSQL + pgvector against
two specialized vector databases (Qdrant and Weaviate) for semantic search. All three use
the same HNSW index and parameters over 384-dim all-MiniLM-L6-v2 embeddings of MS MARCO
passages, at 100k, 500k and 1M vectors, in three scenarios: plain k-NN search, filtered
search, and search under concurrent inserts. Every table and figure of the final report is
generated from the versioned result files in this repository.

---

## Pergunta de pesquisa

O PostgreSQL com a extensão `pgvector` tem desempenho competitivo com bancos vetoriais
especializados em busca semântica, e em quais condições a diferença passa a pesar?

## O que foi medido

- **Sistemas:** PostgreSQL 18.3 + pgvector 0.8.2, Qdrant 1.17.1 e Weaviate 1.37.2, em Docker, com versões fixadas.
- **Índice:** HNSW nos três, com M = 16, ef_construction = 200 e distância de cosseno; `ef_search` em 16, 32, 64, 128 e 256.
- **Dados:** passagens do MS MARCO, `all-MiniLM-L6-v2` (384 dimensões), em 100 mil, 500 mil e 1 milhão de vetores, com 1.000 consultas separadas da base.
- **Cenários:**
  - **A** — busca pura (top-10), cinco repetições por ponto;
  - **B** — busca com filtro de metadados, em duas condições: padrão e equalizada (índice forçado);
  - **C** — busca sob inserção concorrente, a 0, 10, 100 e 1.000 inserções por segundo, em 1 milhão de vetores.
- **Métricas:** recall@10 contra a busca exata, latência (p50, p95, p99), QPS de cliente único, tempo de indexação, disco, e memória, CPU, *swap* e pressão de memória a cada segundo, separados por fase.
- **Hospedeiro:** notebook Dell G15 5530 (Intel i5-13450HX, 16 GiB), Fedora, com a frequência da CPU fixada na base durante a medição.

## Resultados

O relatório final está em [`docx/relatorio_parcial/`](docx/relatorio_parcial/) (o nome do diretório é histórico) e é compilado com `make pdf` nesse diretório. Os números ficam só lá: as tabelas e as figuras são geradas pelo pacote [`code/analise/`](code/analise/) a partir dos arquivos de [`code/results/`](code/results/), e um teste falha se o que está no relatório divergir do que o código produz a partir dos dados.

As versões entregues estão marcadas com tags:

| Tag | Conteúdo |
|---|---|
| `relatorio-parcial` | relatório parcial, Cenários A e B em 100k e 500k |
| `relatorio-final` | relatório final, três cenários e três escalas |

## Estrutura do repositório

```
.
├── code/
│   ├── benchmarks/      # cenários A, B e C e o executor da sessão de medição
│   ├── seeders/         # carga e criação do índice em cada sistema
│   ├── ground_truth/    # busca exata (Faiss) usada como referência do recall
│   ├── pipeline/        # leitura do MS MARCO e geração de embeddings com cache
│   ├── lib/             # métricas, amostrador de recursos e gravação dos resultados
│   ├── analise/         # tabelas, figuras e trechos de código do relatório
│   ├── scripts/         # roteiro da sessão de medição
│   ├── results/         # resultados versionados; sessoes/<id>/ guarda ambiente, marcos e monitor
│   └── tests/           # testes unitários (CI) e de integração
├── docx/relatorio_parcial/  # relatório final em LaTeX (secoes/, gerado/, figuras/)
├── docs/                # metodologia e runbook de medição
└── vault/               # decisões, experimentos, lições e sessões de trabalho
```

`data/` (dataset e embeddings) não é versionado: o MS MARCO é baixado sob demanda no primeiro uso.

## Reprodução

Pré-requisitos: Docker com Compose v2, Python 3.11 e cerca de 16 GiB de RAM para a escala de 1 milhão.

```bash
cd code
make deps                 # venv com dependências pinadas
cp .env.example .env
make up && make smoke     # sobe os três sistemas e valida conexão, escrita e busca
make test                 # testes unitários
make sessao SESSAO_ID=<id>   # sessão completa (destrutiva: recria os volumes)
make tabelas              # regenera tabelas, figuras e trechos do relatório
```

O passo a passo da medição, com ensaio em carga reduzida e verificações do hospedeiro, está em [`docs/runbook-medicao-dell.md`](docs/runbook-medicao-dell.md). As decisões de protocolo estão em [`vault/decisões/`](vault/decisões/).

## Equipe

- **Bolsista:** Rafael Nobre de Souza
- **Orientador:** Prof. Dr. Celson Pantoja Lima — UFOPA / IEG
- **Instituição:** Universidade Federal do Oeste do Pará — Instituto de Engenharia e Geociências, Santarém-PA
- **Curso:** Bacharelado em Ciência da Computação

## Licença

- **Código** (`code/`, scripts de `docx/`, `.github/`): [MIT](LICENSE).
- **Dados de medição, texto e figuras** (`code/results/`, `docx/relatorio_parcial/`, `docs/`, `vault/`): [CC BY 4.0](LICENSE-CC-BY-4.0.txt). Cite como: SOUZA, Rafael Nobre de. *Comparação de desempenho de soluções de bancos de dados vetoriais para busca semântica: uma análise entre pgvector e bancos de dados especializados*. Relatório Final de Iniciação Científica (orientador: Prof. Dr. Celson Pantoja Lima). Santarém: UFOPA/IEG, 2026.
- **Fora das licenças acima:** logotipos e modelos institucionais em `docx/` pertencem às respectivas instituições. O MS MARCO não está no repositório e segue os termos de uso próprios.
