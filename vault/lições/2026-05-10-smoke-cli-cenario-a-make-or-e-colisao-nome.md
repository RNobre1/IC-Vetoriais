---
tipo: lição-aprendida
data: 2026-05-10
contexto: Dia 3 da Etapa 2 — primeiro `make bench-A` (smoke real do CLI do Cenário A) revelou dois bugs que os testes unitários não pegariam. Vide [[../sessões/2026-05-10]] e [[../decisões/2026-05-10-cenario-a-queries-warmup]].
tags: [make, makefile, reprodutibilidade, perda-de-dados, cli, benchmark, idempotencia]
---

# Smoke do CLI do Cenário A: `$(or)` com vírgulas, colisão de nome em sweep, e CLI não-idempotente

O primeiro `make bench-A N=200 Q=20 EF=16,64 WARMUP=2` expôs **três** defeitos. Nenhum apareceria sem rodar o pipeline real ponta-a-ponta — reforço de que smoke de integração é obrigatório, testes unitários verdes não bastam.

## Bug 1 — `$(or $(VAR),lista,com,virgula)` no Makefile

**Sintoma:** `make bench-A` rodou só `--sistemas pgvector` (não os 3) e teria usado só `--ef-search 16`.

**Causa:** `$(or a,b,c)` do GNU Make retorna o **primeiro argumento não-vazio**. Em `$(or $(SYS),pgvector,qdrant,weaviate)`, com `SYS` vazio, os itens `qdrant` e `weaviate` são *argumentos seguintes do `$(or)`*, não parte de um default — então o resultado é só `pgvector`. Idem `$(or $(EF),16,32,64,128,256)` → `16`. Defaults com vírgula **não** podem ir dentro de `$(or)`.

**Correção:** usar atribuição condicional idiomática, que não interpreta vírgulas:
```makefile
EF  ?= 16,32,64,128,256
SYS ?= pgvector,qdrant,weaviate
bench-A:
	$(PYTHON) -m benchmarks.run_cenario_a --ef-search $(EF) --sistemas $(SYS) ...
```
`?=` define o default só se a variável não veio do ambiente/linha de comando (`make bench-A SYS=pgvector` continua sobrescrevendo).

**Regra futura:** nunca colocar lista separada por vírgula como default dentro de `$(or ...)`/`$(if ...)`. Defaults de Make → sempre `VAR ?= valor`.

## Bug 2 — colisão de nome de arquivo perde pontos do sweep

**Sintoma:** rodar o sweep `ef ∈ {16,64}` gravava `cenario_A_pgvector_200_<ts>.json` **duas vezes** com o mesmo nome — o segundo ponto sobrescrevia o primeiro. Perda de dado **silenciosa**.

**Causa:** `salvar_resultado` nomeia por `(cenario, sistema, n, timestamp)`. Num sweep, todos os pontos compartilham esses 4 campos (timestamp é gerado uma vez por execução) → mesmo nome. O loop `for r in resultados: salvar_resultado(r)` só preservava o último `efSearch`.

**Correção:** novo `salvar_curva(resultados, ...)` grava a curva inteira (lista `pontos`) num único JSON. Alinhado à decisão metodológica firme do docs/metodologia.md: *"reportar curvas recall × QPS, não números pontuais"*. `salvar_resultado` (ponto isolado) permanece para outros usos. Teste de regressão: `test_salvar_curva_preserva_todos_os_pontos`.

**Regra futura:** ao persistir resultado de **sweep/varredura**, o identificador de arquivo precisa ou (a) conter o eixo varrido, ou (b) agrupar a curva inteira. Default do projeto: agrupar (curva por arquivo). Desconfiar de qualquer escrita em loop cujo nome de arquivo não dependa da variável do loop.

## Bug 3 — CLI não-idempotente (`relation already exists`)

**Sintoma:** segundo `make bench-A` abortou com `psycopg.errors.DuplicateTable: relation "bench_a_200" already exists`.

**Causa:** os seeders fazem `CREATE` sem `IF NOT EXISTS` (correto para os testes de integração, que usam nomes únicos via `uuid`). O CLI reusa um nome estável por `N` e não limpava antes — diferente do teste de integração, que tem `try/finally` com drop. Um benchmark será re-rodado muitas vezes na Etapa 3; abortar no 2º run é inaceitável.

**Correção:** `_limpar_recurso` no CLI, chamado antes do seed: `DROP TABLE IF EXISTS` (pgvector), `delete_collection` se `collection_exists` (Qdrant), `collections.delete` se `collections.exists` (Weaviate). Não toca nos seeders. É scratch de benchmark, não dado real — descartar e re-seedar é o comportamento desejado.

**Regra futura:** todo script de benchmark reexecutável precisa ser idempotente no setup (limpar o recurso antes de criar). Validar com **dois** runs consecutivos no smoke, não um.

## Backlinks
- [[../sessões/2026-05-10]]
- [[../decisões/2026-05-10-cenario-a-queries-warmup]]
- [[2026-05-10-fake-encoder-hash-flake]]
