---
tipo: lição-aprendida
data: 2026-05-05
contexto: Etapa 2 / Dia 1 — execução do `make deps` + `make up` + `make smoke`
tags: [dependencias, python, docker, weaviate, psycopg, py314]
---

# Três armadilhas no setup inicial do ambiente da Etapa 2

## Situação
Em 2026-05-05, ao executar pela primeira vez `make deps` + `docker compose up -d --wait` + `make smoke` no notebook-alvo (Fedora 43, Python 3.14.3), três falhas precisaram de correção antes do Dia 1 fechar com 6/6 testes integrados verdes.

## Armadilha 1 — `weaviate-client 4.9.6` exige `httpx<=0.27.0`
**Sintoma:** `ResolutionImpossible` ao instalar; pip reclamava de conflito entre `httpx==0.28.1` (que pinei) e `weaviate-client 4.9.6 depends on httpx<=0.27.0`.

**Causa:** assumi um `httpx` recente sem checar constraints transitivas. weaviate-client 4.9.6 fixa o teto em `<=0.27.0` (não `<0.28`).

**Correção:** pinar `httpx==0.27.0` em `code/requirements.txt`.

**Aplicação a futuro:** se for necessário bumpar `httpx` para 0.28+ (e.g. usar features novas), **bumpar weaviate-client junto** para uma versão que aceite o range mais amplo (4.10+ provavelmente). Registrar como ADR a decisão de bump e suas implicações de teste.

## Armadilha 2 — `psycopg-binary==3.2.3` sem wheel para Python 3.14
**Sintoma:** `Could not find a version that satisfies the requirement psycopg-binary==3.2.3; (...) (from versions: 3.2.10, 3.2.11, 3.2.12, 3.2.13, 3.3.0, 3.3.1, 3.3.2, 3.3.3, 3.3.4)`.

**Causa:** Python 3.14 é recente; pacotes com extensões C precisam de releases que tragam wheels para `cp314`. `psycopg-binary` só ganhou esse suporte a partir de 3.2.10. Versão 3.2.3 só tem wheels para 3.11–3.13.

**Correção:** bump para `psycopg[binary,pool]==3.2.13`.

**Aplicação a futuro:**
- Antes de pinar versão de pacote com extensão C, conferir se há wheel para a versão exata do Python do hardware-alvo (`python --version`).
- O notebook do bolsista roda Python 3.14 (default Fedora 43); a CI roda Python 3.11 (fixado no workflow). **Ambos precisam de wheels disponíveis.**
- Lista de pacotes com C-ext que esta IC usa: `psycopg-binary`, `numpy`, `grpcio`, `cryptography`, `cffi`. Sempre que bumpar esses, conferir disponibilidade de wheel py3.14.

## Armadilha 3 — `weaviate-client 4.x` exige porto gRPC 50051 exposto
**Sintoma:** `WeaviateGRPCUnavailableError: gRPC health check against Weaviate could not be completed (...) localhost:50051`. O endpoint REST (`/v1/.well-known/ready`) respondia OK, mas qualquer operação real (criar coleção, insert, search) falhava.

**Causa:** Weaviate 1.20+ usa gRPC como caminho preferencial para operações de dados. O cliente v4 conecta via gRPC para criar/consultar coleções, não via REST. O `docker-compose.yml` inicial só expunha 8080 (REST); 50051 (gRPC) ficou inacessível do host.

**Correção:** adicionar mapeamento `${WEAVIATE_GRPC_PORT:-50051}:50051` ao serviço `weaviate` do `docker-compose.yml` e nova variável `WEAVIATE_GRPC_PORT=50051` em `.env.example`.

**Aplicação a futuro:**
- Documentação oficial do Weaviate menciona gRPC, mas não destaca para iniciantes. Sempre expor 50051 quando usar weaviate-client v4+.
- Se em algum momento a rede do experimento ficar atrás de firewall/NAT (e.g. Cluster HPC do IEG), confirmar que **ambas** as portas (8080 e 50051) estão liberadas.
- Para Qdrant, situação análoga: REST em 6333, gRPC em 6334. **Ambas já estavam expostas** no compose inicial; manter assim para não cair na mesma armadilha.

## Lições gerais
1. **Pinning não é checagem de compatibilidade.** Pinar versões dá reprodutibilidade, mas não garante que o conjunto resolve. Rodar `pip install` cedo é a única forma de validar.
2. **Versão do interpretador importa para wheels.** A escolha de Python (3.14 local vs 3.11 CI) precisa ser checada contra cada pacote com C-ext.
3. **gRPC vs REST em SGBDs vetoriais não é detalhe.** Cada sistema (Qdrant, Weaviate, possivelmente Milvus se vier no futuro) tem padrões próprios de protocolo de transporte. Verificar e expor todas as portas relevantes.

## Backlinks
- [[../decisões/2026-05-05-versoes-imagens-docker]]
- [[../decisões/2026-04-28-sistemas-avaliados]]
- [[2026-05-05-rigor-citacoes-abnt]]
