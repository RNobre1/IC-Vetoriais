---
tipo: referência
conceito: "Vector Space Model (VSM)"
tags: [ir, vsm, esparso, salton]
---

# Vector Space Model (VSM)

## Definição
Modelo clássico de Recuperação de Informação proposto por Salton, Wong e Yang (1975). Representa documentos e consultas como vetores em um espaço cuja dimensionalidade é o tamanho do vocabulário (|V|). Cada coordenada corresponde a um termo; o valor é tipicamente o peso TF-IDF do termo no documento.

## Formalização
Para um documento d e consulta q sobre vocabulário V = {t₁, ..., tₙ}:

- d⃗ = (w₁,d, w₂,d, ..., wₙ,d), onde wᵢ,d = tf(tᵢ, d) · idf(tᵢ)
- tf(tᵢ, d) = frequência do termo tᵢ em d (ou variantes log-normalizadas)
- idf(tᵢ) = log(N / df(tᵢ)), com N = total de documentos e df(tᵢ) = documentos contendo tᵢ

Similaridade cosseno entre vetores:

sim(d, q) = (d⃗ · q⃗) / (‖d⃗‖ · ‖q⃗‖)

Documentos são ranqueados pela similaridade em ordem decrescente.

## Variantes
- **BoW (Bag-of-Words):** mesma representação sem ponderação IDF.
- **BM25:** evolução do TF-IDF com saturação de TF e normalização por comprimento. Padrão de IR clássica.
- **n-gramas:** termos compostos (bigramas, trigramas) como dimensões adicionais.
- **LSI/LSA:** decomposição SVD do VSM para reduzir dimensionalidade e capturar sinônimos latentes.

## Onde aparece neste estudo
Seção §3.1 do relatório parcial — fundamenta a passagem do VSM esparso (clássico) para embeddings densos (§3.2). A IC **não usa VSM nos experimentos**; ele aparece apenas como motivação histórica e ponto de partida conceitual.

## Papers canônicos
- [[papers/Salton-Wong-Yang-1975-VSM]]

## Pegadinhas
- VSM clássico tem dimensionalidade igual ao vocabulário (|V| pode ser ~10⁵–10⁶), mas é **extremamente esparso** (a maioria das coordenadas é zero). Embeddings densos têm dimensionalidade muito menor (~10²–10³) com todas as coordenadas com valor — propriedade fundamental para indexação ANN.
- Cosseno em VSM clássico mede sobreposição de termos exatos. Não captura sinônimos sem extensão (LSI, query expansion, stemming).
- Não confundir "VSM" com "vector database": VSM é o modelo conceitual; um banco vetorial é a infraestrutura que armazena e indexa vetores (de qualquer origem, incluindo embeddings densos).
