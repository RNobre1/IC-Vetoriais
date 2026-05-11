---
tipo: lição-aprendida
data: 2026-05-10
contexto: Pré-Dia 3 da Etapa 2 — adição de `sentence-transformers` ao `requirements.txt` para habilitar a geração real de embeddings (vide [[../sessões/2026-05-10]] e [[../decisões/2026-04-28-modelo-embedding-minilm]])
tags: [pytorch, sentence-transformers, dependencias, reprodutibilidade, disco]
---

# Pin de `torch` sem `--extra-index-url` puxa build CUDA e estoura disco

## Situação
No Pré-Dia 3, ao adicionar `sentence-transformers==5.4.1` em `code/requirements.txt` e rodar `pip install -r requirements.txt`, o pip resolveu `torch` para a **build CUDA padrão** do PyPI. Isso baixou ~3 GB de wheels NVIDIA (`nvidia-cublas`, `nvidia-cudnn-cu13`, `nvidia-cusparse`, `nvidia-cufft`, `nvidia-cusolver`, `nvidia-nccl`, `triton`, etc.) **antes** de o disco do notebook (96 GB, 93 GB ocupados) acabar. O install falhou no meio (`OSError: [Errno 28] Não há espaço disponível no dispositivo`), deixando o venv num estado inconsistente: componentes CUDA presentes em `site-packages/nvidia/` (2,7 GB) sem o `torch` registrado em `pip list`.

## Causa
1. O ADR [[../decisões/2026-04-28-modelo-embedding-minilm]] decide explicitamente CPU para o `all-MiniLM-L6-v2`. O notebook tem GPU (RTX 3050), mas a metodologia escolheu CPU para nivelar com cargas reais do projeto e simplificar reprodução.
2. A wheel default de `torch` no PyPI **assume CUDA**. Para CPU-only é necessário usar o índice próprio do PyTorch:
   ```
   --extra-index-url https://download.pytorch.org/whl/cpu
   torch==<versão>+cpu
   ```
   O sufixo `+cpu` no pin só existe nesse índice — força a resolução para a build CPU (≈200 MB) em vez da CUDA (≈3 GB).
3. Sem essa instrução explícita, o pip silenciosamente puxa a build maior. Não há aviso. Não há flag. O único sintoma é o disco estourar (ou o usuário notar tráfego inesperado).

## Correção aplicada
1. **Limpeza:** `rm -rf .venv` + `python3.14 -m venv .venv` (o estado parcial era irrecuperável sem dezenas de `pip uninstall`).
2. **`requirements.txt`:**
   ```text
   --extra-index-url https://download.pytorch.org/whl/cpu
   ...
   torch==2.11.0+cpu
   sentence-transformers==5.4.1
   ```
3. **Reinstalação:** `pip install -r requirements.txt`.
4. Footprint final do venv: a documentar na nota [[../experimentos/2026-05-10-validacao-embeddings-100-passages]] após reinstalação concluir.

## Aplicação a futuro
- **Toda nova dependência ML/DL** (torch, jax, tensorflow, onnxruntime, sentence-transformers, transformers diretos) entra com pin **explícito de build CPU/GPU** e `--extra-index-url` do fornecedor quando aplicável.
- **Auditar `requirements.txt` antes de `pip install`** quando aparecer um pacote ML novo: rodar `pip install --dry-run -r requirements.txt | head` resolve sem baixar e revela se o pip puxaria wheels CUDA inesperadas.
- **Se faz sentido subir para GPU no futuro** (Etapa 4, possível execução no Cluster HPC do IEG), abrir ADR separada bumpando para `torch==<v>+cu<NN>` com `--extra-index-url https://download.pytorch.org/whl/cu<NN>` — não misturar CPU e CUDA no mesmo lock.
- **Monitorar disco em sessões com bumps de deps ML.** Um `df -h /` antes e depois é cheap e evita surpresa.

## Backlinks
- [[../decisões/2026-04-28-modelo-embedding-minilm]]
- [[../sessões/2026-05-10]]
- [[../experimentos/2026-05-10-validacao-embeddings-100-passages]]
