# ARCAMBE GeoAnalytics

[![Verify](https://github.com/manguenefrance-cmyk/GeoAnalise/actions/workflows/ci.yml/badge.svg)](https://github.com/manguenefrance-cmyk/GeoAnalise/actions/workflows/ci.yml)

Repositório de desenvolvimento: [manguenefrance-cmyk/GeoAnalise](https://github.com/manguenefrance-cmyk/GeoAnalise).

Aplicação WebGIS em Next.js/TypeScript, API FastAPI e processamento Rasterio/NumPy. Implementação iniciada a partir do pacote de especificações v1 de 17 de novembro de 2026. O original está preservado em `ARCAMBE_GeoAnalytics_Codex/`.

**Estado:** versão local 0.3.0 funcional; não é uma versão SaaS certificada para produção. Consulte `MVP_RELEASE_CHECKLIST.md` e `docs/DELIVERY_REPORT.md` para evidências e limitações.

## Testes sem gastos

O orçamento atual é zero. Manter Firebase **Spark**, sem cartão, Cloud Billing ou Blaze. O projeto Firebase será usado para autenticação; a API/worker/PostGIS precisam de um alojamento de teste separado, ainda por adaptar e validar. O laboratório local já funciona. A instalação paga descrita no guia fica adiada para a fase comercial. Ver [passos atuais](docs/COLOCAR_ONLINE.pt.md).

## Abrir no Windows

Já foram instaladas dependências neste computador. A partir desta pasta:

```powershell
.\scripts\start-local.ps1
```

Abra http://127.0.0.1:3000. Clique **Start exploring → Enter local test laboratory**. A autenticação de teste só funciona quando o backend recebe explicitamente `APP_ENV=test` e fica ligada a loopback.

Para instalar novamente, requer Python 3.13 e Node.js 24+:

```powershell
.\scripts\setup-local.ps1
.\scripts\start-local.ps1
```

O script de arranque mantém API, worker e frontend ativos enquanto o terminal estiver aberto. Não execute uma segunda instância nas mesmas portas. Para encerrá-los, use Ctrl+C nesse terminal.

## Percurso de utilização

1. Crie um projeto e desenhe/importa uma área de até 100 km²; alternativamente, **Load synthetic test rasters** cria um laboratório claramente identificado.
2. Em **Satellite explorer**, escolha Sentinel-2 (padrão) ou Landsat 8/9, o fornecedor, as datas e a nebulosidade. Earth Search Collection 1 disponibiliza COGs públicos; o catálogo Copernicus também funciona, mas o acesso direto aos seus recursos autenticados exige um adaptador de credenciais adicional.
3. Escolha uma cena, um dos 21 índices Sentinel-2 (19 compatíveis com Landsat) ou uma transformação. A execução passa pela API e pelo worker persistente.
4. Em **Results**, selecione o trabalho, veja a camada, as estatísticas, o histograma e a proveniência. Clique no mapa para consultar um píxel.
5. Descarregue COG, PNG, PDF em EN/PT ou JSON. As ligações assinadas expiram após 5 minutos.

O idioma inicial é inglês. O seletor EN/PT persiste a preferência. As cenas sintéticas têm identificação explícita; cenas reais não são marcadas como amostras.

## Docker Compose

```sh
docker compose up --build
```

Inclui PostGIS, migrações, API, worker e frontend, com portas limitadas a loopback e volume privado partilhado. **Não executado neste computador: Docker não está instalado.** A configuração Compose destina-se ao laboratório local; a publicação requer configuração e validação de produção.

## Testar

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check services tests scripts db
Set-Location apps\web
npm run typecheck
npm run build
```

Testes externos opcionais, a partir da raiz:

```powershell
.\.venv\Scripts\python.exe scripts\live-smoke.py
.\.venv\Scripts\python.exe scripts\live-pixels.py
```

Os resultados ficam em `docs/evidence/`; os pequenos produtos reais ficam em `data/live-smoke/`. Os testes normais não dependem da rede.

## Configuração

Copie `.env.example` para `.env` apenas se precisar de alterar os valores; não guarde credenciais no Git. O script local define explicitamente o modo de teste. Para Firebase, preencha a configuração pública em `apps/web/.env.local` e injete as credenciais administrativas no servidor por ambiente/Secret Manager.

Em produção, `APP_ENV=production` exige PostgreSQL, `FIREBASE_PROJECT_ID` e uma chave de assinatura aleatória com pelo menos 32 caracteres. Tokens `test:*` e dados sintéticos são recusados. A API verifica tokens Firebase no servidor, incluindo revogação e verificação de email.

Não publique o modo de teste na Internet. Integrações Cloud Run/GCS/Cloud Tasks, ensaios de carga, políticas legais e revisão operacional ainda precisam de conclusão antes de produção.

## Estrutura

```text
apps/web/                 interface bilingue e MapLibre
services/api/             autenticação, recursos, quota e fila persistente
services/processor/       catálogo, calibração, grelhas, cálculos e exportações
contracts/                especificação original e OpenAPI gerado
packages/types/           tipos gerados a partir de OpenAPI
db/migrations/            migrações Alembic / PostGIS
infra/                    imagens, Compose e base Terraform GCP
tests/                    testes numéricos, raster, API e segurança
docs/                     operação, métodos e evidências
```

Consulte `docs/USER_GUIDE.md`, `docs/SCIENTIFIC_LIMITATIONS.md` e `docs/DEPLOYMENT.md`.

## Continuação 0.2.0 — 19 de novembro de 2026

134 testes Python aprovados. A comparação independente no motor QGIS 3.44.8 passou para quatro índices; veja `docs/evidence/qgis-validation.json`. O frontend usa tipos gerados a partir dos modelos de resposta reais da API.

O adaptador privado GCS está implementado e testado offline. Configure `STORAGE_BACKEND=gcs`, `GCS_BUCKET`, ADC e, quando necessário, `GCS_SIGNER_EMAIL`; veja as permissões em `docs/DEPLOYMENT.md`. A ligação real ao GCP e ao Firebase ainda não foi validada.

O limite de tentativas diárias (`DAILY_ATTEMPT_LIMIT=20`) conta também falhas e cancelamentos, embora os créditos sejam devolvidos. Os pedidos de eliminação da conta são registados e podem ser cancelados nas definições; a remoção efetiva exige revisão e execução manual.

Para repetir a comparação QGIS neste computador:

```powershell
.\.venv\Scripts\python.exe scripts/prepare-qgis.py
& 'C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat' scripts/qgis-smoke.py data/qgis-validation/cases.json
```

Para gerar o pacote sem credenciais/dados/dependências: `python scripts/package-source.py`.

## Sentinel/Landsat e primeira publicação — 0.3.0

Sentinel-2 continua como padrão. Landsat 8/9 Collection 2 Level-2 está disponível a 30 m com calibração STAC, assinatura temporária automática e máscaras QA_PIXEL/QA_RADSAT. Os índices red-edge ficam restritos a Sentinel. Não existe harmonização entre sensores.

A marca utiliza o logótipo original ARCAMBE e o nome de produto GeoAnalytics. Consulte [identidade](docs/IDENTIDADE_ARCAMBE.pt.md).

Para preparar a conta Firebase/Google Cloud e o primeiro alojamento HTTPS, siga [Colocar online](docs/COLOCAR_ONLINE.pt.md). Existe uma configuração de produção separada em `infra/production/compose.yaml`. A aplicação continua local até existir alojamento configurado; nenhum serviço pago foi criado.

Validação da versão 0.3.0: 161 testes Python, Ruff, TypeScript e build Next.js aprovados; NDVI Landsat real executado pela interface, API e worker. A configuração de produção passou em `docker compose config`, sem execução de contentores neste computador.

## Publicação no GitHub e contentores — 20 de novembro de 2026

Código publicado neste repositório. Os quatro controlos do [GitHub Actions](https://github.com/manguenefrance-cmyk/GeoAnalise/actions/runs/44691447342) passaram: 161 testes Python, frontend, PostGIS e contentores de produção. A verificação dos contentores confirmou arranque, comunicação Web/API, base de dados disponível e recusa de tokens locais de teste em modo de produção.

A imagem Python inclui `libexpat1` e verifica a importação das dependências raster durante a construção. Evidência: `docs/evidence/github-ci-validation.json`. A aplicação ainda não está alojada num servidor público; faltam projeto Firebase/Google Cloud, domínio e orçamento de alojamento. O login Firebase real e o certificado HTTPS público continuam por validar.

## Firebase Spark integrado

O perfil público da aplicação `arcambe-geoanalytics` está incluído em `apps/web/lib/firebase-public.json`. A interface oferece e-mail/senha e Google, sem inicializar Analytics ou Storage. Variáveis de ambiente podem substituir o perfil; para trocar de projeto, fornecer API key, authDomain e projectId em conjunto. A verificação pública Firebase respondeu com HTTP 200; o login completo e a autorização na API ainda dependem da configuração segura do servidor e do alojamento gratuito. Evidência: `docs/evidence/firebase-public-config.json`.
