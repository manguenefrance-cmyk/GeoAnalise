# ARCHITECTURE / SECURITY / OPERATIONS

## Structure
Frontend Next.js App Router, TypeScript, React, MapLibre, react-hook-form + zod, TanStack Query, i18next/next-intl; API FastAPI, Pydantic v2, SQLAlchemy 2.x/GeoAlchemy2, Alembic, PostgreSQL/PostGIS. Processor independently deployable Python Rasterio/GDAL/NumPy with source adapters and isolated worker image. Async: API stores durable job then Cloud Tasks dispatches Cloud Run Jobs or equivalent worker; local dev Redis/RQ or docker-compose worker using same handler interface. Consumer acknowledges only after durable state. States queued/running/succeeded/failed/cancelled and timeout with retry. Object storage GCS private; local emulator/MinIO with same storage interface. TiTiler or raster tile proxy authorizes each requested preview; do not expose private object path via unauthenticated tile routes.

## Security invariants
- Firebase Identity token validation with issuer, project audience, expiry, UID; verify on API request. Distinct dev/test emulator credentials never in production.
- Individual user belongs to a personal organization; every query for project, AOI, scene selection, analysis, job, artifact includes membership and tenant authorization. Never trust organization_id from client alone. Object download and map tiles check access. No cross-tenant bulk list.
- Database constraints + user authorization + audit log. For higher assurance row-level security planned; if implemented, avoid service-account bypass and test it.
- SQL parameterization; strict GeoJSON parsing, ZIP safeguards against path traversal / zip bombs, file type and max size checks, shapefile required .shp/.shx/.dbf/.prj; cap vertices and coordinate ranges. Restrict external raster URLs to approved provider domains and no metadata-service access (SSRF).
- All expensive operations server quota checked transactionally, idempotency key, reservation debit/refund on failure and prevent duplicate usage. Rate limit registration, login and workloads; provider 429 backoff. Secrets in GCP Secret Manager or environment injection, never repository. HTTPS CORS allowlist, restrictive CSP, server-side audit, telemetry sanitization.
- No raw user location tracking; privacy policy, data retention, account deletion, GDPR-aware workflow for international rollout, legal review before collecting paid subscription info.
- Cloud cost control: max AOI and job count, CPU/memory quotas, budget alerts, max raster bytes, timeouts, TTL for downloads, cache content-addressed results, usage metrics.

## Deployment
GCP reference architecture: Cloud Run Next.js (or managed frontend), Cloud Run API, Cloud Run Jobs worker, Cloud SQL PostgreSQL with PostGIS, GCS, Secret Manager, Cloud Logging/Monitoring, Cloud Tasks; Firebase Auth; custom domains after DNS setup. IAM per service with least privilege. Ensure Cloud Run Jobs dispatch design proven and errors observable. Min instances=0 where appropriate; Cloud SQL costs should be monitored. Infrastructure as Terraform modules with separate staging/production state and secrets not in tfstate outputs. CI GitHub Actions: lint, formatting, typecheck, unit tests, migration smoke, API auth tests, frontend e2e + raster fixtures, container scan, build artifacts.

## Observability and service behavior
Request ID, tenant ID (opaque), job ID, source item ID, processing version, duration, pixel count, billed units; avoid logging JWT/token/download URL. Histograms for p95 API latency, job latency, failed jobs, provider errors, cloud spending. Alert on processing backlog, long tasks, repeated auth failures. Backups and restore drills; disaster recovery RPO/RTO to be established prior production. Operational playbook includes deploy/rollback, queue drain and credentials rotation.

## Accessibility and i18n
English default, Portuguese secondary; all validation/errors/formula descriptions localized. PDF report locale selected by user. Consistent number/date formatting, keyboard accessible map controls, accessible alternatives for charts, contrast WCAG target AA, responsive >=360px.

## Deliverables required
Docker Compose, `.env.example` (NO real secrets), seed command with test GeoJSON and small raster fixture, migrations, OpenAPI schema, docs, terraform reference, GitHub Actions CI, deployment runbook, test report and screenshots from actual local running app.
