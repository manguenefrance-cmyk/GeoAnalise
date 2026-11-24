# API de teste sem custos — Render e Supabase

Preparado em 24 de novembro de 2026. A interface está em https://geo-analise.vercel.app. O projeto Supabase Free **ARCAMBE GeoAnalytics** (`bmoabalkqotxrswcraby`) já foi criado e está saudável. O plano Render `exs-dc2q9hm7bikc739du5ng` está preparado, ainda sem aprovação/implantação. **A API ainda não foi publicada, nem existe validação real da integração completa destes fornecedores**. Não criar recursos pagos nem introduzir cartão para seguir este percurso.

## Componentes

- Vercel Hobby: interface Next.js, já publicada.
- Firebase Spark: identidade, e-mail/senha e Google; continua a ser o único sistema de login da aplicação.
- Render Free: uma API Python com um consumidor da fila no mesmo processo. A fila e os estados continuam persistidos no PostgreSQL.
- Supabase Free: PostgreSQL/PostGIS e bucket privado para os resultados. Não inicializar Supabase Auth no frontend nem disponibilizar as credenciais do servidor na Vercel.

As condições consultadas incluem 500 MB de base de dados e 1 GB de ficheiros no Supabase Free, pausa após uma semana de inatividade e um máximo de 50 MB por ficheiro. O Render Free suspende o serviço após 15 minutos sem tráfego e pode demorar cerca de um minuto a retomar; o disco local é temporário. Não se promete disponibilidade permanente nem desempenho comercial neste perfil.

Referências oficiais: [Render Free](https://render.com/docs/free), [Supabase preços](https://supabase.com/pricing), [limites dos ficheiros](https://supabase.com/docs/guides/storage/uploads/file-limits).

## 1. Preparar o Supabase Free

O [projeto gratuito](https://supabase.com/dashboard/project/bmoabalkqotxrswcraby) já está criado na região `eu-central-1`. A organização confirmou plano Free e custo indicado de 0 por mês para o projeto. As 11 tabelas da aplicação já foram criadas no schema privado `arcambe`, com revisão Alembic `0003`; o arranque da API verifica/aplica apenas migrações pendentes. Guardar a senha da base de dados num gestor de senhas; defini-la/redefini-la pela consola se necessário. Não a enviar no chat.

1. Em Storage, criar um bucket **privado**, com o ID `arcambe-artifacts`. Não ativar acesso público nem criar políticas públicas de leitura/escrita.
2. Obter a ligação PostgreSQL pelo **Session pooler**, porta 5432. Esta opção evita a exigência de IPv6 da ligação direta; não usar o pooler de transações na porta 6543 neste perfil.
3. Usar o formato `postgresql+psycopg://...` e acrescentar `sslmode=require` à ligação. Codificar caracteres especiais da senha na URL. A ligação vai apenas para `DATABASE_URL` no servidor Render.
4. O endereço é `https://bmoabalkqotxrswcraby.supabase.co` e já está no Blueprint. Criar uma chave administrativa **secret** (`sb_secret_...`) para o backend; o adaptador envia-a apenas em `apikey`, sem a confundir com um JWT de utilizador. Também aceita a chave legada JWT `service_role`, com Bearer. Não usar `anon`/publishable. Guardar apenas no Render, nunca no GitHub, interface, captura ou chat.

As migrações usam uma área privada `arcambe`, revogam privilégios de `PUBLIC`, `anon` e `authenticated` e ativam RLS nas tabelas. Não acrescentar esse schema aos schemas expostos pela Data API. A ligação do backend deve ser o proprietário dessas tabelas: o servidor mantém os controlos Firebase e de organização. A API REST pública do Supabase não é utilizada para ler as tabelas da aplicação.

A validação real confirmou o índice espacial, a geração de MultiPolygon/SRID 4326 pelo trigger e o bloqueio dos papéis de navegador. As linhas temporárias do teste foram revertidas: continuam zero utilizadores, projetos e áreas da aplicação. A função tem um `search_path` fixo. O advisor conserva 11 mensagens **informativas** de RLS sem políticas: é o comportamento intencional de negação por defeito neste schema privado, usado apenas pelo backend proprietário. Não criar políticas amplas para silenciar esses avisos. Referência: [RLS sem políticas](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).

Referências: [ligação PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres), [PostGIS](https://supabase.com/docs/guides/database/extensions/postgis), [buckets privados](https://supabase.com/docs/guides/storage/buckets/fundamentals).

## 2. Preparar o Firebase administrativo

O backend verifica assinatura, e-mail confirmado e revogação do token. Esta verificação não será desativada para fazer o teste funcionar.

Preparar uma conta de serviço dedicada ao projeto `arcambe-geoanalytics`, com permissão `firebaseauth.users.get` (por exemplo `roles/firebaseauth.viewer`). Se for necessário um ficheiro JSON para este alojamento externo, criá-lo e colocá-lo **diretamente no armazenamento de segredos do Render**, com nome `firebase-admin.json`. Não usar uma chave administrativa geral quando é possível limitar a função. O caminho esperado é `/etc/secrets/firebase-admin.json`. Não enviar o ficheiro no chat, colocá-lo no repositório ou defini-lo como variável `NEXT_PUBLIC_*`.

Em Firebase Authentication → Settings → Authorized domains, adicionar **`geo-analise.vercel.app`**, sem `https://` e sem caminho. Isto é necessário para o Google na nova origem. Os domínios autorizados ainda precisam de confirmação na consola do proprietário.

## 3. Criar a API Render Free

O `render.yaml` na raiz define **um único Web Service Free**, sem disco persistente, worker pago ou base de dados Render. O projeto usa o Dockerfile já testado em CI, que inclui as dependências Rasterio/GDAL.

Importar o repositório original `manguenefrance-cmyk/GeoAnalise` como Blueprint. Conferir que o plano escolhido é **Free** antes de criar. Preencher os campos privados na própria consola:

| Campo | Origem |
|---|---|
| `DATABASE_URL` | Session pooler Supabase, `postgresql+psycopg`, `sslmode=require` |
| `SUPABASE_URL` | Já configurado: `https://bmoabalkqotxrswcraby.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Chave secret (ou JWT legado `service_role`), só no servidor |
| Ficheiro secreto `firebase-admin.json` | Credencial Firebase com permissões mínimas |

O Blueprint gera `DOWNLOAD_SECRET`. Mantém `APP_ENV=production`, `DATABASE_SCHEMA=arcambe`, `WORKER_EMBEDDED=true` e armazenamento Supabase. O limite é de 10 km² por AOI, 250 mil pixels, 50 MB por artefacto, três créditos diários e um trabalho por organização em simultâneo. O consumidor único processa um trabalho de cada vez. Estes valores são conservadores para teste; **o consumo real de memória no Render Free ainda deve ser medido**.

No arranque: validar configuração e credenciais, verificar que o bucket é privado, executar migrações e iniciar a API. Só depois o `/readyz` deve responder. Se faltar um segredo ou o bucket for público, corrigir a configuração em vez de ativar modo de teste ou tornar dados públicos.

Os produtos recebem nomes com hash e organização, são enviados sem sobrescrever objetos e os ficheiros temporários são removidos após a publicação. Downloads autorizados continuam limitados a cinco minutos. Se o processo for terminado durante uma análise, a fila conserva o registo: a lease expira em 20 minutos e o trabalho é marcado como falhado com devolução do crédito; não se declara sucesso nem se repete automaticamente um resultado incompleto.

## 4. Ligar a interface e verificar

Depois de existir um endereço real da API, confirmar `/healthz` e `/readyz`. Na Vercel, definir `API_URL` com o endereço HTTPS da API **sem `/api` e sem barra final** e fazer novo deploy: o encaminhamento Next.js é compilado durante o build.

Verificar com o proprietário: registo, confirmação do e-mail, login Google, recuperação de senha, criar projeto/AOI, pesquisa e análise Sentinel, uma análise Landsat, preview e exportação. Confirmar isolamento entre duas contas e que os resultados persistem após reiniciar a API. Não usar tokens `test:*` no endereço público. Enquanto estes passos não passarem, não apresentar a plataforma como operacional de ponta a ponta.

Planos pagos, checkout, assinaturas e webhooks continuam nos critérios de implementação. Este perfil de alojamento não os substitui nem ativa cobranças reais.
