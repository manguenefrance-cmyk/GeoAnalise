# Deployment and operations

## Validated local configuration

Python 3.13 on Windows, SQLite WAL for isolated test mode, Node.js 26 on the development host, Next.js production build. `scripts/start-local.ps1` starts a private loopback laboratory. The production container targets Node.js 24 and Python 3.13; container builds have not run on this host.

`docker compose up --build` declares PostGIS, a migration barrier, API, independent database-polling worker and web. Shared local volume stores raster artifacts. No database/public artifact ports are exposed. Test mode is deliberately used by this local Compose; do not expose it to the Internet.

## Verified production container integration — 20 November 2026

The [GitHub Actions run](https://github.com/manguenefrance-cmyk/GeoAnalise/actions/runs/44691447342) built the images and started `infra/production/compose.yaml` with PostgreSQL/PostGIS, migrations, API, worker and frontend. Checks passed for database readiness, Web/API proxying and rejection of local test tokens in production. The Python image installs `libexpat1` and checks scientific-library imports during the build. Evidence: `docs/evidence/github-ci-validation.json`.

This test used placeholder public Firebase configuration, with no real user credentials. Caddy/ACME was not started. A live Firebase login and public HTTPS certificate still need validation on the chosen server and domain. See [the first-host deployment guide](COLOCAR_ONLINE.pt.md).

## Production preflight

1. Configure a PostgreSQL/PostGIS instance and run `alembic upgrade head`. The initial migration installs PostGIS, an AOI MultiPolygon geometry mirror, sync trigger and GiST index. SQLite remains test-only. PostgreSQL uses native UUID and timestamp-with-time-zone mappings.
2. Configure Firebase project, web configuration and server Application Default Credentials. Run real registration, email verification, reset, token expiry/revocation and user-isolation checks. These code paths are implemented but have not been tested against a configured project.
3. Choose private storage: the initial single-host production Compose uses a shared private persistent volume (`STORAGE_BACKEND=local`). For GCS storage, set `STORAGE_BACKEND=gcs`, `GCS_BUCKET` and, for workload identity, `GCS_SIGNER_EMAIL`. The private GCS adapter uploads immutable checksum-named objects, serves authorized previews, opens COGs through short-lived signed URLs and removes unreferenced published products after failures/cancellation. It verifies uniform access and enforced public-access prevention. The API/worker require bucket metadata-read permission; the signer requires object-read permission, and each caller requires `iam.serviceAccounts.signBlob` on that signer. ADC can also use a signing service-account credential. This adapter is tested offline, not against a live bucket. **Separate Cloud Run containers do not share the local directory:** GCS mode is required for that topology; old local products require migration. Signed GCS capabilities can remain usable until their at-most-five-minute expiry after redirect.
4. Configure worker dispatch/leases for the target platform. The implemented database queue supports long-running local/container workers. Cloud Tasks → Cloud Run Jobs dispatch is not implemented. The API never claims tasks were dispatched to GCP.
5. Configure CORS, HTTPS ingress, production hostnames, CSP nonces, persistent download signing secrets and proxy-aware distributed rate limiting. The current rate limiter is per API process; quotas and job idempotency are transactionally stored in the database.
6. Configure quotas, memory/CPU budgets, provider access policy, service timeouts, monitoring, backups and restore tests. Default queue leases expire after 20 minutes, with failure/refund; cancellation is best effort before publishing outputs.
7. Schedule `python scripts/cleanup.py` for seven-day retention of deleted-project products. Configure backup expiration and orphan-file cleanup. Review legal terms/privacy and implement verified account erasure before accepting public registrations.

## Terraform reference

`infra/gcp/main.tf` defines only the provisioning foundation: private uniform-access bucket, service accounts, IAM and Secret Manager containers. It contains no secret values, active workload deployment, Cloud SQL creation or completed production topology. Terraform has not been run. Review region availability, versions, IAM and budget before applying.

## Runbook

- **Failure:** use API request ID and job ID. API messages intentionally omit provider credentials/paths. Worker logs show safe code and exception class. All destructive operations create tenant audit events.
- **Queue drain:** stop accepting new analysis requests at ingress, allow running jobs to settle, then stop the worker. Queued jobs remain durable; restart workers to resume.
- **Rollback:** stop API/workers, restore prior image versions, verify migration compatibility, restart. Back up the DB and private artifacts before schema changes. Do not downgrade live data without a restore plan.
- **Signing-key rotation:** replace DOWNLOAD_SECRET consistently on every API instance. Existing five-minute capabilities become invalid; authenticated users request new ones.
- **Project deletion:** access is revoked immediately; queued jobs settle as cancelled, running jobs receive a cancellation request. Retention cleanup handles stored artifacts separately.

## Known production gaps

Live GCS validation/Cloud Tasks adapter, real Firebase integration validation, CDSE OAuth/S3 access, distributed rate limiting/circuit breaker, workload/restore drills, full browser E2E automation in CI, manual QGIS desktop review, account deletion/legal workflow, formal accessibility audit and performance/load/security scanning remain release gates. Billing remains disabled.

## Validation update — 19 November 2026

Firebase requests obtain `getIdToken()` before API calls; token observers and periodic refresh update the visible session, and logout signs out of the SDK. SDK integration still needs a configured Firebase project for live validation.

Account-deletion requests are persisted as private audit events through `/v1/me/deletion-request`, with idempotent registration, status and cancellation. They do not automatically erase identity or data. An operator must review and fulfill them according to the final retention/legal policy.

`DAILY_ATTEMPT_LIMIT` defaults to 20, separately from 5 successful/reserved daily credits. Failed and cancelled jobs refund credits but still count as attempts. Hard worker termination can bypass the publication cleanup finally block; production operations still need orphan reconciliation, retention of scratch files and storage budget alerts.

Primary references: [GCS V4 signing](https://docs.cloud.google.com/storage/docs/access-control/signing-urls-with-helpers), [Firebase token observer](https://firebase.google.com/docs/reference/js/auth), [QGIS 3.44 Raster Calculator](https://qgis.org/pyqgis/3.44/analysis/QgsRasterCalculator.html).

## Container build configuration

Next.js rewrites are part of its build output. Build the frontend with `API_URL` pointing to the API's address reachable from the web container; Compose passes `http://api:8000` as both build argument and runtime environment. Public Firebase web values must also be supplied as build arguments. Private `.env` files are excluded from the build context and the source archive. Docker execution remains unverified on this host.

For local Swagger UI use http://127.0.0.1:8000/docs. The application's documentation link serves the public OpenAPI schema at `/api/openapi.json`, avoiding an unusable Swagger page behind the frontend CSP/proxy prefix.
