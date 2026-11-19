# ARCAMBE GeoAnalytics — Codex handoff package v1.0
Date: 2026-11-17 | Owner: ARCAMBE – SIG & Soluções Ambientais, SU, LDA

## Read order
1. `CODEX_MASTER_PROMPT.md` — paste this into Codex at the repository root.
2. `specs/PRODUCT_AND_UI.md` — business goals, screens, journeys, acceptance.
3. `specs/GEOSPATIAL_ENGINE.md` — scientific algorithms and processing rules.
4. `specs/ARCHITECTURE_SECURITY.md` — tech stack, security, execution, deployment.
5. `specs/DATABASE_API.md` and `contracts/openapi.yaml` — persistence and API contract.
6. `specs/BACKLOG_AND_TESTS.md` — tickets, quality gates, acceptance.
7. `contracts/spectral_indices.yaml` — executable catalog specification (formula registry).
8. `tests/reference_vectors.json` — numerical unit test cases.
9. `SOURCE_TRACEABILITY.md` — exact source scope, attribution, technical sources.

## Non-negotiable deliverable
A working, responsive, bilingual web application and a functioning Sentinel-2 L2A Python processing backend; not a landing-page-only prototype, screenshots, hardcoded demo outputs, or fictitious successful operations. Progress must be truthful; if imagery cannot be accessed with credentials, return a clear actionable error and allow deterministic offline fixtures.

## Scientific scope
The attached 258-page  *Fundamentals of Remote Sensing* textbook explicitly names NDVI, and describes band ratios, multitemporal subtraction and PCA (section 4.6, printed pages 158–160). The additional indices in `spectral_indices.yaml` are an intentional modern extension, NOT a claim that the manual lists them. Some are derived from external scientific sources. The specified indices are the CONTRACT and ALL must be implemented, tested and surfaced in the UI.

## Hand-off procedure
Copy all files from this directory into a new Git repository (e.g. `arcambe-geoanalytics/`). Include the original PDF as a local reference only if licensed and necessary: do not redistribute copyrighted book pages in the public repository. Instruct Codex to follow the master prompt, implement code incrementally, run tests and identify blocked integrations rather than inventing credentials.
