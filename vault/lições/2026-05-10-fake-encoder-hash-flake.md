---
tipo: lição-aprendida
data: 2026-05-10
contexto: Dia 3 da Etapa 2 — durante a adição de `lib/metrics.py` (vide [[../sessões/2026-05-10]]), `test_gerar_embeddings_input_diferente_recalcula` falhou na suíte completa mas passou isolado. Investigação revelou flakiness preexistente no Dia 2.
tags: [testes, flakiness, python, hash, determinismo, reprodutibilidade]
---

# `hash()` do Python no `FakeEncoder` é flaky cross-process (PYTHONHASHSEED)

## Situação
`tests/unit/test_embeddings.py::test_gerar_embeddings_input_diferente_recalcula` falhou de forma intermitente após uma sessão limpa de testes — passou em 4 de 5 execuções consecutivas, falhou em 1. Quando executado isolado, sempre passa.

```text
arr1 = gerar_embeddings(["a", "b"], cache_dir=tmp_path, encoder_factory=factory)
arr2 = gerar_embeddings(["a", "c"], cache_dir=tmp_path, encoder_factory=factory)
assert not np.array_equal(arr1, arr2)   # ← falhou às vezes
```

## Causa
O `FakeEncoder` deriva o vetor de cada texto T como:

```python
valor = (hash(t) % 7919) / 7919.0 + 0.001
```

`hash()` em Python tem **salt aleatório por processo** quando aplicado a strings (`PYTHONHASHSEED` é gerado a cada start do interpretador, salvo se fixado por env var). Resultado:
- Dentro do mesmo processo: `hash("b")` e `hash("c")` são estáveis → arrays diferentes → teste passa.
- Em processos diferentes (ou seja, runs separados de pytest): valores mudam, e em ~1/7919 ≈ 0,013% dos processos, `hash("b") % 7919 == hash("c") % 7919`. Quando isso acontece, `arr1 == arr2` e o teste falha.

O salt randomizado é defesa contra DoS por hash collision em dicts (PEP 456). Não tem desligamento robusto em testes — `PYTHONHASHSEED=0` resolve mas é workaround.

## Correção aplicada
Substituído `hash()` por SHA-256 truncado em `FakeEncoder.encode`:

```python
import hashlib
...
digest = hashlib.sha256(t.encode("utf-8")).digest()
valor = int.from_bytes(digest[:4], "big") / 2**32 + 1e-6  # evita vetor zero
```

SHA-256 é determinístico cross-process e cross-run, e o espaço de saída (`2**32` valores) torna colisão praticamente impossível para strings distintas usadas em testes.

Validação: 8 execuções consecutivas de `pytest tests/unit/test_embeddings.py` — 15/15 verde em todas.

## Aplicação a futuro
- **Nunca usar `hash()` Python em testes** quando o teste depende do valor numérico (contagem, comparação, modulo). Aceita-se em sets/dicts onde o uso é interno e estável dentro do processo.
- **Substituto canônico em testes:** `hashlib.sha256(s.encode("utf-8")).digest()` + slice + `int.from_bytes` quando precisar de um número. Cross-process estável.
- **Sintoma típico de flakiness por hash:** teste passa isolado mas falha intermitentemente na suíte; muda o número de processos paralelos (pytest-xdist) e o padrão de falha muda; `PYTHONHASHSEED=0` "conserta" sem outras mudanças.
- **Para reproduzir flakes assim no CI:** rodar `for i in {1..20}; do pytest tests/.../test_foo.py -q || break; done` antes de aceitar como verde. Aplicar a qualquer fake/stub que use `hash()` ou aleatoriedade implícita.

## Backlinks
- [[../sessões/2026-05-10]]
- [[../decisões/2026-04-28-modelo-embedding-minilm]]
