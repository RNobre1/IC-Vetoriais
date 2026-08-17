---
tipo: log-de-sessão
data: 2026-08-16
foco: Handoff — estado ao pausar para migração de notebook
tags: [sessão, handoff, migração, etapa-3, etapa-4]
---

# Handoff 2026-08-16 — pausa para migração de notebook

Nota de retomada escrita ao pausar a sessão. O log completo do que foi feito está em [[2026-08-16]]; aqui fica **onde paramos, o que fazer em seguida e o que precisa sobreviver à troca de máquina**.

## Estado do repositório

Tudo commitado e sincronizado: `main` em `68af707`, local e remoto idênticos, **CI verde**. Nada pendente na árvore de trabalho.

A sessão fechou 10 commits, do `ba3d08a` ao `68af707`.

## Onde paramos exatamente

O relatório parcial está **pronto para envio**, com PDF gerado em `docx/relatorio_parcial/Relatorio_Parcial_IC_RafaelNobre.pdf` (23 páginas, A4, sem citação indefinida, sem `\todo`, 14 referências todas citadas). O PDF não é versionado por decisão de convenção — sai de `make pdf` e é renomeado.

A tarefa interrompida era secundária e não afeta o relatório: montar uma coleção Postman com as requisições REST do Qdrant e do Weaviate, para inspecionar manualmente as coleções seedadas. Ficou pela metade — os dados já levantados estão na seção "Requisições REST" abaixo, o que resta é empacotar no formato de coleção do Postman.

Antes de retomar isso, vale registrar que houve um mal-entendido a desfazer: o pedido falava de "endpoints que achou", mas **nenhum levantamento de endpoints foi feito nesta sessão**. O que existia eram as portas citadas na configuração do ambiente. A coleção Postman, se ainda fizer sentido, é trabalho novo — não a formalização de algo já mapeado.

## O que fazer em seguida

Em ordem de prioridade:

1. **Entregar o relatório parcial.** Está pronto. Antes, abrir o PDF e conferir visualmente as quatro tabelas novas (Cenário A em 500k, Cenário B nas duas condições) — posicionamento de tabela com `[H]`/`multirow` é a única coisa que as checagens automáticas não pegam.
2. **Criar tag de release** marcando a versão entregue, já que o PDF não é versionado e a convenção do projeto prevê tag no release.
3. **Re-medir tempos de indexação e footprint com persistência em JSON.** Saíram do relatório por não terem fonte rastreável (foram só para console em julho). A instrumentação precisa gravar junto às curvas.
4. **Etapa 4 (Jul–Set no cronograma canônico):** escala de 1M e Cenário C de carga mista. O `benchmarks/cenario_c.py` é esqueleto — `executar` levanta `NotImplementedError("Etapa 4")`. Nasce já equalizado, por decisão de [[../decisões/2026-08-16-equalizacao-cenario-b]].
5. **Atualizar as actions do CI:** `actions/checkout@v4` e `actions/setup-python@v5` ainda declaram Node 20, depreciado nos runners. Warning, não falha.
6. Opcional: investigar a hipótese de decisão por segmento no Qdrant (por que o equalizado dá recall levemente menor onde o padrão já usava HNSW). Exigiria instrumentar o plano de execução.

## Checklist de migração de notebook

O repositório cobre código, relatório e vault. **Quatro coisas não estão no git** e precisam de ação manual.

### 1. Ferramental de desenvolvimento (obrigatório copiar)

Não é versionado por decisão — o repositório é público. Empacotado em:

```
/home/rnobre/ic-vetoriais-ferramental-local.tar.gz    (96 KB, 66 arquivos)
/home/rnobre/ic-vetoriais-git-exclude.txt             (683 B)
```

No notebook novo, após clonar o repositório:

```bash
cd ~/caminho/para/IC-Vetoriais
tar xzf ~/ic-vetoriais-ferramental-local.tar.gz          # restaura CLAUDE.md, AGENTS.md, .claude/, .agents/, .xp-stack/
cp ~/ic-vetoriais-git-exclude.txt .git/info/exclude      # restaura a exclusão local
git status                                                # deve sair limpo; se listar CLAUDE.md, o exclude não foi aplicado
```

O `.git/info/exclude` é **local ao clone** e não vem com o `git clone`. Sem ele, o ferramental aparece como untracked e corre risco de ir para o repositório público.

### 2. Datasets — 4,9 GB (decidir: copiar ou regerar)

| Diretório | Tamanho | Regenerável? |
|---|---|---|
| `data/ms_marco/` | 3,9 GB | sim — download da fonte oficial |
| `data/embeddings/` | 1,1 GB | sim — mas custa ~14 min de CPU para 100k e ~68 min para 500k |
| `data/ground_truth/` | 1,2 MB | sim — recalculado rapidamente via FAISS |

Copiar por rede ou disco externo é mais rápido que regerar, principalmente pelos embeddings. Se optar por regerar, o `collection.tsv` precisa ter exatamente **8.841.823 linhas** e 3.061.567.852 bytes — conferir antes de rodar qualquer benchmark, porque a amostragem é por ordem de `passage_id` e um arquivo diferente muda toda a base.

Atenção ao cache de embeddings: a chave é o hash dos textos, então `N_QUERIES` diferente gera cache novo. Foi o que aconteceu na primeira contraprova desta sessão — 14 minutos de CPU gastos por usar 200 queries em vez de 1.000.

### 3. Volumes Docker (não copiar — re-seedar)

As coleções seedadas vivem em volumes nomeados do Docker e não acompanham o repositório. No notebook novo:

```bash
cd code && make deps && make up      # sobe os 3 SGBDs
make seed N=100000                   # re-seeda quando precisar
```

Coleções que existiam nesta máquina, para referência: no Qdrant `bench_a_100000`, `bench_a_500000`, `bench_b_100000`, `bench_b_500000`, `bench_b_eq_100000`, `bench_b_eq_500000`; no Weaviate as equivalentes em CamelCase (`BenchA100000`, `BenchBEq500000` etc.).

### 4. Backup pré-rewrite (perdido, sem consequência)

O tarball de segurança criado antes da reescrita do histórico estava em `/tmp` e foi limpo no reboot. Não é problema: o histórico reescrito está no GitHub, com CI verde e validado por clone limpo. Registrado apenas para não se procurar por ele.

## Requisições REST levantadas (para retomar a coleção Postman)

Serviços sem autenticação: Qdrant com `QDRANT_API_KEY` vazio, Weaviate com `AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"`.

| O que | Método e caminho |
|---|---|
| Saúde do Qdrant | `GET http://localhost:6333/healthz` |
| Coleções do Qdrant | `GET http://localhost:6333/collections` |
| Config de uma coleção (mostra `full_scan_threshold`) | `GET http://localhost:6333/collections/{nome}` |
| Busca no Qdrant | `POST http://localhost:6333/collections/{nome}/points/query` |
| Saúde do Weaviate | `GET http://localhost:8080/v1/.well-known/ready` |
| Schema do Weaviate (mostra `flatSearchCutoff`) | `GET http://localhost:8080/v1/schema` |
| Busca no Weaviate | `POST http://localhost:8080/v1/graphql` |

O `pgvector` **não tem API REST** — fala o protocolo wire do PostgreSQL, que o Postman não suporta. O equivalente é SQL direto, e é o que o adaptador executa:

```sql
-- Cenário A
SELECT id FROM bench_a_100000 ORDER BY embedding <=> $1 LIMIT 10;
-- Cenário B (filtro por seletividade)
SELECT id FROM bench_b_100000 WHERE seletor < 0.01 ORDER BY embedding <=> $1 LIMIT 10;
-- ef_search é por sessão:
SET hnsw.ef_search = 64;
```

Uma comparação que vale a pena montar, porque exibe o achado central da sessão de forma direta: consultar `GET /collections/bench_b_100000` e `GET /collections/bench_b_eq_100000` e olhar o `full_scan_threshold` de cada uma — 10000 na primeira, 10 na segunda. O mesmo para o `flatSearchCutoff` de `BenchB100000` contra `BenchBEq100000` no schema do Weaviate.

## Backlinks

- [[2026-08-16]]
- [[../decisões/2026-08-16-equalizacao-cenario-b]]
- [[../experimentos/2026-08-16-cenario-b-equalizado]]
- [[../experimentos/2026-08-16-contraprova-full-scan]]
