.PHONY: tudo corpo slides roteiro pptx clean

# conteudo.py é a fonte única: o corpo do .tex, o .pptx e o roteiro saem dele.

tudo: slides roteiro pptx

corpo:
	python3 gerar_tex.py

slides: corpo
	latexmk -pdf -interaction=nonstopmode -halt-on-error slides.tex
	@echo "--- conferência ---"
	@pdfinfo slides.pdf | grep '^Pages'
	@printf 'avisos de caixa (esperado 0): %s\n' "$$(grep -cE 'Overfull|Underfull' slides.log)"

# O script falha se a soma dos tempos sair da janela de 10 a 15 minutos.
roteiro:
	python3 gerar_roteiro.py

# Depende do PDF: a guarda compara os números dos dois lados e falha se um
# deles tiver sido editado sem o outro. Também falha se algum slide estourar
# a área útil, que é o que não dá para conferir a olho sem PowerPoint aqui.
pptx: slides
	python3 gerar_pptx.py
	python3 gerar_pptx.py --verificar

clean:
	latexmk -C slides.tex
	rm -f corpo-gerado.tex
	rm -rf __pycache__
