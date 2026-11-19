# Colocar ARCAMBE GeoAnalytics online

Estado: configuração de produção preparada, **ainda não publicada**. Não existe projeto Google Cloud/Firebase configurado nesta entrega. Não foi criado nenhum recurso pago.

## O que o proprietário precisa de criar

1. Criar um projeto na [consola Firebase](https://console.firebase.google.com/) e anotar o **ID do projeto**. Firebase e Google Cloud usam o mesmo projeto subjacente.
2. Em Authentication → Sign-in method, ativar Email/Password e/ou Google, conforme o método de entrada pretendido. Em Settings → Authorized domains, acrescentar o domínio final da plataforma.
3. Em Project settings → Your apps, registar uma aplicação Web. Guardar `apiKey`, `authDomain` e `projectId`. Estes são parâmetros públicos da aplicação Web; uma chave privada de conta de serviço nunca deve ir para o frontend ou GitHub.
4. Para alojar o processamento, associar uma conta de faturação ao projeto Google Cloud e definir um orçamento com alertas. Alertas de orçamento não interrompem automaticamente o consumo. O valor mensal precisa de ser escolhido pelo proprietário antes de criar infraestrutura.
5. Disponibilizar um domínio/subdomínio para HTTPS. O repositório GitHub guarda o código; é necessário um servidor para executar a API e processar os rasters.

Partilhar na conversa apenas o ID do projeto, o domínio pretendido e o orçamento mensal. Não enviar senhas, chaves privadas nem dados de pagamento.

## Imagens de satélite e API

A API Python da ARCAMBE já acompanha o projeto. A interface comunica com `/api/v1/...`; o servidor encaminha as chamadas para a API interna. O login Firebase autentica cada utilizador.

- Sentinel-2 fica por defeito. Earth Search Collection 1 permite o acesso aos rasters utilizado nos testes reais. Copernicus Data Space também está disponível para pesquisa; encontrar uma cena não garante que o seu raster esteja acessível sem a configuração específica desse fornecedor.
- Landsat 8/9 Collection 2 Level-2 usa o catálogo público Microsoft Planetary Computer. O servidor obtém automaticamente uma assinatura temporária para ler os rasters; não é necessário introduzir um token na interface.
- Landsat usa 30 m, bandas `SR_B1` a `SR_B7`, calibração do STAC e máscaras `QA_PIXEL`/`QA_RADSAT`. Estão disponíveis 19 índices; NDRE e CI_RE exigem Sentinel-2. A comparação temporal entre sensores é recusada até existir harmonização validada.
- Os dados públicos não eliminam os custos de processamento, armazenamento e tráfego do alojamento.

## Primeira instalação online

O ficheiro `infra/production/compose.yaml` define uma instalação inicial num único servidor Linux com Docker Compose: HTTPS Caddy, Next.js, FastAPI, worker contínuo e PostgreSQL/PostGIS. Apenas portas 80/443 são públicas; base de dados, API e rasters ficam em rede/volumes privados. O modo é fixado em `production`, com autenticação Firebase real. Esta opção preserva a fila durável já implementada.

O servidor pode ser uma VM Google Compute Engine com disco persistente e conta de serviço anexada. A dimensão e região devem ser escolhidas depois de confirmar orçamento e carga; esta entrega não cria a VM. A conta de serviço precisa de `firebaseauth.users.get` (por exemplo, `roles/firebaseauth.viewer`) para a verificação de sessões revogadas. Usar credenciais automáticas da VM, sem distribuir ficheiros JSON. Não anexar credenciais administrativas gerais.

Depois de disponibilizar servidor, domínio e acesso ao repositório privado:

```bash
# Na pasta do código, no servidor Linux com Docker e plugin Compose instalados:
python3 scripts/configure-production.py
docker compose --env-file .env.production -f infra/production/compose.yaml config --quiet
docker compose --env-file .env.production -f infra/production/compose.yaml up -d --build
docker compose --env-file .env.production -f infra/production/compose.yaml ps
```

O configurador pede os parâmetros públicos Firebase e gera senhas aleatórias localmente. Não imprimir a configuração resolvida, pois contém segredos. O DNS deve apontar para o servidor e permitir portas 80/443 para que Caddy obtenha o certificado.

Antes de receber utilizadores: verificar login real, uma pesquisa e análise Sentinel, uma análise Landsat, exportação autenticada, isolamento entre dois utilizadores e restauro de uma cópia de segurança. Configurar snapshots/cópias do PostgreSQL e do volume de rasters, monitorização de disco e alertas de faturação. Nunca executar `docker compose down -v` num ambiente com dados a conservar.

Esta instalação tem um ponto único de falha. O Terraform em `infra/gcp` é apenas a base de GCS/IAM/segredos para uma evolução posterior; não constitui implantação Cloud Run/Cloud SQL. Não usar o worker contínuo num serviço Cloud Run sem definir como recebe CPU e executa os trabalhos.

## Referências

- [Relação Firebase/Google Cloud](https://firebase.google.com/docs/projects/learn-more)
- [Configuração Firebase Authentication Web](https://firebase.google.com/docs/auth/web/start)
- [Criar VM Compute Engine](https://cloud.google.com/compute/docs/instances/create-start-instance)
- [Orçamentos e alertas Google Cloud](https://cloud.google.com/billing/docs/how-to/budgets)
- [Docker Engine Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Qualidade Landsat Collection 2 — USGS](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands)
- [Planetary Computer: assinaturas de acesso](https://planetarycomputer.microsoft.com/docs/concepts/sas/)
