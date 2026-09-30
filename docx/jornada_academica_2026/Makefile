MODELO := modelo/Modelo_de_submissao_de_trabalhos_Jornada_Academica_2026.docx

.PHONY: tudo pdf docx pdf-entrega verificar testar clean

# O .tex é a fonte única do texto. O .docx entregue e o PDF de conferência são
# ambos derivados dele, e nenhum dos dois é versionado.
tudo: testar verificar pdf docx

# Testes das regras de limite do modelo aplicadas pelo gerador.
testar:
	python3 -m unittest -v test_gerar_docx

pdf: banner-jornada.png
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
	@echo "--- páginas (limite do modelo: 3) ---"
	@pdfinfo main.pdf | grep '^Pages'

docx:
	python3 gerar_docx.py

# PDF de entrega, exportado do próprio .docx pelo Pages -- não há Word nem
# LibreOffice na máquina de trabalho. É nele, e não no main.pdf, que se confere
# o limite de três páginas do modelo.
ENTREGA := Resumo_Jornada_Academica_2026_RafaelNobre
pdf-entrega: docx
	rm -f $(ENTREGA).pdf
	osascript -e 'tell application "Pages"' \
	  -e 'set d to open POSIX file "$(CURDIR)/$(ENTREGA).docx"' \
	  -e 'export d to POSIX file "$(CURDIR)/$(ENTREGA).pdf" as PDF' \
	  -e 'close d saving no' \
	  -e 'end tell'
	@echo "--- páginas (limite do modelo: 3) ---"
	@pdfinfo $(ENTREGA).pdf | grep '^Pages'

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
