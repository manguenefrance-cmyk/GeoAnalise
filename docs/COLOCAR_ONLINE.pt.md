# Colocar ARCAMBE GeoAnalytics online

Estado em 24 de novembro de 2026: interface publicada em [geo-analise.vercel.app](https://geo-analise.vercel.app), no plano Vercel Hobby. A API, a base de dados e o processamento ainda não estão ligados à interface publicada. O projeto Firebase `arcambe-geoanalytics` está no plano Spark; a configuração pública está integrada. Não foi criado nenhum recurso pago.

A próxima implantação tem código preparado para Render Free e Supabase Free. O projeto Supabase `bmoabalkqotxrswcraby` foi criado no plano Free; o Render tem um Blueprint preparado, ainda sem aplicação do plano. Seguir [API gratuita](API_GRATUITA.pt.md) para os segredos, schema privado, armazenamento de resultados e verificação completa. As duas integrações já estão ligadas, mas os segredos ainda precisam de ser configurados nas consolas; este estado não é uma implantação da API concluída.

## Fase atual: testes com orçamento zero — 20 de novembro de 2026

Decisão do proprietário: não gastar dinheiro nesta fase. Não associar cartão nem conta Cloud Billing, não ativar Blaze, não criar VM paga e não executar Terraform. A infraestrutura paga fica adiada até à decisão de comercializar.

**Esclarecimento de escopo:** o proprietário quer a plataforma final funcional com contas, planos gratuitos e pagos, assinaturas e pagamentos. A suspensão refere-se aos seus gastos com domínio, infraestrutura e serviços pagos. O desenvolvimento comercial continua no escopo; as transações serão verificadas em modo de teste antes da ativação de cobranças reais. Não confundir plano pago oferecido aos clientes com plano pago de alojamento contratado pelo proprietário.

Na página Firebase apresentada:

1. Clicar **Ir para o console** e depois **Criar um projeto**.
2. Nome sugerido: **ARCAMBE GeoAnalytics**. Anotar o ID atribuído ao projeto.
3. Para simplificar os testes, desativar Google Analytics se essa opção aparecer; não é necessário para o login.
4. Concluir a criação e manter **Spark — gratuito**. Se aparecer uma proposta de ativar faturação/Blaze, não a ativar.
5. Abrir Authentication → Começar e ativar **E-mail/senha**.

O Spark permite começar sem dados de pagamento e inclui opções de autenticação gratuitas dentro dos limites aplicáveis. Será usado para o login. Não confundir com App Hosting: este exige Blaze. A API Python, o worker e o PostGIS não ficam alojados gratuitamente no Firebase apenas por criar este projeto.

Referências oficiais: [planos Firebase](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans), [App Hosting e faturação](https://firebase.google.com/docs/app-hosting/costs).

O projeto Firebase já foi criado e o proprietário publicou a interface na Vercel. O alojamento de teste da API e do processamento ainda precisa de ser configurado e validado. O laboratório local continua disponível. Não comprar domínio nesta fase; usar os subdomínios gratuitos dos fornecedores.

## Configuração pública integrada — 20 de novembro de 2026

O perfil Web fornecido pelo proprietário está em `apps/web/lib/firebase-public.json`. A interface usa esse perfil por padrão e permite substituição através das variáveis `NEXT_PUBLIC_FIREBASE_*`; uma substituição parcial é recusada para não misturar projetos. O SDK inicializa apenas Authentication. Não foram inicializados Analytics ou Cloud Storage, nem ativada faturação.

A configuração pública respondeu com HTTP 200 no serviço Firebase. Os domínios autorizados incluem `localhost`, `arcambe-geoanalytics.firebaseapp.com` e `arcambe-geoanalytics.web.app`. Para teste local de Google, usar `http://localhost:3000/auth/login`; `127.0.0.1` é um domínio diferente. Quando existir um endereço de alojamento, adicioná-lo em Authentication → Settings → Authorized domains.

O formulário permite e-mail/senha e Google. A entrada de utilizadores reais na plataforma inteira ainda precisa de teste: o servidor mantém verificação de revogação e necessita de credenciais administrativas protegidas no alojamento. Não enviar essas credenciais no chat nem colocá-las no GitHub. Nesta etapa foi verificada apenas a configuração pública, sem criar contas nem enviar e-mails.

Referência: [configuração e chaves públicas Firebase](https://firebase.google.com/docs/projects/api-keys).

## Configuração técnica do login

1. Criar um projeto na [consola Firebase](https://console.firebase.google.com/) e anotar o **ID do projeto**. Firebase e Google Cloud usam o mesmo projeto subjacente.
2. Em Authentication → Sign-in method, ativar Email/Password e/ou Google, conforme o método de entrada pretendido. Em Settings → Authorized domains, acrescentar o domínio final da plataforma.
3. Em Project settings → Your apps, registar uma aplicação Web. Guardar `apiKey`, `authDomain` e `projectId`. Estes são parâmetros públicos da aplicação Web; uma chave privada de conta de serviço nunca deve ir para o frontend ou GitHub.

Nesta fase, o orçamento é zero. Não enviar senhas, chaves privadas nem dados de pagamento. A configuração de um servidor pago não é um passo atual.

## Imagens de satélite e API

A API Python da ARCAMBE já acompanha o projeto. A interface comunica com `/api/v1/...`; o servidor encaminha as chamadas para a API interna. O login Firebase autentica cada utilizador.

- Sentinel-2 fica por defeito. Earth Search Collection 1 permite o acesso aos rasters utilizado nos testes reais. Copernicus Data Space também está disponível para pesquisa; encontrar uma cena não garante que o seu raster esteja acessível sem a configuração específica desse fornecedor.
- Landsat 8/9 Collection 2 Level-2 usa o catálogo público Microsoft Planetary Computer. O servidor obtém automaticamente uma assinatura temporária para ler os rasters; não é necessário introduzir um token na interface.
- Landsat usa 30 m, bandas `SR_B1` a `SR_B7`, calibração do STAC e máscaras `QA_PIXEL`/`QA_RADSAT`. Estão disponíveis 19 índices; NDRE e CI_RE exigem Sentinel-2. A comparação temporal entre sensores é recusada até existir harmonização validada.
- Os dados públicos não eliminam os custos de processamento, armazenamento e tráfego do alojamento.

## Instalação paga futura — adiada

Esta secção é uma referência para a fase comercial e não deve ser executada como parte do teste gratuito. Só avançar depois de o proprietário decidir ativar alojamento pago.

O ficheiro `infra/production/compose.yaml` define uma instalação inicial num único servidor Linux com Docker Compose: HTTPS Caddy, Next.js, FastAPI, worker contínuo e PostgreSQL/PostGIS. Apenas portas 80/443 são públicas; base de dados, API e rasters ficam em rede/volumes privados. O modo é fixado em `production`, com autenticação Firebase real. Esta opção preserva a fila durável já implementada.

O servidor pode ser uma VM Google Compute Engine com disco persistente e conta de serviço anexada. A dimensão e região devem ser escolhidas depois de confirmar orçamento e carga; esta entrega não cria a VM. A conta de serviço precisa de `firebaseauth.users.get` (por exemplo, `roles/firebaseauth.viewer`) para a verificação de sessões revogadas. Usar credenciais automáticas da VM, sem distribuir ficheiros JSON. Não anexar credenciais administrativas gerais.

Depois de disponibilizar servidor, domínio e acesso ao repositório privado:

```bash
# No servidor Linux com Git, Python, Docker e plugin Compose instalados:
git clone https://github.com/manguenefrance-cmyk/GeoAnalise.git
cd GeoAnalise
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
