# Execução complementar: controle do Cenário B padrão do Weaviate em 500k

Medida logo após a sessão de 16/11/2026 (07h43 a 08h08), fora da janela da sessão. Os valores daqui não entram nas tabelas do relatório; servem só para a leitura do critério de controle.

## Por quê

O critério de controle fixado antes da sessão (`vault/decisões/2026-11-15-protocolo-da-sessao-final.md`) exigia |recall padrão − recall equalizado| ≤ 0,005 em p = 10%, em todos os `ef_search`. Em 500k o critério falhou em `ef_search = 16` (0,7539 contra 0,7660). A regra previa, nesse caso, medir as células omitidas do B padrão (p = 50% e 100%, `ef_search` 16, 32, 128 e 256) com a folga da janela.

## O que foi feito

1. `make reset-medicao` (volumes apagados e contêineres recriados; o comando foi interrompido durante a espera do healthcheck, com os contêineres já iniciados, como mostra `reset.log`).
2. Três chamadas do executor antigo do Cenário B, condição padrão, uma por seletividade, com prazo de corte às 08h15 (`log_d9.txt`):
   - p = 10%, `ef_search` = 16 (primeiro, para separar variância entre construções de caminho distinto);
   - p = 50%, `ef_search` = 16, 32, 128 e 256;
   - p = 100%, `ef_search` = 16, 32, 128 e 256.
3. Contêineres parados ao fim.

Cada chamada do executor carrega a base e constrói um grafo HNSW novo. Os três arquivos vêm, portanto, de três grafos diferentes dos da sessão.

## Leitura

| p | ef | recall complementar | recall equalizado (sessão) | diferença |
|---|---|---|---|---|
| 10% | 16 | 0,7592 | 0,7660 | 0,0068 |
| 50% | 16 | 0,8925 | 0,8934 | 0,0009 |
| 50% | 32 | 0,9478 | 0,9489 | 0,0011 |
| 50% | 128 | 0,9911 | 0,9894 | 0,0017 |
| 50% | 256 | 0,9964 | 0,9957 | 0,0007 |
| 100% | 16 | 0,8474 | 0,8490 | 0,0016 |
| 100% | 32 | 0,9157 | 0,9197 | 0,0040 |
| 100% | 128 | 0,9785 | 0,9781 | 0,0004 |
| 100% | 256 | 0,9899 | 0,9914 | 0,0015 |

Em p = 10% e `ef_search` = 16, o terceiro grafo ficou entre os dois valores da sessão (0,7539 no padrão, 0,7660 no equalizado). Nas oito células omitidas, a diferença para o equalizado ficou abaixo de 0,005 mesmo entre grafos distintos.

A latência daqui vale só como ordem de grandeza: os contêineres não foram reiniciados entre as chamadas, e o Weaviate começou a segunda e a terceira com cerca de 2,4 GB de memória residente herdados da chamada anterior.
