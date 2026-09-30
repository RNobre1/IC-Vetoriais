"""Testes dos limites do modelo aplicados por `gerar_docx.verificar`.

O modelo oficial distingue dois tipos de limite de caracteres. Introdução e
metodologia têm limite seco ("Limite 1.000 caracteres com espaços"). Resultados
e conclusões podem passar do limite "desde que o tamanho total do documento não
ultrapasse três páginas" -- condição que só se confere no PDF. Por isso os dois
primeiros bloqueiam a geração e os dois últimos só avisam.

Rodar com `make testar`.
"""

import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "gerar_docx", Path(__file__).parent / "gerar_docx.py"
)
gerar_docx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gerar_docx)


def secoes(**tamanhos: int) -> dict[str, str]:
    """Seções válidas, com o tamanho de algumas sobrescrito por `tamanhos`."""
    sec = {
        "SUBEVENTO": "XII Seminário de Graduação",
        "RESUMO": " ".join(["palavra"] * 200),
        "PALAVRAS": "um; dois; três.",
        "INTRODUCAO": "x" * 900,
        "METODOLOGIA": "x" * 900,
        "RESULTADOS": "x" * 900,
        "RESULTADOS2": "x" * 900,
        "CONCLUSOES": "x" * 900,
    }
    for nome, n in tamanhos.items():
        sec[nome] = "x" * n
    return sec


class LimitesRigidos(unittest.TestCase):
    def test_introducao_acima_de_1000_bloqueia(self):
        problemas = gerar_docx.verificar(secoes(INTRODUCAO=1001))
        self.assertTrue(any("INTRODUCAO" in p for p in problemas))

    def test_metodologia_acima_de_1000_bloqueia(self):
        problemas = gerar_docx.verificar(secoes(METODOLOGIA=1001))
        self.assertTrue(any("METODOLOGIA" in p for p in problemas))

    def test_subevento_com_texto_do_modelo_bloqueia(self):
        sec = secoes()
        sec["SUBEVENTO"] = "[INSERIR NOME DO SUBEVENTO]"
        self.assertTrue(any("SUBEVENTO" in p for p in gerar_docx.verificar(sec)))


class LimitesFlexiveis(unittest.TestCase):
    def test_conclusoes_acima_de_1000_nao_bloqueia(self):
        self.assertEqual(gerar_docx.verificar(secoes(CONCLUSOES=1500)), [])

    def test_conclusoes_acima_de_1000_avisa(self):
        avisos = gerar_docx.avisos(secoes(CONCLUSOES=1500))
        self.assertTrue(any("CONCLUSOES" in a for a in avisos))

    def test_resultados_acima_de_2000_nao_bloqueia(self):
        self.assertEqual(gerar_docx.verificar(secoes(RESULTADOS=1500, RESULTADOS2=1000)), [])

    def test_resultados_acima_de_2000_avisa(self):
        avisos = gerar_docx.avisos(secoes(RESULTADOS=1500, RESULTADOS2=1000))
        self.assertTrue(any("RESULTADOS" in a for a in avisos))

    def test_dentro_dos_limites_nao_avisa(self):
        self.assertEqual(gerar_docx.avisos(secoes()), [])


if __name__ == "__main__":
    unittest.main()
