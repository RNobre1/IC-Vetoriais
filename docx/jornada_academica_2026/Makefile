MODELO := modelo/Modelo_de_submissao_de_trabalhos_Jornada_Academica_2026.docx

.PHONY: tudo pdf docx verificar clean

# O .tex é a fonte única do texto. O .docx entregue e o PDF de conferência são
# ambos derivados dele, e nenhum dos dois é versionado.
tudo: verificar pdf docx

pdf: banner-jornada.png
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
	@echo "--- páginas (limite do modelo: 3) ---"
	@pdfinfo main.pdf | grep '^Pages'

docx:
	python3 gerar_docx.py

# Confere os limites de caracteres e palavras do modelo sem gerar arquivo.
# O gerar_docx.py aplica os mesmos limites e falha se algum estourar.
verificar:
	python3 gerar_docx.py --verificar

# A logo do evento é extraída do próprio modelo, para não existir uma segunda
# cópia dela no repositório.
banner-jornada.png: $(MODELO)
	unzip -p $(MODELO) word/media/image1.png > $@

clean:
	latexmk -C main.tex
	rm -f banner-jornada.png
