# Relatório Parcial — IC 2026 (LaTeX/Overleaf)

Migração do `relatorio_parcial.docx` para LaTeX, mantendo o visual ABNT e o conteúdo já aprovado (incluindo as edições das seções 4.2 e 5.1).

## Estrutura

```
relatorio_parcial/
├── main.tex              # preâmbulo + capa + \input das seções
├── refs.bib              # 13 referências do parcial em ABNT
└── secoes/
    ├── 01-resumo.tex
    ├── 02-introducao.tex
    ├── 03-objetivos.tex
    ├── 04-fundamentacao.tex
    ├── 05-metodologia.tex
    ├── 06-resultados.tex
    ├── 07-consideracoes.tex
    └── 08-cronograma.tex
```

## Como usar no Overleaf

1. Em https://www.overleaf.com → **New Project** → **Upload Project** → seleciona o `.zip` deste diretório.
2. Abre o projeto. O compilador padrão (pdfLaTeX) já funciona.
3. **Menu → Settings → Compiler:** confirma `pdfLaTeX`.
4. Clica em **Recompile**. Na primeira compilação, o Overleaf roda `pdflatex` → `bibtex` → `pdflatex` → `pdflatex` automaticamente para resolver as citações.

Se aparecer ‘`Citation 'foo' undefined`’ na primeira passada, é normal — recompila uma vez e some.

## Macros do projeto

- `\todo{texto}` — marcador editorial em vermelho/itálico (substitui o estilo `[TODO]` do docx). Removido conforme cada pendência é resolvida.
- `\code{trecho}` — fonte monoespaçada inline (substitui o run em Courier do docx). Usar em nomes de imagens Docker, parâmetros, arquivos de configuração.
- `\citeonline{key}` — citação textual “Sobrenome (ano)”.
- `\cite{key}` — citação parentética “(SOBRENOME, ano)”.

## Decisões de formatação

| Item | docx original | LaTeX equivalente |
|---|---|---|
| Página | A4 | `geometry, a4paper` |
| Margens | 3 / 3 / 2 / 2 cm | `top=3,left=3,bottom=2,right=2` |
| Fonte | Arial 12pt | Helvetica 12pt (`helvet` + `\sfdefault`) — vide nota abaixo |
| Espaçamento | 1.5 linhas | `\onehalfspacing` |
| Justificação | sim | default |
| Recuo | 1.25cm | `\setlength{\parindent}{1.25cm}` |
| Citações ABNT | manual | `abntex2cite` (estilo `alf`) |
| Bibliografia | manual | `bibtex` + `refs.bib` |

### Nota sobre Arial vs Helvetica

`pdflatex` não embarca Arial nativamente (fonte proprietária). `helvet` traz Helvetica, que é visualmente quase idêntica e é o padrão de fato em ABNT-LaTeX. Para Arial *exato*, alterar:

- **Compilador:** `XeLaTeX` (Settings → Compiler).
- **Preâmbulo:** trocar `\usepackage{helvet}\renewcommand{\familydefault}{\sfdefault}` por:
  ```latex
  \usepackage{fontspec}
  \setmainfont{Arial}
  ```

Overleaf possui Arial disponível para XeLaTeX. Custo: compilação um pouco mais lenta.

## Workflow daqui pra frente

- Editar via Overleaf web (com share para o orientador) ou local (`git clone` + qualquer editor).
- Cada nova citação: adiciona entrada em `refs.bib` e usa `\citeonline{}` ou `\cite{}` no texto.
- Cada `[TODO]` resolvido: substitui `\todo{...}` pelo conteúdo real.
- Versionar em git. PDF é artefato de saída — `.gitignore` recomendado:
  ```
  *.aux *.bbl *.blg *.log *.out *.toc *.fdb_latexmk *.fls *.synctex.gz
  main.pdf
  ```
