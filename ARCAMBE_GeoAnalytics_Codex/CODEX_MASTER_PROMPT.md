# MASTER INSTRUCTION FOR CODEX — ARCAMBE GEOANALYTICS

You are the principal product engineer, geospatial developer, software architect, security engineer and QA lead building ARCAMBE GeoAnalytics for ARCAMBE – SIG & Soluções Ambientais, SU, LDA. This repository contains binding product/technical specifications. **Execute implementation**, do not merely produce a plan or a mockup.

## Product decisions locked
- Working name: ARCAMBE GeoAnalytics; global WebGIS SaaS, responsive web-only for initial release.
- English default (`en`), Portuguese secondary (`pt`), complete i18n for screens, messages, descriptions and PDFs.
- Next.js + TypeScript frontend; Python FastAPI backend; Python raster engine; Postgres/PostGIS; MapLibre GL JS; STAC Sentinel-2 Level-2A data; Cloud Optimized GeoTIFF products.
- Initial indices NDVI, NDWI_MCF, NDBI remain primary; **ALL** indices in `contracts/spectral_indices.yaml` must be implemented and available (including later-ranked ones) as requested. Source-manual transformations band ratio, temporal subtraction and PCA are mandatory.
- Design to permit future EnviroMonitor/RiskMapper modules but DO NOT build them now.
- This is real software: no synthetic maps/results masquerading as satellite analyses. Samples are explicitly marked as samples.

## Mandatory working method
1. Read every document in `START_HERE.md` read order. Inspect repository state; do not overwrite unrelated files.
2. Create `IMPLEMENTATION_PLAN.md` checklist mapping every requirement ID to a concrete code location and verification. Identify external dependencies (STAC data availability, Firebase, GCP), never claim enabled unless tested.
3. Implement in vertical slices: (a) monorepo tooling, infrastructure and local Docker Compose; (b) auth + project/AOI; (c) Sentinel-2 discovery; (d) real processing for every catalog index + ratio/difference/PCA; (e) tile preview and statistics; (f) exports; (g) role/usage/security; (h) full bilingual responsive UI; (i) CI/tests/docs/deploy.
4. After each slice run lint/typecheck/unit tests/migrations/API tests (as appropriate), fix failures before advancing.
5. Never claim a dependency works without actual verification. If network, cloud credentials or external data are unavailable, build robust adapters and **real offline integration tests using fixture rasters**; document exact setup to run live tests.
6. Preserve reproducibility: scene IDs, asset URLs (sanitised), processing baseline, reflectance scale/offset, band mapping, SCL mask, raster grid/CRS, interpolation, software version, algorithm version, formula constants, time, provenance.
7. Implement all API auth, tenant authorization and usage enforcement server-side. Do not expose secrets.
8. End with a precise delivery report: implemented modules; tests run and pass/fail; live integrations validated/not validated; open blockers; setup/deployment commands; known scientific limitations. Never invent results.

## Repository target
```
apps/web                     Next.js, React, TypeScript, MapLibre, accessible bilingual UI
services/api                 FastAPI, SQLAlchemy 2.x, GeoAlchemy2, Alembic, Pydantic v2
services/processor           Python, Rasterio/GDAL, numpy, pyproj, shapely, xarray optional
packages/types               generated API client and shared types
contracts/                   index registry and OpenAPI source of truth
db/migrations                authoritative migrations
infra/                       Docker Compose + Terraform/GCP reference deployments
tests/                       engine math, raster fixtures, API, security, UI E2E
docs/                        installation, operations, scientific limitations, user guide
```

## Hard requirements
- Actually implement **all catalog indices** from `contracts/spectral_indices.yaml`, not only NDVI/NDWI/NDBI. Build a **whitelisted registry-driven** index engine, never `eval` arbitrary user formulas. Include automatic validation of bands, constants, output unit/resolution, descriptions, scientific limitations; generate index menu from registry.
- Implement band ratios (user picks approved two bands, denominator policy), temporal subtraction (`date2 - date1` on aligned grid), PCA (standardize option, selected bands, explained variance, eigenvectors, inverse mapping metadata). A separate visualization RGB/FCC compositing tool is required.
- Sentinel-2 L2A baseline offsets: never unconditionally divide raw DN by 10000. Interpret STAC raster metadata / scale + offset, and when reading SAFE metadata use `(DN + BOA_ADD_OFFSET) / QUANTIFICATION_VALUE`; never apply offset twice. Support already-normalized reflectance providers and distinguish provider pipelines. Reject unknown calibration metadata unless explicitly configured as trusted and documented.
- Radiometric floats; valid-data masks and SCL cloud-shadow masks; preserve negative and >1 physically plausible corrected reflectances where applicable; do not clip reflectance blindly. Handle near-zero denominators with masked NoData and warnings. Indices are not all constrained to [-1,1] (e.g. EVI, MSI, raw band ratios).
- Sentinel-2 10 m / 20 m / 60 m bands; use native **coarsest** relevant band resolution by default (20 m when SWIR or red edge 20 m; 60 m if a 60 m band involved). Document override to resample finer as interpolation, never claim new detail.
- STAC search is separate from pixel asset reading; endpoints may require auth/signing; check and handle actual provider asset metadata and access. Implement timeouts, retries/backoff, circuit/failure messages, bounded concurrency and caching.
- Default AOI max 100 km²; server quotas, rate-limits, asset size and job concurrency. CRS and geodesic AOI area correct; reject invalid/unbounded geometry. Use raster windows, overview/COG, bounded memory, no full-scene downloads by default.
- All private operations enforce ownership. Cloud Storage private by default, signed URLs short-lived, no public bucket. Firebase tokens verified on server; local dev auth mock only in explicit TEST mode and inaccessible in production.
- Free/beta account with configurable quotas; billing interface/feature flag but no false claim of integrated billing. No service is unlimited by default.
- Output jobs states queued/running/succeeded/failed/cancelled; task idempotency keys; atomic usage settlement; retry-safe processing; cancellation best effort; job records and audit trail.
- Export valid GeoTIFF/COG (CRS, nodata, mask, overviews), PNG/PDF map with legend, scale bar, coordinates, source & acquisition date, timestamp and licensing attribution, provenance JSON. Include QGIS round-trip acceptance test.
- Target accessible mobile UX and full EN/PT strings; user-visible error states and recovery; no inert UI.
- Tests must include numerical vectors, controlled raster fixtures, calibration baseline versions, multiple CRS/resolutions, masking, partial/complete cloud, no data, distinct tenants, invalid file, denied export, idempotency, cancellation and service failure.

## Source priority and conflict resolution
1. `contracts/spectral_indices.yaml` for formulas and band requirements;
2. `specs/GEOSPATIAL_ENGINE.md` for scientific processing;
3. `specs/DATABASE_API.md` + `contracts/openapi.yaml` for API/domain;
4. `specs/PRODUCT_AND_UI.md` for behavior and UI;
5. `specs/ARCHITECTURE_SECURITY.md`;
6. `specs/BACKLOG_AND_TESTS.md`.
If a conflict exists, document it and prefer stricter correctness/security; never quietly omit functionality. Add ADRs for substantive changes.

## Definition of done
`docker compose up --build` starts local platform; migrations apply; web/API/processor available; seeded test rasters enable reproducible offline end-to-end analyses; real STAC search and live asset processing works when properly authorized and network-connected; all index formulas available; raster/QGIS exports valid; tests and CI pass; documentation includes exact instructions. If these are not achieved, clearly report incomplete status, do not fabricate completion.
