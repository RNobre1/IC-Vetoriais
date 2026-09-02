#!/usr/bin/env python3
"""Preenche uma cópia do modelo oficial da Jornada com o texto de `main.tex`.

O `.tex` é a fonte única. Este script extrai os blocos delimitados por
`% >>> SECAO: <nome>` / `% <<< SECAO`, converte a marcação LaTeX de volta para
texto simples e substitui o texto de exemplo do modelo, preservando estilos,
cabeçalho com a logo, rodapé, margens e configuração de página do arquivo
original -- que não é modificado em nenhum momento.

Só mexe no que precisa: cada parágrafo do modelo é localizado pelo texto que
ele contém hoje, e apenas os `<w:t>` daquele parágrafo são reescritos. Nenhum
estilo é redefinido, porque o objetivo é aderir ao modelo, não reproduzi-lo.
"""

from __future__ import annotations

import re
import shutil
import sys
import zipfile
from pathlib import Path

AQUI = Path(__file__).parent
MODELO = AQUI / "modelo" / "Modelo_de_submissao_de_trabalhos_Jornada_Academica_2026.docx"
SAIDA = AQUI / "Resumo_Jornada_Academica_2026_RafaelNobre.docx"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Limites de caracteres com espaços declarados pelo modelo. Resumo é em palavras.
LIMITES_CHARS = {
    "INTRODUCAO": 1000,
    "METODOLOGIA": 1000,
    "CONCLUSOES": 1000,
}
LIMITE_RESULTADOS = 2000  # soma de RESULTADOS + RESULTADOS2
LIMITE_RESUMO_PALAVRAS = (150, 500)


def extrair_secoes(tex: str) -> dict[str, str]:
    """Devolve o texto simples de cada bloco marcado no `.tex`."""
    padrao = re.compile(
        r"% >>> SECAO: (\w+)\n(.*?)\n% <<< SECAO", re.S
    )
    return {m.group(1): despir_latex(m.group(2)) for m in padrao.finditer(tex)}


def despir_latex(s: str) -> str:
    """Converte a marcação usada nas seções de volta para texto simples.

    Deliberadamente restrita ao que o texto usa: itálico, escapes de `_` e `%`,
    travessão e `\\par\\vspace` das referências. Qualquer comando não previsto
    faz o script falhar em vez de silenciosamente entregar `\\algo` ao Word.
    """
    s = re.sub(r"\\textit\{([^}]*)\}", r"\1", s)
    # `\par\vspace` separa itens que devem continuar em linhas distintas (as
    # referências). Marcado com um sentinela para sobreviver ao colapso de
    # espaços em branco logo abaixo, e restaurado como quebra de linha.
    s = re.sub(r"\\par\\vspace\{[^}]*\}\n?", "\x00", s)
    s = s.replace(r"\_", "_").replace(r"\%", "%").replace(r"\{", "{").replace(r"\}", "}")
    s = s.replace("---", "\u2014").replace("--", "\u2013")
    s = re.sub(r"[ \t]*\n[ \t]*", " ", s)
    s = "\n".join(parte.strip() for parte in s.split("\x00")).strip()
    sobrou = re.findall(r"\\[A-Za-z]+", s)
    if sobrou:
        raise SystemExit(f"comando LaTeX não tratado em despir_latex: {sobrou}")
    return s


def verificar(sec: dict[str, str]) -> list[str]:
    """Confere os limites do modelo. Devolve a lista de violações."""
    problemas = []
    for nome, limite in LIMITES_CHARS.items():
        n = len(sec[nome])
        if n > limite:
            problemas.append(f"{nome}: {n} caracteres, limite {limite}")
    n = len(sec["RESULTADOS"]) + len(sec["RESULTADOS2"]) + 1
    if n > LIMITE_RESULTADOS:
        problemas.append(f"RESULTADOS: {n} caracteres, limite {LIMITE_RESULTADOS}")
    palavras = len(sec["RESUMO"].split())
    lo, hi = LIMITE_RESUMO_PALAVRAS
    if not lo <= palavras <= hi:
        problemas.append(f"RESUMO: {palavras} palavras, faixa {lo}-{hi}")
    termos = sec["PALAVRAS"].rstrip(".").count(";") + 1
    if not 3 <= termos <= 5:
        problemas.append(f"PALAVRAS-CHAVE: {termos} termos, faixa 3-5")
    return problemas


def relatorio(sec: dict[str, str]) -> None:
    print(f"{'RESUMO':<24} {len(sec['RESUMO']):>5} chars {len(sec['RESUMO'].split()):>4} palavras  (150-500 palavras)")
    for nome, limite in LIMITES_CHARS.items():
        print(f"{nome:<24} {len(sec[nome]):>5} chars                 (limite {limite})")
    n = len(sec["RESULTADOS"]) + len(sec["RESULTADOS2"]) + 1
    print(f"{'RESULTADOS E DISCUSSÃO':<24} {n:>5} chars                 (limite {LIMITE_RESULTADOS})")
    termos = sec["PALAVRAS"].rstrip(".").count(";") + 1
    print(f"{'PALAVRAS-CHAVE':<24} {termos:>5} termos                (faixa 3-5)")


def texto_do_paragrafo(p) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t"))


def reescrever(p, novo: str) -> None:
    """Põe `novo` no primeiro `<w:t>` do parágrafo e esvazia os demais.

    Mantém o primeiro run, e com ele a fonte, o tamanho e o negrito que o
    modelo definiu para aquele parágrafo. Quebras de linha em `novo` viram
    `<w:br/>` dentro do mesmo run, o que preserva o estilo do parágrafo --
    é o caso das referências, uma por linha.
    """
    import xml.etree.ElementTree as ET

    ts = list(p.iter(W + "t"))
    if not ts:
        raise SystemExit("parágrafo sem <w:t> para reescrever")
    primeiro = ts[0]
    linhas = novo.split("\n")
    primeiro.text = linhas[0]
    primeiro.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in ts[1:]:
        t.text = ""
    if len(linhas) > 1:
        run = next(r for r in p.iter(W + "r") if primeiro in list(r.iter(W + "t")))
        pos = list(run).index(primeiro)
        for i, linha in enumerate(linhas[1:], start=1):
            br = ET.Element(W + "br")
            t = ET.Element(W + "t")
            t.text = linha
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            run.insert(pos + 2 * i - 1, br)
            run.insert(pos + 2 * i, t)


def montar_autores(p, autores: list[tuple[str, str]]) -> None:
    """Reescreve a linha de autores preservando os índices em expoente.

    O modelo marca cada índice com um run próprio em `vertAlign=superscript`.
    Reescrever o parágrafo como texto corrido perderia isso, então os runs são
    remontados a partir de dois modelos clonados do próprio arquivo: um comum,
    para o nome, e um em expoente, para o número.
    """
    import copy
    import xml.etree.ElementTree as ET

    runs = list(p.iter(W + "r"))
    normal = next(
        (r for r in runs if (rpr := r.find(W + "rPr")) is None or rpr.find(W + "vertAlign") is None),
        None,
    )
    sobrescrito = next(
        (r for r in runs
         if (rpr := r.find(W + "rPr")) is not None
         and (va := rpr.find(W + "vertAlign")) is not None
         and va.get(W + "val") == "superscript"),
        None,
    )
    if normal is None or sobrescrito is None:
        raise SystemExit("linha de autores do modelo sem run comum e run em expoente")

    def clonar(molde, texto: str):
        novo = copy.deepcopy(molde)
        for t in list(novo.iter(W + "t"))[1:]:
            novo.remove(t) if t in list(novo) else None
        ts = list(novo.iter(W + "t"))
        if not ts:
            t = ET.SubElement(novo, W + "t")
            ts = [t]
        ts[0].text = texto
        ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for t in ts[1:]:
            t.text = ""
        return novo

    novos = []
    for i, (nome, indice) in enumerate(autores):
        if i:
            novos.append(clonar(normal, ", "))
        novos.append(clonar(normal, nome))
        novos.append(clonar(sobrescrito, indice))

    for filho in list(p):
        if filho.tag == W + "r":
            p.remove(filho)
    for r in novos:
        p.append(r)


def main() -> int:
    # A entrada é um arquivo local e conhecido (o modelo oficial baixado do
    # site do evento), não conteúdo de rede, e o ElementTree não expande
    # entidades externas. Por isso a stdlib basta aqui, sem defusedxml.
    import xml.etree.ElementTree as ET

    ET.register_namespace("w", W[1:-1])
    sec = extrair_secoes((AQUI / "main.tex").read_text(encoding="utf-8"))
    faltando = {
        "RESUMO", "PALAVRAS", "INTRODUCAO", "METODOLOGIA",
        "RESULTADOS", "RESULTADOS2", "CONCLUSOES", "REFERENCIAS",
    } - set(sec)
    if faltando:
        raise SystemExit(f"seções ausentes no main.tex: {sorted(faltando)}")

    relatorio(sec)
    problemas = verificar(sec)
    if problemas:
        print("\nLIMITES VIOLADOS:", file=sys.stderr)
        for p in problemas:
            print("  " + p, file=sys.stderr)
        return 1

    if "--verificar" in sys.argv:
        return 0

    titulo = re.search(r"\n(COMPARAÇÃO DE DESEMPENHO[^\n]*)\n", (AQUI / "main.tex").read_text(encoding="utf-8"))
    subevento = "[INSERIR NOME DO SUBEVENTO E O NUMERAL DA EDIÇÃO DE 2026]"

    # Cada entrada é (trecho que identifica o parágrafo no modelo, texto novo).
    # Ordem preservada: a primeira ocorrência ainda não substituída é a alvo.
    substituicoes = [
        ("Inserir nome do subevento", subevento),
        ("INSERIR O TÍTULO", titulo.group(1).strip()),
        ("Maria X. Silva", None),  # tratada por montar_autores, com expoentes
        ("1. Estudante do curso de Graduação",
         "1. Estudante do curso de Graduação em Ciência da Computação, Instituto de "
         "Engenharia e Geociências, Universidade Federal do Oeste do Pará (IEG/UFOPA)"),
        ("2. Estudante do curso de Mestrado",
         "2. Professor do Instituto de Engenharia e Geociências, Universidade Federal "
         "do Oeste do Pará (IEG/UFOPA) \u2014 Orientador"),
        ("3. Professor do curso de Graduação", ""),
        ("Obs.: Os nomes acima são fictícios", ""),
        ("O resumo, segundo a NBR 6028", sec["RESUMO"]),
        ("Palavras-chave:  Trabalhos acadêmicos", "Palavras-chave: " + sec["PALAVRAS"]),
        ("A introdução deve apresentar o tema", sec["INTRODUCAO"]),
        ("Evidencie a relevância", ""),
        ("Descreva como o trabalho foi realizado", sec["METODOLOGIA"]),
        ("Discuta os resultados do trabalho", sec["RESULTADOS"]),
        ("Apresente as principais conclusões", sec["CONCLUSOES"]),
        ("Toda referência citada no texto deve constar", sec["REFERENCIAS"]),
        ("Autorização legal:", ""),
        ("Apoio financeiro:", ""),
    ]

    with zipfile.ZipFile(MODELO) as z:
        partes = {n: z.read(n) for n in z.namelist()}

    doc = ET.fromstring(partes["word/document.xml"])
    paragrafos = list(doc.iter(W + "p"))
    usados: set[int] = set()
    resultados2_inserido = False

    for marca, novo in substituicoes:
        alvo = None
        for i, p in enumerate(paragrafos):
            if i in usados:
                continue
            if marca in texto_do_paragrafo(p):
                alvo = (i, p)
                break
        if alvo is None:
            raise SystemExit(f"não achei no modelo o parágrafo com: {marca!r}")
        i, p = alvo
        usados.add(i)
        if novo is None:
            montar_autores(p, [("Rafael Nobre de Souza", "1"), ("Celson Pantoja Lima", "2")])
        else:
            # Parágrafo esvaziado aqui é removido na varredura final, abaixo.
            reescrever(p, novo)
        # O segundo parágrafo de resultados aproveita o parágrafo de exemplo
        # que o modelo já traz logo depois, em vez de criar um novo.
        if marca == "Discuta os resultados do trabalho" and not resultados2_inserido:
            for j in range(i + 1, len(paragrafos)):
                if j in usados:
                    continue
                if texto_do_paragrafo(paragrafos[j]).strip().startswith("Ex.: x0") or \
                   texto_do_paragrafo(paragrafos[j]).strip().startswith("x0"):
                    reescrever(paragrafos[j], sec["RESULTADOS2"])
                    usados.add(j)
                    resultados2_inserido = True
                    break
    if not resultados2_inserido:
        raise SystemExit("não achei parágrafo de exemplo para o 2o bloco de resultados")

    # Remove os parágrafos de exemplo restantes ("Ex.: x0 x0 ..." e afins) e os
    # que ficaram vazios por substituição, para o documento não herdar as
    # instruções do modelo nem páginas em branco.
    for pai in doc.iter():
        for filho in list(pai):
            if filho.tag != W + "p":
                continue
            txt = texto_do_paragrafo(filho).strip()
            if txt.startswith("Ex.: x0") or (txt.startswith("x0 x0") and txt.count("x0") > 5):
                pai.remove(filho)
            elif txt == "" and filho.find(".//" + W + "drawing") is None and \
                    filho.find(".//" + W + "br") is None and list(filho.iter(W + "t")):
                pai.remove(filho)

    partes["word/document.xml"] = ET.tostring(doc, encoding="UTF-8", xml_declaration=True)

    if SAIDA.exists():
        SAIDA.unlink()
    with zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, dados in partes.items():
            z.writestr(nome, dados)

    print(f"\ngerado: {SAIDA.name}")
    print(f"modelo original intocado: {MODELO.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
