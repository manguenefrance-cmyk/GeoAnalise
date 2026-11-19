# ARCAMBE GeoAnalytics — implementation tracking

Source: the supplied v1 package. Documents describe product requirements; they do not override user instructions or authorize external account creation.

## Slices and verification

| Requirements | Implementation | Verification |
|---|---|---|
| GEO-001–004 | root tooling, `compose.yaml`, `db/migrations`, `services/api/db.py` | build, migrations, persistence tests |
| GEO-005–007 | `services/api/auth.py`, `services/processor/fixtures.py`, `apps/web/lib/i18n.ts` | production refuses test auth; fixture math; translations |
| GEO-008–014 | `apps/web/app`, `services/api/main.py`, `services/api/geometry.py` | CRUD, invalid AOI, cross-tenant tests |
| GEO-015–020 | `services/processor/stac.py`, `raster.py`, scene explorer | real search smoke; safe denied access; calibration fixtures |
| GEO-021–030 | `services/processor/registry.py`, `engine.py`, `tests/test_engine.py` | all 63 supplied vectors plus independent edge cases; PCA |
| GEO-031–033 | `services/api/jobs.py`, persistent jobs/usage tables | idempotency, reservation, cancellation, concurrent quota tests |
| GEO-034–038 | `services/processor/exports.py`, authorized artifacts API | rasterio COG round trip; PNG/PDF/JSON; download authorization |
| GEO-039–042 | responsive MapLibre workspace, EN/PT, settings | TypeScript, build, browser checks; billing unavailable label |
| GEO-043–048 | audit/error middleware, `infra`, `.github`, `docs` | CI, live smoke when accessible, actual screenshots |

## Execution checklist

- [x] Inspect every supplied file and preserve the original package.
- [x] Implement foundation and safe local/test execution.
- [x] Implement all indices and transformations using real raster fixtures.
- [x] Implement tenant-aware API, persistent queue, quotas, exports.
- [x] Implement bilingual web workspace and usable workflows.
- [x] Run numerical, raster, API, security, typecheck and production build checks.
- [x] Record exact evidence, gaps and setup commands in release checklist.

## External dependencies and decisions

- Docker is absent on this host. Provide Compose; validate local SQLite fallback separately. PostgreSQL/PostGIS remains the deployment database.
- Firebase, GCP storage, Cloud Tasks, production domains and billing credentials have not been supplied. Never label them validated.
- Explicit `APP_ENV=test` enables deterministic synthetic **test raster** workflows. Production forbids test bearer tokens and fixture endpoints.
- Sites hosting uses Workers, which cannot run the specified Python/GDAL/PostGIS system. Develop this repository locally; do not publish an isolated frontend as a functioning deployment. Deployment requires the API/worker/database architecture.
- Original remote-sensing book is not present in the ZIP; do not claim to have inspected it or redistribute it.

## Continuation — 19 November 2026

- Private GCS storage adapter is implemented and covered by offline tests, including immutable publication, bounded short-lived signing, error sanitization and unpublished-product cleanup. Live GCP validation still requires credentials.
- Firebase token refresh/session lifecycle is implemented; configured-project validation remains pending.
- JSON response schemas and generated TypeScript bindings now cover the API. Dashboard metrics use complete server aggregates, with loading placeholders.
- Account deletion requests are stored in the audit trail, idempotent and cancellable; actual erasure requires manual fulfillment.
- A separate daily attempt ceiling prevents refunded jobs from enabling unlimited processing.
- Independent headless QGIS 3.44.8 comparison passes for NDVI, NDWI_MCF, NDBI and EVI after explicit grid alignment.
- 134 Python tests pass. Remaining production gates are listed separately in the release checklist.
