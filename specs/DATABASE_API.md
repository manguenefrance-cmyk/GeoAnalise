# DATABASE AND API DOMAIN CONTRACT

## PostgreSQL schema
All primary keys UUID; `created_at/updated_at` timezone aware UTC. PostGIS extensions installed by migration. Objects belong to an organization (personal organizations in MVP). Geometry `geometry(MultiPolygon,4326)`, GiST spatial index. Maintain hard database FK and tenant authorization in application. Project soft-delete and asynchronous artifact TTL cleanup.

`users`: id, firebase_uid UNIQUE, email, display_name, locale enum(en,pt), created_at, updated_at.
`organizations`: id, name, kind(personal/business), created_at.
`memberships`: id, user_id, organization_id, role(owner,editor,viewer), UNIQUE(user_id,org_id).
`projects`: id, organization_id FK, name, description, status(active,archived,deleted), created_by, timestamps.
`aoi`: id, project_id FK, geom MultiPolygon(4326), area_km2, name, source, native_crs, timestamps; validated area and 100km² max.
`scenes`: id, provider, collection, stac_item_id, acquired_at, cloud_cover_scene, footprint, assets_metadata JSONB, processing_baseline, UNIQUE(provider,collection,stac_item_id).
`analyses`: id, organization_id, project_id, aoi_id, scene_id nullable for multi-input, operation_kind(index,band_ratio,temporal_diff,pca,composite), operation_id (catalog ID), params JSONB, algorithm_version, status, provenance JSONB, created_by, timestamps.
`analysis_inputs`: id, analysis_id, source_scene_id nullable, source_analysis_id nullable, role (primary,earlier,later,etc).
`jobs`: id, analysis_id, status, attempt, idempotency_key, worker_execution_id, progress_nullable, error_code_nullable, error_message_safe, started_at, finished_at, created_at; UNIQUE(organization_id,idempotency_key) via a tenant-owned key table or scoped column.
`artifacts`: id, analysis_id, organization_id, artifact_type(cog,png,pdf,json,pca_band), storage_key, mime_type, bytes, checksum, expires_at, created_at.
`usage_events`: id, organization_id, analysis_id, units_reserved, units_settled, status, created_at; exactly-once settlement transaction.
`audit_events`: id, actor_user_id, organization_id, action, resource_type, resource_id, metadata_sanitized, created_at.
`quota_policies`: organization_id, daily_limit, concurrent_limit, area_max_km2, max_scene_search_days, cpu_seconds_budget; defaults from environment.

## Endpoint contract (prefix `/v1`)
`GET /healthz` liveness; `GET /readyz` readiness (internal). `GET /me`, `PATCH /me`; `GET/POST /projects`; `GET/PATCH/DELETE /projects/{project_id}`; `GET/POST /projects/{project_id}/aois`, `GET/DELETE /aois/{aoi_id}`; `POST /satellite/search` STAC paginated; `GET /indices` returns registry categories/formulas/bands/limits and descriptions; `POST /analyses` enqueue; `GET /analyses?project_id=...`, `GET /analyses/{analysis_id}`; `GET /jobs/{job_id}`, `POST /jobs/{job_id}/cancel`; `POST /analyses/{analysis_id}/exports`, `GET /exports?project_id=...`, `GET /artifacts/{artifact_id}/download`, `GET /artifacts/{artifact_id}/tiles/{z}/{x}/{y}.png` authorized or tokenized limited capability; `GET /usage`.

## Formats and validation
POST analysis takes project_id,aoi_id,operation_kind, operation_id, scene_id or input_analysis_ids, params; header `Idempotency-Key`; JSON response HTTP 202 includes analysis/job IDs and reserved quota. Validate operation-specific band requirements against catalog on server. Results HTTP 200 include job status and stats, metadata, outputs only once succeeded. Cancellations HTTP 202 best effort; errors consistent `{error:{code,message,request_id,details?}}`. Pagination for project, scene, job and artifact lists. UTC ISO8601 timestamps. Use UUID in real application; sample JSON using placeholder strings not accepted by strict runtime.

## Strict access test cases
Tenant A cannot view tenant B project, AOI, analysis, job, raster tiles, exports nor use a known artifact ID to download. Deleting owning project must make endpoints unreachable and queue cleanup. Job cancellation requires edit access. A user cannot exceed quotas by concurrent POST or replay retries.

## Example request
```
POST /v1/analyses
Idempotency-Key: generated-client-uuid
Authorization: Bearer <firebase-id-token>
{
 "project_id":"<uuid>","aoi_id":"<uuid>",
 "operation_kind":"index","operation_id":"NDVI",
 "scene_id":"<uuid>",
 "params":{"mask":"SCL_DEFAULT","resolution_policy":"coarsest_native"}
}
```
Response HTTP 202 with queued job; no fake result value before processing.

## OpenAPI
`contracts/openapi.yaml` provides route skeletons and schema; implementation must generate fully expanded OpenAPI from FastAPI, ensure no drift and update contracts as models evolve. Document real error codes, authentication and provenance.
