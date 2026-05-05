---
tipo: paper
autores: ["Aerospike (corporate blog)"]
ano: 2025
titulo: "Best practices for database benchmarking"
venue: "Aerospike Blog"
tags: [benchmark, metodologia, prática, blog]
citacao_abnt: "AEROSPIKE. Best practices for database benchmarking. Aerospike Blog, 2025. Disponível em: https://www.aerospike.com/blog/best-practices-for-database-benchmarking/. Acesso em: 9 dez. 2025."
arquivo_local: "Best practices for database benchmarking _ Aerospike.html"
---

# Best practices for database benchmarking

> **Status do fichamento:** referência operacional (post de blog corporativo, não paper acadêmico). Preenchido a partir do tema declarado e práticas estabelecidas da literatura. Validar e datar a partir do HTML salvo localmente.

## Síntese
Guia operacional sobre boas práticas em benchmarking de SGBDs, escrito do ponto de vista de uma fornecedora de banco de dados. Cobre o conjunto de cuidados práticos que distinguem um benchmark publicável de um número de marketing: representatividade da carga, isolamento do ambiente, distinção entre cache quente e frio, importância das caudas de latência (p99), e neutralidade entre fornecedores.

## Contribuições
- **Operacional, não acadêmica.** Serve como checklist prático para o protocolo dos experimentos da IC.
- Discussão de armadilhas comuns: usar cargas sintéticas demais, ignorar warmup, comparar versões diferentes, ignorar tail latency.

## Método
*[Não aplicável — material expositivo. Catalogar os tópicos cobertos a partir do HTML.]*

## Pontos de aplicação no protocolo da IC
- **Warmup:** descartar primeiras execuções até estabilização de cache.
- **Carga representativa:** queries variadas, não loop sobre uma única; respeitar a distribuição esperada em produção.
- **Isolamento:** containers dedicados, sem competição por recursos no host.
- **Reprodutibilidade:** versões pinadas, seeds documentados.
- **Tail latency (p99, p99.9):** reportar, não esconder atrás da média.
- **Neutralidade:** documentar configuração de cada sistema com simetria.

## Limitações
- Material de marketing/educacional; não é peer-reviewed.
- Eventuais vieses pró-Aerospike (não relevantes para esta IC, mas notar ao citar).

## Relevância para a IC
**Sustenta §3.6 do relatório parcial** ([[referência/metodologia-benchmarking-ann]]) como **referência prática complementar** ao ANN-Benchmarks. Onde o ANN-Benchmarks foca em algoritmos isolados, este guia cobre o que vem depois: o sistema-em-operação. As recomendações entram diretamente no protocolo dos experimentos das Etapas 3 e 4.

## Citáveis
> *[Selecionar 1–2 frases sobre warmup, tail latency ou representatividade da carga.]*

## Backlinks
- [[referência/metodologia-benchmarking-ann]]
- [[papers/Aumuller-Bernhardsson-Faithfull-2020-ANN-Benchmarks]]
