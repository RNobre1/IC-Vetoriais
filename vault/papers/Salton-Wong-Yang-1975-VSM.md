---
tipo: paper
autores: ["Salton, G.", "Wong, A.", "Yang, C. S."]
ano: 1975
titulo: "A Vector Space Model for Automatic Indexing"
venue: "Communications of the ACM"
tags: [vsm, ir, indexação, esparso, foundational]
citacao_abnt: "SALTON, G.; WONG, A.; YANG, C. S. A vector space model for automatic indexing. Communications of the ACM, v. 18, n. 11, p. 613–620, 1975."
arquivo_local: "A Vector Space Model for Automatic Index.pdf"
---

# A Vector Space Model for Automatic Indexing

> **Status do fichamento:** preenchido a partir de conhecimento prévio do paper (texto canônico de IR) + título e citação no docx. Sem citáveis diretos pendentes — revisar antes do relatório final.

## Síntese
Paper canônico que introduz o **Vector Space Model (VSM)** como formalização de Recuperação de Informação. Documentos e consultas são representados como vetores de pesos em um espaço cujas dimensões são os termos do vocabulário. A relevância é medida por similaridade geométrica (originalmente produto interno e variantes; o cosseno se consolidou como padrão na literatura subsequente). Estabelece a base conceitual sobre a qual TF-IDF, LSI/LSA e (por extensão) embeddings densos modernos se apoiam.

## Contribuições
- Formalização vetorial de documentos para IR, substituindo modelos puramente booleanos.
- Demonstração de que pesos (TF) por termo, em vez de presença binária, melhoram qualidade de retrieval.
- Estabelecimento da geometria como ferramenta de IR — abre caminho para técnicas posteriores de redução de dimensionalidade (LSI) e, no longo prazo, embeddings.

## Método
*[Detalhar a partir do PDF: experimentos com coleções da época (CACM, MEDLARS), escolha de pesos, comparação com modelo booleano.]*

## Resultados-chave
*[Resultados experimentais específicos do paper — preencher com números do PDF.]*

## Limitações
- Dimensionalidade igual ao tamanho do vocabulário (~10⁵–10⁶); vetores extremamente esparsos.
- Não captura sinonímia nem polissemia sem extensões.
- Assume independência entre termos (Bag-of-Words).

## Relevância para a IC
**Sustenta §3.1 do relatório parcial.** É o ponto de partida histórico para justificar a transição para embeddings densos (§3.2). Não usado diretamente nos experimentos — entra apenas como motivação conceitual e fundamentação teórica.

## Citáveis
> *[Selecionar 1–2 frases do paper para citação direta no relatório, com número de página.]*

## Backlinks
- [[referência/vector-space-model]]
- [[referência/embeddings-densos]]
- [[drafts/...]]
