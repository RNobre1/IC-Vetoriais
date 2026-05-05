.PHONY: help pdf watch clean distclean

help:  ## Lista os alvos
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

pdf:  ## Compila main.tex em main.pdf (1 passada com latexmk)
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

watch:  ## Recompila ao salvar (preview continuous)
	latexmk -pdf -pvc -interaction=nonstopmode main.tex

clean:  ## Remove artefatos intermediários (preserva PDF)
	latexmk -c
	rm -f *.bbl

distclean:  ## Remove tudo, inclusive PDF
	latexmk -C
	rm -f *.bbl
