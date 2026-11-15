---
tipo: decisão
data: 2026-11-15
status: aceita
autores: ["Rafael Nobre"]
tags: [metodologia, protocolo, sessão-de-medição, escala-1m, reprodutibilidade, etapa-4]
---

# Protocolo da sessão final: um seed por sistema e escala, cada sistema medido sozinho

Registrada **antes** de qualquer dado oficial da sessão, para que nenhuma escolha abaixo possa ser lida como ajuste feito depois de ver o resultado.

## Contexto

O relatório final precisa da escala de 1 milhão de vetores nos Cenários A e B e do Cenário C. A regra do relatório parcial é que todo valor reportado venha de **uma única sessão de medição** ([[2026-08-22-medicao-de-footprint-e-tempo-de-indexacao]]): a latência variou até 3,3 vezes entre as sessões de julho e de 23/08, enquanto o recall reproduziu. Juntar 1M medido agora com 100k e 500k de agosto misturaria estados do hospedeiro justamente na comparação entre escalas.

A sessão nova, completa (100k, 500k e 1M), tinha uma janela única de cerca de 7 horas na máquina de referência. Com o protocolo de 23/08 — volumes zerados antes de **cada** comando e cada comando semeando os três sistemas — a estimativa a partir dos tempos medidos em 23/08 passava de 10 horas. Dois custos dominam:

- o seed do pgvector: 1.272 s em 500k, com `maintenance_work_mem` no *default* da imagem; em 1M, estimado em perto de uma hora, e o protocolo antigo o repetiria quatro vezes (A, B padrão, B equalizado, C);
- as consultas filtradas do Weaviate no Cenário B: 1.563 s por condição em 500k, cerca do dobro esperado em 1M.

## Opções consideradas

1. **Protocolo de 23/08 intacto**
   - Prós: comparabilidade direta com agosto.
   - Contras: não cabe na janela; a sessão se partiria em duas, o que é o problema que a sessão única existe para evitar.
2. **Sessão nova só em 1M, mantendo 100k e 500k de agosto**
   - Prós: cabe com folga.
   - Contras: a curva de escala cruza sessões na métrica que não reproduz (latência).
3. **Sessão nova completa com seeds compartilhados e execução por sistema** (escolhida)
   - Prós: cabe na janela; uma sessão só para as três escalas.
   - Contras: muda o protocolo em pontos que precisam ser declarados; agosto passa a ser dado anterior, não réplica direta.

## Decisão

**Escolhida:** opção 3, com os seguintes elementos.

- **pgvector: um seed por escala**, no layout do Cenário B (vetores e coluna `seletor` preenchida, sem índice nela), seguido de `VACUUM (ANALYZE)` fora do relógio. Nesse seed medem-se recursos e tempo de indexação, Cenário A e B padrão. O B equalizado recebe só o B-tree em `seletor` (tempo registrado) — no pgvector a equalização é exatamente esse índice. Em 1M, o B-tree é removido e o Cenário C roda por último, porque insere vetores. Diferença declarada em relação a agosto: a tabela medida no A tem `seletor` preenchido em vez de nulo; o índice HNSW tem os mesmos parâmetros.
- **Qdrant e Weaviate: um seed por layout** (B padrão, B equalizado, A, nesta ordem). São baratos, e no Qdrant o índice de payload em `seletor` pode alterar o grafo HNSW — hipótese não verificada, mas suficiente para não medir o A numa coleção que o tenha. O C roda na coleção do A e é o último passo de todos os sistemas: se a escrita concorrente falhar, os demais cenários já estão gravados.
- **Cada sistema medido sem os dados dos outros.** Contêiner e volume do serviço são recriados no início do bloco do sistema e a cada descarte; os contêineres dos outros dois continuam de pé, vazios e ociosos. Em agosto as coleções dos outros dois ficavam residentes, ociosas, durante a medição de cada um; apagar coleção não basta, porque o processo pode reter memória e a linha de base de RSS deixaria de ser limpa.
- **Ordem dos sistemas girada por escala**: 100k pgvector → Qdrant → Weaviate; 1M Qdrant → Weaviate → pgvector; 500k Weaviate → pgvector → Qdrant. Com execução por sistema, os sistemas de uma mesma escala ficam horas distantes; girar a ordem impede que ordem e sistema se confundam.
- **Ordem das escalas: 100k, 1M, 500k.** O 500k tem dado datado de agosto como referência; o 1M não tem nenhum.
- **Sonda fixa de CPU** (carga sintética de uma thread) antes e depois de cada bloco, e amostrador de recursos a 1 Hz durante toda a sessão (memória, swap, pressão PSI, faltas de página maiores, CPU e *throttling* do hospedeiro; memória e CPU de cada contêiner). Marcos de fase em JSONL permitem atribuir cada amostra a seed, A, B ou C — o que fecha a ressalva do parcial de que não se sabia em qual fase o swap ocorreu.
- **Ponte de protocolo**: o Cenário A em 100k é medido também pelo protocolo de agosto, na mesma sessão. Separa o efeito da mudança de protocolo do efeito da sessão.
- **Repetições**: Cenário A com 5 repetições das 1.000 consultas por ponto, com a repetição como laço externo, a ordem dos valores de `ef_search` alternada entre repetições e aquecimento de 50 buscas antes de cada bloco. Reporta-se a mediana entre repetições, a amplitude e o p99 agrupado (5.000 amostras). Isso mede repetibilidade dentro da sessão, não reprodutibilidade entre sessões, e não é apresentado como intervalo de confiança. Cenário B com uma passagem, como em agosto: a latência do B é lida em ordem de grandeza.
- **Cenário B padrão do Weaviate em 500k e 1M**: seletividades de 1% e 10% com o varrimento completo; 50% e 100% só em `ef_search = 64`. Acima do `flatSearchCutoff` (40.000 elegíveis), padrão e equalizado executam o mesmo caminho HNSW — em agosto coincidiram nas oito séries. A seletividade de 10% fica acima do corte nas duas escalas e serve de controle.
  - **Critério do controle, fixado agora:** em p = 10%, |recall padrão − recall equalizado| ≤ 0,005 em todos os `ef_search`. Se falhar, as células omitidas são medidas com a folga da janela, e a hipótese de caminho idêntico é registrada como refutada.
  - Nas tabelas, as células omitidas aparecem como "não medido", nunca preenchidas com o valor equalizado.
- **Validade por bloco**: cada passo grava as páginas enviadas ao swap durante a própria medição. Valor diferente de zero não invalida automaticamente o dado — o swap pode ser de outro processo —, mas é cruzado com a pressão de memória (PSI) e com a memória do contêiner antes de o número entrar em tabela.

## Justificativa

O seed do HNSW no pgvector é o mesmo nos três layouts — mesmos vetores, mesmos parâmetros —, e o que distingue A, B padrão e B equalizado nesse sistema é o predicado e o índice no atributo, não o grafo. Semeá-lo quatro vezes em 1M mediria quatro vezes a mesma coisa. Nos especializados o raciocínio não vale, porque a configuração da coleção (índice de payload, limiar de varredura exata) é definida na criação e pode afetar o índice.

Medir cada sistema sozinho troca uma confusão por outra: elimina a pressão de memória das coleções vizinhas, que em agosto coincidiu com swap-out em três das seis execuções, mas afasta no tempo os sistemas de uma mesma escala. A rotação de ordem, a sonda de CPU e o amostrador existem para tornar essa segunda confusão visível em vez de supor que não existe.

## Consequência

- A sessão de 15/11/2026 substitui a de 23/08 como sessão vigente. A de 23/08 continua como dado datado, útil para tendência e reprodutibilidade do recall, sem mesclar valores nas mesmas tabelas.
- Footprint e tempo de indexação do pgvector passam a vir do seed com `seletor` preenchido; a diferença de disco entre os layouts é medida no ensaio em 100k e declarada.
- Novos artefatos versionados por sessão em `code/results/sessoes/<id>/`: ambiente, progresso, marcos e o CSV do amostrador.
- O executor é `benchmarks/run_sessao.py`; o roteiro, `scripts/sessao_final.sh` (`make sessao`).

## Critério de revisão

Reabrir se o controle do Weaviate falhar; se a ponte mostrar diferença de protocolo maior que a variação entre repetições; se o amostrador mostrar pressão de memória sustentada durante medição; ou se a sessão não couber na janela e precisar ser partida.

## Backlinks

- [[2026-04-28-cenarios-A-B-C]]
- [[2026-04-28-tamanhos-100k-500k-1m]]
- [[2026-08-16-equalizacao-cenario-b]]
- [[2026-08-22-medicao-de-footprint-e-tempo-de-indexacao]]
- [[2026-08-19-divisao-de-maquinas-mac-dell]]
- [[2026-11-15-desenho-do-cenario-c]]
