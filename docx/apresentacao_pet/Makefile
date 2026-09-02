.PHONY: tudo slides roteiro clean

tudo: slides roteiro

slides:
	latexmk -pdf -interaction=nonstopmode -halt-on-error slides.tex
	@echo "--- conferência ---"
	@pdfinfo slides.pdf | grep '^Pages'
	@printf 'avisos de caixa (esperado 0): %s\n' "$$(grep -cE 'Overfull|Underfull' slides.log)"

# O script falha se a soma dos tempos sair da janela de 10 a 15 minutos.
roteiro:
	python3 gerar_roteiro.py

clean:
	latexmk -C slides.tex
	rm -rf __pycache__
