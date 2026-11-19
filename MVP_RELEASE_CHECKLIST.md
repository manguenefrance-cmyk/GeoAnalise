# Release evidence — 19 November 2026

Status: **working local implementation; production deployment not validated**.

## Verified

- [x] 134 automated Python tests pass, including 63 supplied numerical vectors for all 21 indices. Evidence: `docs/evidence/pytest-results.xml`.
- [x] Every index runs over real GeoTIFF fixtures and survives COG reopening with CRS/masks/Float32 preserved.
- [x] Calibration pre/post baseline offsets, normalized inputs, negative reflectance and double-scaling refusal.
- [x] Native 10/20/60 m grids, complete/partial cloud masks, invalid geometry, safe ZIP import, approved asset resolution.
- [x] Ratio, temporal difference, PCA (independent sklearn comparison), RGB/FCC.
- [x] Persistent queue, idempotency, cancellation, refunds, concurrent quota contention, tenant/role isolation, signed capability expiry.
- [x] Python Ruff checks and frontend TypeScript check pass.
- [x] Next.js production build passes.
- [x] `npm audit --omit=dev --audit-level=high`: zero reported vulnerabilities after updating the vulnerable transitive gRPC dependency.
- [x] SQLite Alembic migration smoke passes.
- [x] Real Copernicus collection discovery/search succeeds. Evidence: `docs/evidence/live-stac.json`.
- [x] Real Earth Search Collection 1 NDVI raster processing succeeds for scene `S2C_T36JVS_20261016T075055_L2A`, acquired 16 October 2026. 2,800 valid pixels, EPSG:32736, 10 m, 51×56 grid; COG verified. Evidence: `docs/evidence/live-pixels.json`.
- [x] Actual PNG map inspected after fixing map scaling and font rendering. Local products: `data/live-smoke/`.
- [x] Browser: test login, sample seeding, index execution and statistics verified. Real-scene search and execution initiated from the interface and persisted in the database.

## Remaining release gates

- [ ] Docker/PostGIS/container integration executed: Docker is absent on this host; CI configuration is provided but has not run remotely.
- [ ] Real Firebase registration, reset, verification and revocation lifecycle validated with configured credentials.
- [x] Private GCS adapter, immutable uploads, bounded signing and failure/cancellation cleanup implemented and tested offline.
- [ ] Live GCS validation and Cloud Tasks/Cloud Run Jobs dispatch. Terraform remains a provisioning reference.
- [ ] Copernicus authenticated pixel assets integrated; current public pixel path is Earth Search Collection 1.
- [x] Independent headless QGIS 3.44.8 algebra/grid/CRS/mask comparison for NDVI, NDWI_MCF, NDBI and EVI; maximum error 2.3842e-7 (tolerance 1e-5). Evidence: `docs/evidence/qgis-validation.json`.
- [ ] Desktop GUI review, formal accessibility audit, workload/backup/restore tests and security scanning.
- [ ] Complete account-erasure/legal workflows, distributed rate limiting and production operational approval.
- [x] Typed JSON response models, generated frontend types, complete dashboard counts and loading states.
- [x] Persisted, private, idempotent account-deletion request and cancellation endpoints; actual erasure remains a manual fulfillment task.
- [x] Configurable daily attempt ceiling and tests for refund/cancellation abuse.
- [ ] Automated browser E2E CI.

No live cloud deployment, paid billing or production readiness is claimed. QGIS evidence is from the independent headless engine, not a manual desktop review.

## Browser evidence — 19 November 2026

- [x] EN/PT navigation and new NDWI fixture job complete in the running 0.2.0 interface.
- [x] Real NDVI result displays with its persisted statistics; desktop 1440×1000 has no horizontal overflow.
- [x] Mobile 360×800 has no horizontal overflow; map/tools adapt and the analysis inspector can be opened.
- [x] COG downloaded through the browser; SHA-256 matches the authenticated artifact record and Rasterio confirms COG/EPSG:32736/51×56.
- [x] Evidence: `docs/evidence/browser-validation.json`, `browser-download.json`, `workspace-desktop.jpg`, `workspace-mobile.jpg`.

These are manual checks through the browser automation interface; no claim of a complete automated browser CI suite is made.
