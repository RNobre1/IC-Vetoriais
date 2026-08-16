---
tipo: lição-aprendida
data: 2026-08-16
contexto: Auditoria da Etapa 3. O fix aplicado em julho para destravar a carga de 500k no Qdrant removeu, sem que se percebesse, a garantia de que o índice estava pronto na hora de medir. Vide [[../experimentos/2026-07-09-etapa3-cenarios-a-b]].
tags: [qdrant, indexação, benchmarking, bug-silencioso, tdd, regra-2a]
---

# `wait=False` no upsert do Qdrant deixou o CLI canônico medindo índice pela metade

## Situação

A carga de 500k no Qdrant estourava o timeout com `upsert(..., wait=True)`. O fix de julho trocou por `wait=False` nos dois pontos de upsert do `qdrant_seeder`, e a carga passou a rodar.

O problema é o que veio junto. Com `wait=False`, o `seed_qdrant` retorna antes de o Qdrant terminar de construir o grafo HNSW — a indexação segue em background. Quem chamar o seeder e começar a medir imediatamente mede um índice incompleto.

Os scripts avulsos da Etapa 3 compensaram isso com um laço de espera pelo status `green`:

```python
if sistema == "qdrant":
    for _ in range(120):
        info = recurso.get_collection(nome_recurso)
        if str(info.status) == "green":
            break
        time.sleep(2)
```

Só que essa espera ficou **apenas nos scripts avulsos**. O caminho canônico — `benchmarks/run_cenario_a.py` e `run_cenario_b.py`, que é o que `make bench-A` e `make bench-B` executam — nunca recebeu a espera. Uma busca por `green|wait|sleep` nesses arquivos não retornava nada.

## Causa

A correção foi aplicada no lugar errado da pilha. O seeder é quem sabe que o upsert virou assíncrono; os chamadores não têm como saber. Ao consertar no chamador, o conserto cobriu o único chamador que existia naquele dia e deixou descoberto todo o resto — presente e futuro.

É a Regra 2-A vista de outro ângulo: a garantia "a coleção está pronta ao retornar" precisa morar **uma vez**, no ponto que a quebrou.

## Por que é grave

Falha em silêncio. Um índice HNSW parcial responde consultas normalmente — devolve os K vizinhos do que já foi indexado, com latência plausível e recall degradado. Nada estoura, nada avisa. O resultado é um JSON com números críveis e errados, que entra no relatório sem levantar suspeita.

Nenhum dado da Etapa 3 foi comprometido por isso: os scripts que rodaram em julho *tinham* a espera. O risco era inteiramente futuro — a próxima pessoa (ou a próxima sessão) que rodasse `make bench-B` teria medido índice pela metade.

## Correção

`seed_qdrant` passa a aguardar o status `green` antes de retornar, com `aguardar_indexacao=True` por default:

- mantém `wait=False` nos upserts, preservando o ganho de velocidade que motivou o fix;
- a espera acontece **uma vez**, ao final, em vez de por lote;
- levanta `TimeoutError` explícito se o índice não ficar pronto, em vez de seguir silenciosamente;
- `aguardar_indexacao=False` continua disponível para quem quiser o comportamento assíncrono puro.

Coberto por `tests/unit/test_qdrant_indexacao.py` (4 testes: espera até green, desligamento explícito, timeout com limite, contrato de retorno preservado).

## Regra para o futuro

1. **Ao trocar uma chamada síncrona por assíncrona, perguntar que garantia foi removida junto** — e restaurá-la no mesmo módulo, não no chamador.
2. **Conserto aplicado em script avulso é conserto provisório.** Se a lógica é necessária para a medição estar correta, ela pertence ao caminho canônico; caso contrário existem dois comportamentos e ninguém sabe qual rodou.
3. **Bug que não falha, só mente, é o mais caro.** Vale um teste explícito mesmo quando "obviamente funciona" — foi o que este caso pedia e não tinha.

## Backlinks

- [[../experimentos/2026-07-09-etapa3-cenarios-a-b]]
- [[../decisões/2026-08-16-equalizacao-cenario-b]]
- [[2026-05-10-smoke-cli-cenario-a-make-or-e-colisao-nome]]
