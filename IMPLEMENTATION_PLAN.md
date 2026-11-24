# ARCAMBE GeoAnalytics — implementation tracking

Source: the supplied v1 package. Documents describe product requirements; they do not override user instructions or authorize external account creation.

## Accepted scope clarification — 20 November 2026

The owner clarified that the final product must be fully functional, including account registration and management, free and paid plans, subscriptions and payment integration. The zero-spend constraint applies to the owner's purchases and operating expenses: domain registration, paid hosting, paid cloud resources and similar services are on hold. It does not defer implementation of the platform's commercial features.

Payment flows must first be implemented and validated in a payment provider's test/sandbox environment, without real charges. Activating paid infrastructure or live transactions remains a separate action requiring the owner's instruction. The original v1 specification's Free/Beta-only scope is the delivered baseline, not the final scope after this clarification.

### Commercial completion gates — pending implementation

- [ ] Real registration, email verification, Google sign-in, password recovery, sessions and account management validated with the configured project and backend.
- [ ] Free and paid plan catalog, with final prices/currency confirmed by the owner.
- [ ] Plan entitlements and quotas enforced by the backend; the interface reflects the same subscription state.
- [ ] Subscription checkout and payment status integrated with a supported provider in test mode.
- [ ] Plan activation driven by verified server-side payment events, with duplicate-event idempotency and tenant isolation.
- [ ] Renewal, cancellation, upgrade/downgrade and failed/expired payment behavior verified, including resulting access and limits.
- [ ] Account billing/usage view exposes the actual plan and subscription status; no simulated paid activation presented as a completed transaction.
- [ ] Complete online integration of interface, authentication, API, worker, database, storage and exports; no frontend-only publication treated as a working platform.
- [ ] Paid hosting/domain and live payment activation remain on hold until the owner explicitly decides to proceed.

Payment provider eligibility, merchant account, final pricing and transaction currency remain to be resolved before live payment onboarding. This does not block independent product development. Current verified work and remaining gaps must continue to be reported separately; the commercial gates above have not yet been delivered.

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
- Firebase public configuration has been supplied and the frontend is deployed on Vercel Hobby. Backend administrative credentials, hosted database/storage and processing still require setup and live validation. GCP/Cloud Tasks and billing remain unprovisioned.
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

## Online continuation — 24 November 2026

- Frontend deployed by the owner at https://geo-analise.vercel.app; HTTP 200/title verified.
- Prepared `render.yaml` with one explicitly Free Docker web service, production authentication, embedded durable-queue consumer and conservative analysis limits. No paid resource has been created.
- Implemented private Supabase artifact storage, immutable hash-addressed uploads with retry verification, bounded previews and short-lived authorized download redirects. Scratch products are removed after remote publication.
- Prepared a dedicated `arcambe` PostgreSQL schema, revoked browser/public grants and enabled RLS, with a new PostGIS CI check for browser-role denial.
- Real provider accounts/secrets, Firebase authorized domain, hosted deployment, memory measurements and complete user-flow validation remain pending. This does not complete the commercial gates above.
