# Relatório de entrega — versão local 0.3.0

## Atualização de 19 de novembro de 2026 — 0.3.0

- Mesmo símbolo original ARCAMBE, nome de produto GeoAnalytics, verde principal e ícone do navegador. Ver `IDENTIDADE_ARCAMBE.pt.md`.
- Sentinel-2 por padrão; Landsat 8/9 C2 L2 opcional com catálogo de 19 índices, resolução 30 m, bandas nativas, calibração STAC e QA_PIXEL/QA_RADSAT. O processamento interno reutiliza chaves semânticas do catálogo original; a interface e a proveniência identificam as bandas OLI reais. Não há substituição artificial de bandas red-edge.
- 161 testes Python passaram. Ruff, tipos TypeScript gerados e build Next.js passaram.
- NDVI real Landsat 9, cena LC09_L2SP_167078_20261019_02_T1, Maputo: 304 pixels válidos, 30 m, EPSG:32736, média 0,1715639. Evidência em `evidence/landsat-live-pixels.json`. Este recorte não valida todos os produtos e condições de aquisição.
- Configuração de produção em `infra/production/compose.yaml`: HTTPS, Firebase real e volumes privados. Verificada com Docker Compose 5.8.0; contentores não foram construídos nem executados localmente, pois não existe Docker Engine. O workflow GitHub Actions inclui construção e arranque dos contentores, verificação do proxy Web/API e recusa de tokens locais em produção.
- Código publicado na branch `main` de [manguenefrance-cmyk/GeoAnalise](https://github.com/manguenefrance-cmyk/GeoAnalise), repositório público indicado pelo proprietário. Credenciais e dados de execução locais ficaram excluídos. Os quatro controlos GitHub Actions passaram; evidência em `evidence/github-ci-validation.json`.
- Não existe projeto cloud/Firebase configurado, domínio de produção ou alojamento ativo. Nenhum recurso pago foi criado. Passos concretos em `COLOCAR_ONLINE.pt.md`.

As secções seguintes conservam as evidências da base 0.2.0; as limitações cloud mantêm-se até a instalação ser validada.

## Verificação GitHub — 20 de novembro de 2026

[Execução 44691447342](https://github.com/manguenefrance-cmyk/GeoAnalise/actions/runs/44691447342), código `e160ccd67ffe583f8d5a2edbdc4694ebcd16b135`: Python (161 testes), frontend, PostGIS e contentores passaram. A API, o worker e a interface arrancaram com PostgreSQL/PostGIS em modo `production`. A verificação confirmou proxy Web/API, disponibilidade da base de dados e recusa de autenticação ausente e tokens `test:*`.

O primeiro teste de arranque detetou `libexpat.so.1` em falta. A imagem Python passou a instalar `libexpat1` e a verificar as importações raster durante a construção. O teste passou depois da correção. O certificado HTTPS público e o login Firebase real não foram exercitados com o domínio/projeto do proprietário; a aplicação continua sem alojamento cloud.

## O que foi desenvolvido

Repositório independente, sem alterar os outros projetos da pasta de trabalho. O ZIP original foi preservado e os seus contratos/specs foram copiados para a raiz do novo projeto.

- **Interface:** Next.js/React/TypeScript, página inicial, autenticação configurável, dashboard, projetos, área MapLibre, desenho e importação de AOI, explorador de satélite, 21 índices, quatro transformações, trabalhos/resultados, estatísticas, histograma, proveniência, downloads e definições. EN/PT, grelhas responsivas e alternativa textual ao desenho por rato.
- **API:** FastAPI, validação Pydantic, SQLAlchemy, verificação Firebase no servidor e autenticação de laboratório exclusivamente em modo test. Organizações pessoais, memberships/roles, CRUD, limites, auditoria e autorização em projetos, áreas, análises, trabalhos, píxeis, mosaicos e exportações.
- **Processamento:** Rasterio/NumPy, janelas espaciais limitadas, grelha UTM alinhada, calibração por metadados, máscaras SCL, resolução nativa mais grosseira, 21 fórmulas por AST permitido, razão entre bandas, subtração temporal, PCA determinística e RGB/FCC.
- **Execução:** fila na base de dados, worker independente, estados duráveis, reserva de utilização, idempotência, liquidação única, reembolso, cancelamento e recuperação de leases expiradas.
- **Exportação:** COG Float32 com CRS/máscara, mapa PNG/PDF em EN/PT, JSON, links privados assinados de cinco minutos, consulta de píxeis e mosaicos autorizados com escala de cor global.
- **Entrega técnica:** dependências bloqueadas, scripts Windows, imagens Docker, Compose/PostGIS, Alembic, tipos OpenAPI gerados, GitHub Actions, base Terraform, guias e evidências.

## Validação concluída

134 testes Python aprovados, incluindo os 63 valores fornecidos e testes reais sobre ficheiros raster. Os testes cobrem máscaras, calibração, 10/20/60 m, PCA contra sklearn, COG, importação ZIP segura, dois utilizadores, roles, idempotência, concorrência de quota, cancelamento e indisponibilidade do fornecedor. O teste final registou avisos de depreciação das bibliotecas Starlette/Shapely, sem falhas.

Ruff, TypeScript e compilação otimizada Next.js passaram. A auditoria npm de dependências de produção terminou com zero vulnerabilidades reportadas após corrigir a dependência transitiva gRPC. Não foi feita uma auditoria de segurança abrangente.

O catálogo Copernicus respondeu a uma pesquisa real. O processamento real foi validado com a coleção pública Sentinel-2 Collection 1 do Earth Search: cena de 16/10/2026, recorte de aproximadamente 0,277 km² perto de Maputo, 2.800 píxeis válidos NDVI, resolução 10 m e EPSG:32736. A média calculada foi 0,1359293. O COG foi reaberto e os produtos cartográficos foram gerados. Isto verifica esse recorte específico, não todas as cenas/fornecedores.

As evidências numéricas estão em `docs/evidence/`. Os produtos reais estão em `data/live-smoke/`; os dados sintéticos do laboratório são sempre identificados como tal.

## Execução

Na raiz do projeto, execute `scripts/start-local.ps1` e abra http://127.0.0.1:3000. O guia principal é `README.md`. Para reinstalar dependências, execute `scripts/setup-local.ps1`.

O comando `docker compose up --build` está preparado, mas não foi executado porque o Docker não está instalado neste computador.

## Pendências explícitas

Esta é uma versão funcional para desenvolvimento local. A publicação de produção depende da configuração do alojamento, de Firebase real, domínio/HTTPS e operação/cópias de segurança. A integração PostGIS/Docker passou no GitHub Actions. A alternativa Cloud Run/GCS continua a exigir validação real do adaptador GCS e implementação do despacho Cloud Tasks/Cloud Run Jobs. O frontend não foi publicado isoladamente como se fosse uma plataforma completa.

Ainda não estão concluídos: ingestão automática de arquivos SAFE, OAuth/S3 autenticado Copernicus, exportação individual de cada componente PCA, workflow completo de eliminação de conta/termos legais, limitação distribuída de pedidos/circuit breaker, testes de carga/restauro, auditoria formal de acessibilidade e testes browser E2E automáticos no CI. Os modelos de resposta JSON OpenAPI já foram definidos e os tipos TypeScript do frontend são gerados a partir deles. Faturação permanece desativada.

Foi utilizado o motor QGIS 3.44.8 sem interface gráfica para verificar independentemente NDVI, NDWI_MCF, NDBI e EVI. Os quatro passaram com erro máximo 2,3842e-7, e os COGs mantiveram grelha, CRS e máscaras. O NDBI exigiu alinhamento explícito das bandas 10/20 m com GDAL do QGIS antes da álgebra; a tolerância não foi alterada. A revisão manual na interface gráfica do QGIS permanece pendente. O livro PDF referido nas especificações não estava dentro do ZIP; não foi lido nem redistribuído.

## Continuação de 19 de novembro de 2026

- Adaptador GCS privado ligado ao worker, aos mosaicos/píxeis, às pré-visualizações e às descargas. Testes verificam política privada, gravação imutável, idempotência de publicação, assinaturas curtas e erros sem credenciais. Não houve ligação real ao GCP.
- Renovação de tokens Firebase antes dos pedidos, observação da sessão e saída do SDK. Ainda sem ensaio contra um projeto Firebase configurado.
- Registo de pedidos de eliminação da conta, consulta e cancelamento privados. A eliminação efetiva exige execução manual; a interface comunica esse estado.
- Métricas do dashboard calculadas no servidor sem depender da primeira página. Estados de carregamento deixam de mostrar zeros como resultado definitivo.
- Limite diário de 20 tentativas por defeito, incluindo falhas e cancelamentos, além da quota de créditos. Publicações sem referência são removidas após cancelamento/falha de upload.
- Tipografia e controlos mais legíveis e modelos de resposta JSON utilizados pelos tipos gerados do frontend.
- Descarregamento real de COG pela interface confirmado por checksum, com EPSG:32736, grelha 51×56 e estrutura COG.

O pacote de código encontra-se em `dist-delivery/`, com SHA-256. Exclui dependências instaladas, credenciais e dados de execução.

A verificação visual final cobriu 1440×1000 e 360×800, sem transbordo horizontal, incluindo abertura do inspetor em telemóvel e navegação EN/PT. Um novo trabalho NDWI de teste concluiu na versão 0.2.0. As imagens e o relatório de browser estão em `docs/evidence/`. A compilação final e a auditoria npm passaram em 19/11/2026.
