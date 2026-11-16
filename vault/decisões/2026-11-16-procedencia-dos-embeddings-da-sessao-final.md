---
tipo: decisão
data: 2026-11-16
status: aceita
autores: ["Rafael Nobre"]
tags: [embeddings, procedência, reprodutibilidade, sessão-de-medição, escala-1m]
---

# Procedência dos embeddings da sessão final: base de 1M gerada na máquina de trabalho

Registrada antes da sessão de medição, com o critério de aceite fixado antes de conhecer o resultado da verificação.

## Contexto

Os embeddings de 1 milhão de passagens precisam existir antes da sessão. A geração na CPU da máquina de referência roda a cerca de 100 passagens por segundo e começou em 15/11; a máquina foi desligada às 13h15, antes de o arquivo ser gravado, e o trabalho se perdeu. Refazer ali custaria cerca de três horas, e a sessão completa, estimada em 5,3 horas, deixaria de caber na janela da madrugada (cerca de 7 horas).

## Opções consideradas

1. **Gerar de novo na CPU da máquina de referência**
   - Prós: procedência idêntica à de julho.
   - Contras: a sessão ultrapassa a janela em cerca de 1,5 hora, ou se parte em duas.
2. **Gerar a base na GPU da máquina de trabalho e verificar a equivalência antes de medir** (escolhida)
   - Prós: a base fica pronta em cerca de 45 minutos.
   - Contras: muda o hardware em que a entrada foi produzida; exige prova de que os vetores são os mesmos para efeito do estudo.

## Decisão

**Escolhida:** opção 2.

- **Base (1.001.000 vetores: 1M e as 1.000 consultas):** gerada na máquina de trabalho (Apple M4, GPU via MPS), com o mesmo modelo, os mesmos textos, a mesma normalização L2 e o mesmo tamanho de lote (64) de `pipeline/embeddings.py`, gravada com a mesma chave de cache. Um processo por bloco de 20 mil textos: o driver do MPS retém memória entre chamadas (medido: +2,5 GiB a cada 5 mil textos) e só a devolve ao fim do processo.
- **Pool de inserções do Cenário C (80.000 vetores):** gerado na CPU da máquina de referência, em paralelo.
- **Fonte única nas três escalas:** 100k e 500k passam a ler prefixos do mesmo arquivo de 1M. Os caches de julho e agosto (CPU da máquina de referência) são movidos para `data/embeddings/anteriores-cpu-fedora/`, não apagados.
- **Critério de aceite, verificado na máquina de referência antes de medir:**
  - textos idênticos (chave de cache = SHA-256 do nome do modelo e dos textos, recalculada lá);
  - `float32`, sem NaN, norma L2 a menos de 1e-5 de 1;
  - diferença máxima elemento a elemento < 1e-4 contra o cache de julho nos primeiros 501 mil vetores, e contra 2.000 vetores da faixa [501 mil, 1.001.000) recodificados ali na CPU;
  - top-10 exato (como conjunto) das 1.000 consultas da escala de 500 mil igual em pelo menos 99,9% das posições, calculado com cada uma das duas fontes.
- Se o critério falhar, a base é gerada na CPU da máquina de referência e a sessão é partida, com a partição declarada.

## Justificativa

Embeddings são entrada, não medida: nenhuma métrica de latência, *recall*, memória ou disco depende do hardware em que o vetor foi calculado, desde que o vetor seja o mesmo. A diferença esperada entre CPU e GPU em `float32` é de arredondamento, e o critério acima a torna verificável em vez de suposta. O teste que importa para o estudo é o do top-10 exato: se a verdade exata é a mesma com as duas fontes, o *recall* medido não pode depender da troca.

## Evidência

Verificação executada na máquina de referência em 16/11/2026, às 02h38, antes de qualquer medição da sessão (`verificar_embeddings.py`, saída guardada em `code/results/sessoes/2026-11-16-final/verificacao_embeddings.json`):

| Item | Resultado | Critério |
|---|---|---|
| Textos idênticos (chave de cache recalculada) | sim, base e inserções | igual |
| Forma, tipo, NaN | 1.001.000 × 384 e 80.000 × 384, `float32`, 0 NaN | — |
| Desvio máximo da norma L2 | 1,2 × 10⁻⁷ (base), 1,8 × 10⁻⁷ (inserções) | < 1 × 10⁻⁵ |
| Diferença máxima contra o cache de julho, primeiros 501 mil | 5,0 × 10⁻⁷ (média 3,3 × 10⁻⁸) | < 1 × 10⁻⁴ |
| Diferença máxima, 2.000 vetores da faixa [501 mil, 1.001.000) recodificados na CPU | 3,1 × 10⁻⁷ | < 1 × 10⁻⁴ |
| Top-10 exato das 1.000 consultas de 500k igual (conjunto) | 100% | ≥ 99,9% |

Aceite: sim. O arquivo chegou à máquina de referência por rede local, com SHA-256 igual ao da origem (`39d0caa6…`). Os caches antigos estão em `data/embeddings/anteriores-cpu-fedora/`; as escalas de 100k e 500k leem agora prefixos do arquivo novo.

## Consequência

- O relatório final declara a procedência dos embeddings e a evidência de equivalência.
- A comparação com a sessão de 23/08 passa a envolver também a fonte dos embeddings; a evidência acima limita esse efeito.

## Backlinks

- [[2026-04-28-modelo-embedding-minilm]]
- [[2026-08-19-divisao-de-maquinas-mac-dell]]
- [[2026-11-15-protocolo-da-sessao-final]]
