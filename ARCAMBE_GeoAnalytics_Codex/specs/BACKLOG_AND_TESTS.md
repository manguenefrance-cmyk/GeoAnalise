# DELIVERY BACKLOG AND ACCEPTANCE

## Phases and dependencies (all P0 except noted)
**S1 Engineering foundation:** GEO-001 monorepo; GEO-002 Docker Compose; GEO-003 precommit lint+typecheck+CI; GEO-004 migrations PostGIS; GEO-005 Firebase verification; GEO-006 local fixture factory; GEO-007 i18n EN/PT.
**S2 Product & AOI:** GEO-008 Landing/auth/dashboard; GEO-009 project CRUD; GEO-010 map controls; GEO-011 draw/edit AOI GeoJSON; GEO-012 ZIP shapefile import+secure extract; GEO-013 geodesic area and CRS; GEO-014 tenant authorization tests.
**S3 Satellite data:** GEO-015 STAC search; GEO-016 collection and asset resolver; GEO-017 provider auth and retries; GEO-018 source normalization/baseline offsets; GEO-019 SCL masks/resampling/alignment; GEO-020 scene UI and no-scenes errors.
**S4 Scientific index registry:** GEO-021 `spectral_indices.yaml` loader with schema validation; GEO-022 universal safe formula dispatcher; GEO-023 all catalog indices; GEO-024 protected division/sqrt and nodata; GEO-025 band ratio; GEO-026 temporal difference; GEO-027 PCA; GEO-028 composite presets; GEO-029 catalog and method info UI; GEO-030 quantitative reference tests.
**S5 Real execution:** GEO-031 durable queue and worker; GEO-032 job state/idempotency/cancellation; GEO-033 quotas and atomic settlement; GEO-034 COG exports; GEO-035 authorized map tiles; GEO-036 stats/histogram/provenance; GEO-037 maps PNG/PDF; GEO-038 downloads/retention.
**S6 Release:** GEO-039 responsive accessible UI; GEO-040 full translation; GEO-041 E2E journeys; GEO-042 billing feature flag (no charge); GEO-043 telemetry/error alerting; GEO-044 cloud reference deploy; GEO-045 runbooks; GEO-046 security tests; GEO-047 external-data live smoke test when credentials available; GEO-048 demo video/screenshots from actual app.

## Definition of Ready per ticket
Purpose and acceptance, data source, real errors, auth and quota effects, tests, dependencies, docs updated.

## Acceptance scenarios
AT-001 register/sign in/account verify/reset/logout; AT-002 project CRUD personal tenant; AT-003 AOI draw/save/refresh/ZIP import; AT-004 STAC search scene coverage and dates; AT-005 valid NDVI outputs; AT-006 NDWI_MCF distinct NDMI; AT-007 NDBI 20m; AT-008 **every index in YAML** unit + fixture test; AT-009 band ratio values including denom zero; AT-010 date2 - date1 aligned result; AT-011 PCA explained variance and reproducibility; AT-012 composite visualization; AT-013 mask nodata/partial cloud; AT-014 metadata reflectance baseline correction; AT-015 20m/10m native grid and no false resolution; AT-016 cloud fraction warning; AT-017 deterministic failure when provider denies access; AT-018 job retry and duplicate idempotency; AT-019 quota bypass concurrency refused; AT-020 COG round trip rasterio/QGIS; AT-021 PDF with attribution, correct scale, CRS and band metadata; AT-022 signed URL expires; AT-023 tenant B resource 403/404 all endpoints including tile; AT-024 full translated UI; AT-025 mobile controls interactive, not inert; AT-026 live source smoke test; AT-027 delete and retention; AT-028 no fake demo products in production; AT-029 audit all destructive operations.

## Performance and release quality targets
On controlled source fixture, 25 km² index in <=180 sec on documented reference resources (performance target, not guarantee); p95 normal API <=800ms under declared load; successful deterministic processing >=95% on supported accessible scenes; all numeric formula tests tolerance <=1e-5, use more conservative tolerance for reprojection; 0 critical security vulnerabilities, no unresolved cross-tenant leak; error recovery demonstrated.

## Test strategy
`pytest` pure math; test rasterio fixtures with 10/20m alignment and non-square AOI; ref vectors in `tests/reference_vectors.json`; API test with FastAPI test client/temporary PostGIS and auth mocks test-only; Playwright E2E with local fixtures; CI on PR; manual QGIS open GeoTIFF, MapLibre coordinate inspection; no live dependencies in standard CI; separate gated live integration workflow.

## Reporting format for Codex
After each phase show: completed ticket IDs, changed files, verification commands/output, scientific edge cases covered, remaining TODO, any unverified service. Include `MVP_RELEASE_CHECKLIST.md` evidence links.
