---
tipo: decisão
data: 2026-05-05
status: aceita
tags: [metodologia, redação, latex, abntex2, relatório, ferramentas]
relacionadas: []
---

# ADR — Migração do relatório parcial: Word/.docx → LaTeX/abntex2

## Contexto

O relatório parcial inicialmente era um `relatorio_parcial.docx` editado manualmente pelo bolsista, fora do controle do agente IA. Em 2026-05-05 houve uma sessão em que o agente editou o `.docx` programaticamente via `python-docx` para atualizar a tabela de cronograma; o bolsista cancelou a edição e estabeleceu a regra dura de "não editar `.docx` diretamente" (vide `feedback_no_docx_edits.md` na memória global).

Essa regra cria fricção: toda alteração no relatório requer gerar um prompt para o Claude da nuvem (que tem o `.docx` anexado) executar a edição lá. Para um IC de 8 meses com revisões frequentes, o overhead é alto.

Em paralelo, o bolsista instalou TeX Live no Fedora (texlive-scheme-medium + abntex2 + collection-langportuguese + collection-fontsrecommended + biber) e a extensão LaTeX Workshop no VS Code. Migrou manualmente o conteúdo do `.docx` para um projeto LaTeX modular em `docx/relatorio_parcial/` (template baseado em `article` + `helvet` + `abntex2cite[alf]`, com 8 seções modulares e 13 referências em `refs.bib`).

## Decisão

**O relatório parcial passa a ter como fonte canônica o projeto LaTeX em `docx/relatorio_parcial/`.** O PDF gerado (`main.pdf`) é o entregável; o `.tex` é versionado em git e editado normalmente pelo agente IA (sem restrição). O `.docx` legado foi removido pelo bolsista.

A regra de "não editar `.docx`" continua válida para arquivos `.docx` legados (e.g. `docx/OFC- Planejamento Rafael Nobre - 2026.docx`), mas **não se aplica ao novo fluxo LaTeX**.

## Opções consideradas

| Opção | Editabilidade pelo agente | Versionamento git | Padrão científico ABNT | Custo de setup |
|-------|--------------------------|-------------------|------------------------|----------------|
| Manter `.docx` + prompts pra cloud | Indireta (via prompt) | Pobre (binário) | Suportado | Zero |
| Migrar pra Markdown + Pandoc → docx | Direta | Excelente | Frágil (pandoc-ABNT é problemático) | Médio |
| **Migrar pra LaTeX + abntex2** ✅ | Direta | Excelente | Padrão de facto em CS/Engenharia BR | Médio (TeX Live + abntex2) |
| Migrar pra Overleaf cloud | Indireta (sem CLI access) | OK (sync git) | Suportado | Zero local; depende de internet |

## Consequências

- **Positivas:**
  - Editabilidade direta pelo agente (Edit/Write em `.tex` como qualquer arquivo).
  - `git diff` mostra mudanças linha-a-linha em texto — impossível em `.docx`.
  - `abntex2cite[alf]` resolve citações ABNT autor-ano automaticamente; antes era manual.
  - Bibliografia em `.bib` é estruturada e reusável entre relatórios parcial e final.
  - Compilação local 30s; preview no VS Code via LaTeX Workshop com SyncTeX.
- **Negativas / custo:**
  - Curva de aprendizado de LaTeX para o bolsista (mitigação: VS Code + LaTeX Workshop reduz overhead).
  - Orientador pode preferir receber `.docx` no envio final (mitigação: `latexmk -pdf` gera PDF; PDF é o que o edital exige; `.docx` só se ele explicitar).
  - Diagramas/figuras precisam ser PDFs ou inseridos via `\includegraphics`. Plot do matplotlib em PDF resolve.

## Aplicação imediata

- `docx/relatorio_parcial/` — projeto LaTeX (template feito pelo bolsista).
- `docx/relatorio_parcial/.gitignore` — ignora artefatos de build (`.aux`, `.bbl`, `main.pdf`, etc.).
- `docx/relatorio_parcial/Makefile` — targets `pdf`, `watch`, `clean`, `distclean`.
- `CLAUDE.md` raiz — atualizado para refletir que `.tex` é fonte canônica.
- `feedback_no_docx_edits.md` (memória global) — atualizado para esclarecer que regra aplica a binários legados, não ao fluxo LaTeX.

## Validação inicial

Compilação local em 2026-05-05 (após instalação de `texlive-abntex2`):

```
$ cd docx/relatorio_parcial && latexmk -pdf main.tex
Output written on main.pdf (16 pages, 137157 bytes).
Latexmk: All targets (main.pdf) are up-to-date
```

Bibliografia resolveu via `abntex2-alf` style. 1 warning de overfull hbox em `08-cronograma.tex` (linha 13-14, "Etapa 2 — Preparação..." 28pt overfull) — apenas visual, não impede compilação. Será endereçado em revisão de microtipografia.

## Backlinks

- [[../lições/2026-05-05-erro-recomendacao-weaviate-cloud-console]] — sessão em que decisão foi tomada.
- [[2026-05-05-isolamento-ui-vs-benchmark]] — outra decisão da mesma sessão.
- `docx/relatorio_parcial/README.md` — instruções operacionais do projeto LaTeX.
