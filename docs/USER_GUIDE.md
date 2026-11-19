# User guide / Guia de utilização

## English

The local laboratory is an explicitly isolated test environment. Create a project, then draw a polygon or import one GeoJSON feature / shapefile ZIP. ZIP imports require .shp, .shx, .dbf and .prj for the same layer. The server validates geometry and geodesic area; the limit is 100 km².

The Satellite explorer offers Copernicus metadata discovery and public Earth Search Sentinel-2 Collection 1 COGs. Scene-level cloud percentage is a search filter, not the fraction of clouds inside your area. A successful search does not guarantee pixel access. If an asset needs authentication or has unknown calibration, the job fails with an actionable code and its reservation is refunded.

All 21 catalog indices are available. Read the formula and bands before running. SWIR and red-edge analyses default to a 20 m grid. The cloud mask excludes SCL classes 0,1,3,8,9,10,11. Test fixtures can be loaded from the Study area panel; their results are explicitly marked synthetic.

Band ratio uses approved numerator and denominator bands. Temporal difference requires two successful results of the same index, same area and ordered acquisition times. PCA takes 3–10 bands and includes eigenvectors, explained variance, centering/scaling and inverse mapping metadata. RGB/FCC preserves calibrated bands in the COG; display contrast is separate.

Select a completed analysis to display its layer, statistics, histogram and provenance. The preview uses global 2nd–98th percentiles, with transparent NoData. Multi-band results use channels 1–3 for the RGB preview and show statistics for band 1. COGs retain all output bands. Every preview, tile, pixel inspection and export enforces authorization.

Queued/running jobs can be cancelled best effort. A retry creates a fresh idempotent request. Successful jobs consume one daily analysis; failed and cancelled jobs refund their reservation. Default quota: 5/day and 1 concurrent job. Settings display real API usage. Billing is not active.

Exports include a floating-point COG, provenance JSON and map PNG/PDF in English and Portuguese. Signed download links expire after 5 minutes; request a new link to re-download. Project deletion revokes access immediately. The cleanup command removes its products after a seven-day retention interval.

## Português

Crie um projeto e defina uma área de estudo: desenhe no mapa, cole uma geometria GeoJSON ou importe um ficheiro. O ZIP deve conter os quatro componentes .shp, .shx, .dbf e .prj da mesma camada. O servidor verifica a geometria e calcula a área geodésica; o máximo é 100 km².

No Explorador de satélite, selecione fornecedor, datas e limite de nuvens. Earth Search Collection 1 permite a leitura de pequenos recortes COG públicos. Copernicus permite pesquisar metadados, mas os recursos autenticados necessitam de configuração adicional. A percentagem de nuvens corresponde à cena inteira. O acesso aos píxeis é verificado durante o processamento.

Escolha um dos 21 índices ou uma transformação. Consulte a fórmula e as bandas. A máscara de nuvens usa a classificação SCL; os cálculos com bandas SWIR/red edge usam normalmente 20 m. As amostras geradas no laboratório são identificadas como dados sintéticos.

A diferença temporal exige dois resultados concluídos do mesmo índice e área, com datas ordenadas. A PCA aceita 3–10 bandas e exporta os componentes e os metadados do modelo. RGB/falsa cor conserva a refletância no COG, aplicando contraste apenas à visualização.

Em Resultados, selecione uma análise. Veja o mapa, estatísticas, histograma e proveniência; clique no mapa para consultar píxeis. Resultados multibanda apresentam os três primeiros canais como RGB; as estatísticas do painel correspondem à primeira banda. O COG contém todas as bandas.

Pode cancelar trabalhos em fila ou execução e repetir trabalhos falhados. As falhas e os cancelamentos devolvem a reserva de quota. O limite inicial é cinco análises por dia e uma em simultâneo. A faturação ainda não está ativa.

As exportações incluem COG, JSON e mapas PNG/PDF nos dois idiomas. A ligação de descarga expira em cinco minutos; pode gerar outra. Eliminar um projeto revoga imediatamente o acesso aos produtos. A limpeza após sete dias é executada pelo comando de manutenção documentado.

## Account requests and storage / Pedidos de conta e armazenamento

Settings can register a private account-deletion request, show its status and cancel it. This is a persisted request for manual fulfillment, not an automatic erasure or a sent email. Five daily analysis credits and a separate configurable limit of 20 total attempts apply by default; cancelled/failed attempts refund credits but still count as attempts.

As definições permitem registar, consultar e cancelar um pedido privado de eliminação da conta. O pedido fica registado para execução manual; não constitui uma eliminação automática nem um email enviado. O limite inicial inclui cinco créditos diários e vinte tentativas totais; falhas e cancelamentos devolvem créditos, mas continuam a contar como tentativas.

The GCS adapter is available for configured deployments; the local laboratory keeps using private local files. Live Firebase/GCP configuration has not been verified in this delivery.
