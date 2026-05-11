---
tipo: experimento
data: 2026-05-10
sistema: ""
cenário: validação-de-pipeline
dataset: MS MARCO passages (subset top-100 por passage_id)
dataset_tamanho_n: 100
tags: [pre-dia-3, validação, embeddings, sentence-transformers, minilm, etapa-2]
---

# Experimento: validação ponta-a-ponta da geração real de embeddings (100 passages MS MARCO)

## Objetivo
**Confirmar que o pipeline `ms_marco_loader → embeddings` produz, com o encoder REAL `sentence-transformers/all-MiniLM-L6-v2`, vetores no formato esperado (shape `(N, 384)`, `float32`, normalizados L2) e que o cache local é reutilizado de forma determinística.** Esta é a primeira execução real do pipeline — substitui o `FakeEncoder` usado nos testes unitários do Dia 2. Antes de prosseguir para o Dia 3 (ground truth FAISS, métricas, cenários A/B), precisamos confiar que a peça que gera os vetores está correta.

## Configuração

- **Sistema(s):** N/A para este experimento (não toca os 3 SGBDs alvo; é validação do pipeline de embeddings em si).
- **Versão(ões) e imagens Docker:** N/A. Os 3 containers continuam de pé (`make up`), mas não foram exercitados aqui.
- **Hardware:** Dell G15 5530 — Intel i5-13450HX (10c/16t, até 4.6 GHz), 16 GiB DDR5 4800 MHz, NVMe Kingston 1 TB, NVIDIA RTX 3050 6 GB. **Inferência em CPU** por decisão da ADR [[../decisões/2026-04-28-modelo-embedding-minilm]] (sem `torch.cuda`).
- **SO/runtime:** Linux 6.19.9 (Fedora 43), Python 3.14.3, `torch==2.11.0+cpu`, `sentence-transformers==5.4.1`.
- **Dataset:** subset reproduzível do MS MARCO passages v1 (`collection.tar.gz`, MD5 `87dd01826da3e2ad45447ba5af577628`, decodificado do header oficial `Content-MD5` em base64). Origem: `https://msmarco.z22.web.core.windows.net/msmarcoranking/collection.tar.gz`.
- **Tamanho N:** 100 passages.
- **Seleção:** top-100 por `passage_id` ascendente (`sample_passages(..., n=100)` → IDs **0..99** confirmados).
- **Modelo de embedding:** `sentence-transformers/all-MiniLM-L6-v2`.
- **Dimensão:** 384.
- **Normalização:** L2 (`normalize_embeddings=True`).
- **Parâmetros HNSW (M, efConstruction, efSearch):** N/A neste experimento (não houve inserção em SGBD nem busca ANN).
- **Cenário:** N/A (validação de pipeline, não Cenário A/B/C).
- **Concorrência:** 1 thread (chamada síncrona em CPU).

## Comando executado

Pipeline disparado via Python embutido (não há script `scripts/embed_subset.py` ainda; este experimento foi o smoke). O comando reproduz a chamada:

```bash
cd code && .venv/bin/python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, ".")
from pipeline.ms_marco_loader import sample_passages
from pipeline.embeddings import gerar_embeddings

passages = sample_passages(Path("../data/ms_marco/collection.tsv"), n=100)
embs = gerar_embeddings(
    [p.text for p in passages],
    cache_dir=Path("../data/embeddings/pre_dia_3"),
)
print(embs.shape, embs.dtype)
PY
```

Suíte de testes equivalente:

```bash
cd code && .venv/bin/python -m pytest tests/integration/test_embeddings_real.py -v
```

## Resultados

### Verificação técnica
| Verificação                                       | Esperado                          | Observado                              |
|---------------------------------------------------|-----------------------------------|----------------------------------------|
| `shape`                                           | `(100, 384)`                      | `(100, 384)` ✓                         |
| `dtype`                                           | `float32`                         | `float32` ✓                            |
| `norma L2 mínima`                                 | ≈ 1.0                             | `0.9999999403953552` ✓                 |
| `norma L2 máxima`                                 | ≈ 1.0                             | `1.0000001192092896` ✓                 |
| `norma L2 média`                                  | 1.0                               | `1.0000000` ✓                          |
| IDs amostra (primeiros/últimos)                   | `[0,1,2, 97,98,99]`               | `[0,1,2, 97,98,99]` ✓                  |
| Cache hit produz array idêntico                   | `array_equal == True`             | `True` ✓                               |

### Características do subset
| Métrica                          | Valor      |
|----------------------------------|------------|
| `passage_min_len` (chars)        | 113        |
| `passage_max_len` (chars)        | 925        |
| `passage_avg_len` (chars)        | 313.46     |
| Chave de cache (SHA-256)         | `21d374662cf392279d83317f2e2623e2af19a4e2f87308740e18ae2b5ccbddef` |
| Arquivo `.npy` resultante        | `data/embeddings/pre_dia_3/21d374...ddef.npy` |
| Tamanho `.npy` em disco          | 153.728 bytes (= 100 × 384 × 4 + cabeçalho NumPy) |

### Timings (execução isolada, modelo já em `~/.cache/huggingface/`)
| Etapa                                             | Tempo (s)  |
|---------------------------------------------------|------------|
| `sample_passages(tsv, n=100)`                     | ~0.000     |
| 1ª chamada `gerar_embeddings` (load + encode 100) | **10.333** |
| 2ª chamada `gerar_embeddings` (cache hit)         | 0.0004     |

### Extrapolação grosseira (não é compromisso de SLO)
A 1ª chamada inclui carga do modelo. Considerando ~9,7 passages/s sustentado em CPU para tamanhos moderados:
- 100k → ~3 h
- 500k → ~14 h
- 1M  → ~28 h (ficará para Etapa 4)

Pré-cálculo offline com cache em disco torna isso aceitável: pago 1× e os SGBDs leem do `.npy`.

### Suíte completa após adição do teste real
- **50 passed in 26.33s** (era 46/46 ao fim do Dia 2; +4 testes em `tests/integration/test_embeddings_real.py`).

## Observações

1. **Determinismo confirmado.** Mesmas 100 strings → mesmo array bit-a-bit (`array_equal`). O cache local pula 100% da inferência: 0.4 ms vs 10.3 s. Isto é decisivo para reprodutibilidade: o lote de embeddings da Etapa 3 será congelado em `data/embeddings/` e revivido por hash.

2. **Top-N por `passage_id` ascendente está correto.** Primeiros IDs 0-2, últimos 97-99 — descarta qualquer ordem por hash, hora-de-leitura, ou ordem do arquivo TSV (que pode não estar ordenado).

3. **Normas L2 com flutuação ≤ 1.2e-7** (`0.9999999` a `1.0000001`). Compatível com aritmética `float32`. Não é um defeito: é o ruído de representação do produto interno após divisão pela norma. As buscas por similaridade nos SGBDs ainda usam cosseno/dot-product nativo — não dependem dessa precisão final.

4. **Warning do `huggingface_hub`** sobre `hf_xet.download_files()` deprecated. Não é nosso uso direto; vem do `hf-xet 1.5.0` chamado pelo `huggingface-hub 1.14.0`. Reportável para a HF; aqui só observado. Não impacta resultados.

5. **Sem `HF_TOKEN`** — usando rate limit anônimo. Para o porte do projeto (1 modelo de 80 MB baixado 1×, ~poucos refetchs ao longo do ano) é suficiente. Se virmos rate-limit no futuro (HPC, builds em CI), abrir token gratuito e setar via `.env`.

6. **Pitfall do `pip install` registrado** em [[../lições/2026-05-10-torch-cpu-only-vs-cuda]]: sem `--extra-index-url https://download.pytorch.org/whl/cpu`, o pip puxa ~3 GB de wheels CUDA. Fix aplicado em `code/requirements.txt`. Disco do notebook chegou a 100% durante a sessão; foi necessário `pip cache purge` + `rm -rf .venv` + reinstalação CPU-only (venv final: 1,4 GB vs 4,0 GB com lixo CUDA).

## Próximos passos

- [ ] **Dia 3 / passo 1:** `ground_truth/exact_search.py` em TDD — FAISS `IndexFlatIP` para top-K exato sobre o mesmo lote de embeddings (base do recall@K). Vai precisar de `faiss-cpu==1.13.2` em `requirements.txt`.
- [ ] **Dia 3 / passo 2:** `lib/metrics.py` em TDD — p50/p95/p99 (via `numpy.percentile`), QPS, recall@K.
- [ ] **Dia 3 / passo 3:** `benchmarks/cenario_a.py` (busca pura) varrendo `efSearch ∈ {16, 32, 64, 128, 256}` nos 3 SGBDs.
- [ ] **Etapa 3 / pré-execução:** rodar `gerar_embeddings` para 100k passages e medir tempo real wall-clock (a estimativa de 3 h é grosseira). Cachear `.npy` correspondente.
- [ ] **HF rate-limit defensivo:** abrir `HF_TOKEN` em `.env.example` e documentar uso opcional no `code/README.md` antes da Etapa 4 (HPC pode fazer múltiplos refetchs em paralelo).

## Backlinks
- [[../decisões/2026-04-28-modelo-embedding-minilm]]
- [[../decisões/2026-04-28-dataset-ms-marco]]
- [[../lições/2026-05-10-torch-cpu-only-vs-cuda]]
- [[../sessões/2026-05-10]]
- [[../../docs/tasks/etapa-2-preparacao-ambiente]]
