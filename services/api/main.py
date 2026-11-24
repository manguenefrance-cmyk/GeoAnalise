import hashlib
import hmac
import json
import logging
import secrets
import time
import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID
from typing import Literal

import numpy as np
import rasterio
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sqlalchemy import func, select, text
from services import __version__

from services.processor.exports import png_bytes
from services.processor.fixtures import FIXTURE_GEOMETRY, create_fixture
from services.processor.registry import BANDS, REGISTRY
from services.processor.stac import ProviderError, search_cached
from services.processor.sensors import LANDSAT, SENTINEL, band_resolutions, catalog_for, sensor_of
from .auth import current_user, require_editor
from .config import settings
from .db import (
    AOI,
    Analysis,
    Artifact,
    Audit,
    Base,
    Job,
    Project,
    Scene,
    Usage,
    engine,
    get_db,
    now,
    serialize,
)
from .geometry import read_shapefile_zip, validate_aoi
from .jobs import locked, settle
from .schemas import AnalysisCreate, AreaCreate, ProfilePatch, ProjectCreate, ProjectPatch, SceneSearch
from .storage import GCSStorage, StorageError, storage_for
from .supabase_storage import SupabaseStorage
from .responses import DeletionRequestView, DashboardView
from .responses import (
    AnalysisView,
    AreaView,
    ArtifactView,
    CatalogView,
    DeletedView,
    DownloadView,
    ErrorEnvelope,
    HealthView,
    JobView,
    PixelView,
    ProfileView,
    ProjectView,
    ReadyView,
    SceneView,
    SearchView,
    SeedView,
    UsageView,
)


@asynccontextmanager
async def lifespan(app):
    settings.validate_runtime()
    if settings.app_env == "test":
        Base.metadata.create_all(engine)
    worker = None
    if settings.worker_embedded:
        from .embedded_worker import EmbeddedWorker

        worker = EmbeddedWorker()
        worker.start()
    try:
        yield
    finally:
        if worker:
            await asyncio.to_thread(worker.stop)


app = FastAPI(
    title="ARCAMBE GeoAnalytics",
    version=__version__,
    lifespan=lifespan,
    responses={code: {"model": ErrorEnvelope} for code in (400, 401, 403, 404, 409, 413, 422, 429, 500, 503)},
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
requests_by_ip = defaultdict(deque)
download_secret = settings.download_secret or secrets.token_hex(32)


@app.middleware("http")
async def request_controls(request: Request, call_next):
    request.state.request_id = secrets.token_hex(12)
    if int(request.headers.get("content-length", 0)) > 6_000_000:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "UPLOAD_TOO_LARGE",
                    "message": "UPLOAD_TOO_LARGE",
                    "request_id": request.state.request_id,
                }
            },
        )
    if request.url.path not in ("/healthz", "/readyz"):
        key = request.client.host if request.client else "unknown"
        current = time.monotonic()
        for old_key in list(requests_by_ip):
            q = requests_by_ip[old_key]
            while q and q[0] < current - 60:
                q.popleft()
            if not q:
                del requests_by_ip[old_key]
        bucket = requests_by_ip[key]
        if len(bucket) >= 240:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT",
                        "message": "RATE_LIMIT",
                        "request_id": request.state.request_id,
                    }
                },
                headers={"Retry-After": "60"},
            )
        bucket.append(current)
    try:
        response = await call_next(request)
    except Exception as exc:
        # Exception strings can contain credential-bearing raster URLs. Log only safe identifiers.
        logging.getLogger("arcambe.api").error(
            "request_failed request_id=%s type=%s", request.state.request_id, type(exc).__name__
        )
        response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "INTERNAL_ERROR",
                    "request_id": request.state.request_id,
                }
            },
        )
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(HTTPException)
async def api_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": str(exc.detail),
                "message": str(exc.detail),
                "request_id": request.state.request_id,
            }
        },
    )


@app.exception_handler(StorageError)
async def storage_error(request, exc):
    code = str(exc)
    status = 404 if code == "ARTIFACT_EXPIRED" else 503
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": code, "request_id": request.state.request_id}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_INPUT",
                "message": "INVALID_INPUT",
                "request_id": request.state.request_id,
                "details": jsonable_encoder(
                    [{k: v for k, v in item.items() if k in ("loc", "msg", "type")} for item in exc.errors()]
                ),
            }
        },
    )


def audit(db, user, action, resource):
    db.add(Audit(organization_id=user.organization_id, actor=user.id, action=action, resource_id=resource))


def project_owned(db, user, ident, edit=False):
    project = db.get(Project, str(ident))
    if not project or project.organization_id != user.organization_id or project.status == "deleted":
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    if edit:
        require_editor(db, user)
    return project


def area_owned(db, user, ident, edit=False):
    area = db.get(AOI, str(ident))
    if not area:
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    project_owned(db, user, area.project_id, edit)
    return area


def analysis_owned(db, user, ident, edit=False):
    analysis = db.get(Analysis, str(ident))
    if not analysis or analysis.organization_id != user.organization_id:
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    project_owned(db, user, analysis.project_id, edit)
    return analysis


def job_owned(db, user, ident, edit=False):
    job = db.get(Job, str(ident))
    if not job or job.organization_id != user.organization_id:
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    analysis_owned(db, user, job.analysis_id, edit)
    return job


def artifact_owned(db, user, ident):
    artifact = db.get(Artifact, str(ident))
    if not artifact or artifact.organization_id != user.organization_id:
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    analysis_owned(db, user, artifact.analysis_id)
    return artifact


def analysis_result(db, analysis):
    return {
        **serialize(analysis),
        "job": serialize(db.scalar(select(Job).where(Job.analysis_id == analysis.id))),
        "artifacts": [
            {k: v for k, v in serialize(a).items() if k != "storage_key"}
            for a in db.scalars(select(Artifact).where(Artifact.analysis_id == analysis.id))
        ],
    }


@app.get("/healthz", response_model=HealthView)
def health():
    return {"status": "ok", "version": __version__, "mode": settings.app_env}


@app.get("/readyz", response_model=ReadyView)
def ready(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/v1/me", response_model=ProfileView)
def me(user=Depends(current_user)):
    return serialize(user)


def deletion_state(db, user):
    event = db.scalar(
        select(Audit)
        .where(
            Audit.actor == user.id,
            Audit.resource_id == user.id,
            Audit.organization_id == user.organization_id,
            Audit.action.in_(["account.deletion_requested", "account.deletion_cancelled"]),
        )
        .order_by(Audit.created_at.desc())
        .limit(1)
    )
    if not event:
        return {"status": "none"}
    return {
        "status": "requested" if event.action == "account.deletion_requested" else "cancelled",
        "request_id": event.id,
        "requested_at": event.created_at,
    }


@app.get("/v1/me/deletion-request", response_model=DeletionRequestView)
def deletion_request_status(user=Depends(current_user), db=Depends(get_db)):
    return deletion_state(db, user)


@app.post("/v1/me/deletion-request", status_code=202, response_model=DeletionRequestView)
def request_account_deletion(user=Depends(current_user), db=Depends(get_db)):
    with locked(db, user.organization_id):
        state = deletion_state(db, user)
        if state["status"] != "requested":
            audit(db, user, "account.deletion_requested", user.id)
            db.flush()
            state = deletion_state(db, user)
    return state


@app.delete("/v1/me/deletion-request", response_model=DeletionRequestView)
def cancel_account_deletion(user=Depends(current_user), db=Depends(get_db)):
    with locked(db, user.organization_id):
        state = deletion_state(db, user)
        if state["status"] == "requested":
            audit(db, user, "account.deletion_cancelled", user.id)
            db.flush()
            state = deletion_state(db, user)
    return state


@app.patch("/v1/me", response_model=ProfileView)
def profile(body: ProfilePatch, user=Depends(current_user), db=Depends(get_db)):
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(user, key, value)
    db.commit()
    return serialize(user)


@app.get("/v1/projects", response_model=list[ProjectView])
def projects(limit: int = 30, offset: int = 0, user=Depends(current_user), db=Depends(get_db)):
    return [
        serialize(p)
        for p in db.scalars(
            select(Project)
            .where(Project.organization_id == user.organization_id, Project.status != "deleted")
            .order_by(Project.created_at.desc())
            .limit(max(1, min(limit, 100)))
            .offset(max(0, offset))
        )
    ]


@app.get("/v1/dashboard", response_model=DashboardView)
def dashboard(user=Depends(current_user), db=Depends(get_db)):
    count = db.scalar(
        select(func.count())
        .select_from(Project)
        .where(Project.organization_id == user.organization_id, Project.status != "deleted")
    )
    states = dict(
        db.execute(
            select(Analysis.status, func.count())
            .join(Project)
            .where(Analysis.organization_id == user.organization_id, Project.status != "deleted")
            .group_by(Analysis.status)
        ).all()
    )
    return {
        "project_count": count,
        "completed_analyses": states.get("succeeded", 0),
        "active_jobs": states.get("queued", 0) + states.get("running", 0),
    }


@app.post("/v1/projects", status_code=201, response_model=ProjectView)
def create_project(body: ProjectCreate, user=Depends(current_user), db=Depends(get_db)):
    require_editor(db, user)
    p = Project(organization_id=user.organization_id, **body.model_dump())
    db.add(p)
    db.flush()
    audit(db, user, "project.create", p.id)
    db.commit()
    return serialize(p)


@app.get("/v1/projects/{project_id}", response_model=ProjectView)
def get_project(project_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    return serialize(project_owned(db, user, project_id))


@app.patch("/v1/projects/{project_id}", response_model=ProjectView)
def patch_project(project_id: UUID, body: ProjectPatch, user=Depends(current_user), db=Depends(get_db)):
    p = project_owned(db, user, project_id, True)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(p, key, value)
    p.updated_at = now()
    audit(db, user, "project.update", p.id)
    db.commit()
    return serialize(p)


@app.delete("/v1/projects/{project_id}", response_model=DeletedView)
def delete_project(project_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    project_owned(db, user, project_id, True)
    with locked(db, user.organization_id):
        p = project_owned(db, user, project_id, True)
        p.status, p.updated_at = "deleted", now()
        for a in db.scalars(select(Analysis).where(Analysis.project_id == p.id)):
            job = db.scalar(select(Job).where(Job.analysis_id == a.id))
            if job.status == "queued":
                settle(db, job, "cancelled")
            elif job.status == "running":
                job.cancel_requested = True
        audit(db, user, "project.delete", p.id)
    return {"status": "deleted", "artifact_retention_days": 7}


@app.get("/v1/projects/{project_id}/aois", response_model=list[AreaView])
def areas(project_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    project_owned(db, user, project_id)
    return [serialize(a) for a in db.scalars(select(AOI).where(AOI.project_id == str(project_id)))]


def add_area(db, user, project_id, name, geometry, source="geojson"):
    project_owned(db, user, project_id, True)
    try:
        geometry, area = validate_aoi(geometry, settings.max_aoi_km2)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    a = AOI(project_id=str(project_id), name=name, geometry=geometry, area_km2=area, source=source)
    db.add(a)
    db.flush()
    audit(db, user, "aoi.create", a.id)
    db.commit()
    return serialize(a)


@app.post("/v1/projects/{project_id}/aois", status_code=201, response_model=AreaView)
def create_area(project_id: UUID, body: AreaCreate, user=Depends(current_user), db=Depends(get_db)):
    return add_area(db, user, project_id, body.name, body.geometry)


@app.post("/v1/projects/{project_id}/aois/import", status_code=201, response_model=AreaView)
async def import_area(
    project_id: UUID, file: UploadFile = File(...), user=Depends(current_user), db=Depends(get_db)
):
    project_owned(db, user, project_id, True)
    content = await file.read(5_000_001)
    if len(content) > 5_000_000:
        raise HTTPException(413, "UPLOAD_TOO_LARGE")
    try:
        if (file.filename or "").lower().endswith(".zip"):
            geometry = read_shapefile_zip(content)
        else:
            payload = json.loads(content)
            if payload.get("type") == "FeatureCollection":
                if len(payload["features"]) != 1:
                    raise ValueError("IMPORT_ONE_AOI")
                payload = payload["features"][0]
            geometry = payload.get("geometry", payload)
    except Exception as exc:
        raise HTTPException(
            400, str(exc) if isinstance(exc, ValueError) and str(exc).isupper() else "INVALID_IMPORT"
        ) from exc
    return add_area(db, user, project_id, (file.filename or "Imported AOI")[:180], geometry, "import")


@app.get("/v1/aois/{aoi_id}", response_model=AreaView)
def get_area(aoi_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    return serialize(area_owned(db, user, aoi_id))


@app.delete("/v1/aois/{aoi_id}", response_model=DeletedView)
def delete_area(aoi_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    area = area_owned(db, user, aoi_id, True)
    if db.scalar(select(Analysis.id).where(Analysis.aoi_id == area.id).limit(1)):
        raise HTTPException(409, "AOI_HAS_ANALYSES_ARCHIVE_PROJECT_INSTEAD")
    audit(db, user, "aoi.delete", area.id)
    db.delete(area)
    db.commit()
    return {"status": "deleted"}


def scene_card(scene):
    item = scene.item
    return {
        "sensor": sensor_of(item),
        "id": scene.id,
        "stac_item_id": item["id"],
        "sample": scene.sample,
        "geometry": item.get("geometry"),
        "properties": item.get("properties", {}),
        "collection": item.get("collection"),
        "asset_keys": list(item.get("assets", {})),
    }


@app.post("/v1/satellite/search", response_model=SearchView)
def search(body: SceneSearch, user=Depends(current_user), db=Depends(get_db)):
    area = area_owned(db, user, body.aoi_id)
    if not 0 <= (body.date_end - body.date_start).days <= 366:
        raise HTTPException(400, "DATE_RANGE_MAX_12_MONTHS")
    try:
        items, has_more = search_cached(
            json.dumps(area.geometry, sort_keys=True),
            body.date_start.isoformat(),
            body.date_end.isoformat(),
            body.max_cloud_cover,
            body.limit,
            int(time.time() // 300),
            body.provider,
        )
    except ProviderError as exc:
        raise HTTPException(503, str(exc)) from exc
    cards = []
    for item in items:
        existing = db.scalars(
            select(Scene).where(Scene.organization_id == user.organization_id, Scene.sample.is_(False))
        )
        scene = next((s for s in existing if s.item["id"] == item["id"]), None)
        if not scene:
            scene = Scene(organization_id=user.organization_id, item=item, sample=False)
            db.add(scene)
            db.flush()
        cards.append(scene_card(scene))
    db.commit()
    return {
        "scenes": cards,
        "has_more": has_more,
        "provider": body.provider,
        "cloud_metric": "scene_level",
        "pixel_access": "Requires individually accessible calibrated raster assets; discovery alone does not grant access",
    }


@app.get("/v1/indices", response_model=CatalogView)
def indices(sensor: Literal["sentinel-2", "landsat-8-9"] = SENTINEL, user=Depends(current_user)):
    return catalog_for(sensor)


@app.get("/v1/scenes", response_model=list[SceneView])
def list_scenes(user=Depends(current_user), db=Depends(get_db)):
    return [
        scene_card(s)
        for s in db.scalars(select(Scene).where(Scene.organization_id == user.organization_id).limit(100))
        if not s.sample or settings.app_env == "test"
    ]


@app.post("/v1/test/seed", status_code=201, response_model=SeedView)
def seed(user=Depends(current_user), db=Depends(get_db)):
    if settings.app_env != "test":
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    require_editor(db, user)
    p = db.scalar(
        select(Project).where(
            Project.organization_id == user.organization_id,
            Project.name == "Synthetic raster laboratory",
            Project.status == "active",
        )
    )
    if not p:
        p = Project(
            organization_id=user.organization_id,
            name="Synthetic raster laboratory",
            description="Deterministic synthetic GeoTIFF fixtures. NOT satellite observations.",
        )
        db.add(p)
        db.flush()
        add_area(db, user, p.id, "Maputo test grid", FIXTURE_GEOMETRY, "fixture")
    cards = []
    for variant in (0, 1):
        scene = next(
            (
                s
                for s in db.scalars(
                    select(Scene).where(Scene.organization_id == user.organization_id, Scene.sample.is_(True))
                )
                if s.item["id"] == f"SYNTHETIC-TEST-{variant}"
            ),
            None,
        )
        if not scene:
            item = create_fixture(settings.data_dir / "fixtures" / str(variant), variant)
            scene = Scene(organization_id=user.organization_id, item=item, sample=True)
            db.add(scene)
            db.flush()
        cards.append(scene_card(scene))
    audit(db, user, "test.seed", p.id)
    db.commit()
    return {"project": serialize(p), "scenes": cards, "sample": True}


@app.post("/v1/analyses", status_code=202, response_model=AnalysisView)
def enqueue(
    body: AnalysisCreate,
    idempotency_key: str = Header(min_length=8, max_length=128),
    user=Depends(current_user),
    db=Depends(get_db),
):
    project_owned(db, user, body.project_id, True)
    area = area_owned(db, user, body.aoi_id)
    if area.project_id != str(body.project_id):
        raise HTTPException(400, "AOI_PROJECT_MISMATCH")
    if body.operation_kind == "index" and body.operation_id not in REGISTRY:
        raise HTTPException(400, "UNKNOWN_INDEX")
    if body.operation_kind != "temporal_diff":
        scene = db.get(Scene, str(body.scene_id))
        if (
            not scene
            or scene.organization_id != user.organization_id
            or (scene.sample and settings.app_env != "test")
        ):
            raise HTTPException(404, "SCENE_NOT_FOUND")
        try:
            sensor = sensor_of(scene.item)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    else:
        if len(body.input_analysis_ids) != 2:
            raise HTTPException(400, "TWO_SUCCESSFUL_INPUTS_REQUIRED")
        inputs = [analysis_owned(db, user, ident) for ident in body.input_analysis_ids]
        if inputs[0].provenance.get("sensor", SENTINEL) != inputs[1].provenance.get("sensor", SENTINEL):
            raise HTTPException(400, "CROSS_SENSOR_TEMPORAL_COMPARISON_REQUIRES_HARMONIZATION")
    allowed_params = {
        "cloud_mask",
        "mask_scl_2",
        "mask_scl_7",
        "cloud_dilation_m",
        "resolution_m",
        "interpolation",
        "constants",
        "numerator",
        "denominator",
        "bands",
        "standardize",
    }
    if not body.params.keys() <= allowed_params:
        raise HTTPException(400, "UNKNOWN_PARAMETER")
    for flag in ("cloud_mask", "mask_scl_2", "mask_scl_7", "standardize"):
        if flag in body.params and type(body.params[flag]) is not bool:
            raise HTTPException(400, "INVALID_PARAMETER_TYPE")
    if "resolution_m" in body.params and body.params["resolution_m"] not in (10, 20, 30, 60):
        raise HTTPException(400, "INVALID_RESOLUTION")
    if "interpolation" in body.params and body.params["interpolation"] not in ("nearest", "bilinear"):
        raise HTTPException(400, "INVALID_INTERPOLATION")
    if "cloud_dilation_m" in body.params:
        value = body.params["cloud_dilation_m"]
        if type(value) not in (int, float) or not 0 <= value <= 200:
            raise HTTPException(400, "INVALID_CLOUD_DILATION")
    if body.operation_kind == "band_ratio":
        if any(
            body.params.get(key, default) not in BANDS
            for key, default in (("numerator", "B08"), ("denominator", "B04"))
        ):
            raise HTTPException(400, "INVALID_BAND")
    if body.operation_kind in ("pca", "composite"):
        bands = body.params.get("bands", ["B04", "B03", "B02"])
        if not isinstance(bands, list) or any(not isinstance(b, str) or b not in BANDS for b in bands):
            raise HTTPException(400, "INVALID_BAND")
        if (body.operation_kind == "pca" and not 3 <= len(set(bands)) == len(bands) <= 10) or (
            body.operation_kind == "composite" and len(bands) != 3
        ):
            raise HTTPException(400, "INVALID_BAND_COUNT")
    if "constants" in body.params:
        constants = body.params["constants"]
        allowed = REGISTRY.get(body.operation_id, {}).get("constants", {})
        if not isinstance(constants, dict) or not constants.keys() <= allowed.keys():
            raise HTTPException(400, "INVALID_CONSTANT")
        if "L" in constants and (type(constants["L"]) not in (int, float) or not 0 <= constants["L"] <= 1):
            raise HTTPException(400, "INVALID_CONSTANT")
    if len(json.dumps(body.params)) > 4000:
        raise HTTPException(400, "PARAMETERS_TOO_LARGE")
    if body.operation_kind != "temporal_diff":
        supported = band_resolutions(sensor)
        if body.operation_kind == "index":
            selected = REGISTRY[body.operation_id]["bands"]
        elif body.operation_kind == "band_ratio":
            selected = [body.params.get("numerator", "B08"), body.params.get("denominator", "B04")]
        else:
            selected = body.params.get("bands", ["B04", "B03", "B02"])
        if not set(selected) <= supported.keys():
            raise HTTPException(400, "BANDS_UNAVAILABLE_FOR_SENSOR")
        if body.params.get("resolution_m", max(supported[b] for b in selected)) not in (
            (30,) if sensor == LANDSAT else (10, 20, 60)
        ):
            raise HTTPException(400, "INVALID_SENSOR_RESOLUTION")
        if sensor == LANDSAT and (body.params.get("mask_scl_2") or body.params.get("mask_scl_7")):
            raise HTTPException(400, "SCL_OPTIONS_REQUIRE_SENTINEL")
    fingerprint = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    with locked(db, user.organization_id):
        existing = db.scalar(
            select(Job).where(
                Job.organization_id == user.organization_id, Job.idempotency_key == idempotency_key
            )
        )
        if existing:
            if existing.request_hash != fingerprint:
                raise HTTPException(409, "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_INPUT")
            return analysis_result(db, analysis_owned(db, user, existing.analysis_id))
        today = datetime.now(timezone.utc).date().isoformat()
        attempted = db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.organization_id == user.organization_id, Job.created_at >= today)
        )
        if attempted >= settings.daily_attempt_limit:
            raise HTTPException(429, "DAILY_ATTEMPT_LIMIT")
        used = db.scalar(
            select(func.count())
            .select_from(Usage)
            .where(
                Usage.organization_id == user.organization_id,
                Usage.status.in_(["reserved", "settled"]),
                Usage.created_at >= today,
            )
        )
        concurrent = db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.organization_id == user.organization_id, Job.status.in_(["queued", "running"]))
        )
        if used >= settings.daily_job_limit or concurrent >= settings.concurrent_job_limit:
            raise HTTPException(429, "QUOTA_EXCEEDED")
        a = Analysis(
            organization_id=user.organization_id,
            **{**body.model_dump(mode="json"), "scene_id": str(body.scene_id) if body.scene_id else None},
        )
        db.add(a)
        db.flush()
        job = Job(
            organization_id=user.organization_id,
            analysis_id=a.id,
            idempotency_key=idempotency_key,
            request_hash=fingerprint,
        )
        db.add_all([job, Usage(organization_id=user.organization_id, analysis_id=a.id)])
        db.flush()
        audit(db, user, "analysis.enqueue", a.id)
        result = analysis_result(db, a)
    return result


@app.get("/v1/analyses", response_model=list[AnalysisView])
def analyses(
    project_id: UUID | None = None,
    limit: int = 30,
    offset: int = 0,
    user=Depends(current_user),
    db=Depends(get_db),
):
    stmt = (
        select(Analysis)
        .join(Project)
        .where(Analysis.organization_id == user.organization_id, Project.status != "deleted")
    )
    if project_id:
        project_owned(db, user, project_id)
        stmt = stmt.where(Analysis.project_id == str(project_id))
    return [
        analysis_result(db, a)
        for a in db.scalars(
            stmt.order_by(Analysis.created_at.desc()).limit(max(1, min(limit, 100))).offset(max(0, offset))
        )
    ]


@app.get("/v1/analyses/{analysis_id}", response_model=AnalysisView)
def get_analysis(analysis_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    return analysis_result(db, analysis_owned(db, user, analysis_id))


@app.get("/v1/jobs/{job_id}", response_model=JobView)
def get_job(job_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    return serialize(job_owned(db, user, job_id))


@app.post("/v1/jobs/{job_id}/cancel", status_code=202, response_model=JobView)
def cancel(job_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    job_owned(db, user, job_id, True)
    with locked(db, user.organization_id):
        job = job_owned(db, user, job_id, True)
        if job.status == "queued":
            settle(db, job, "cancelled")
        elif job.status == "running":
            job.cancel_requested = True
        audit(db, user, "job.cancel", job.id)
        result = serialize(job)
    return result


@app.get("/v1/usage", response_model=UsageView)
def usage(user=Depends(current_user), db=Depends(get_db)):
    today = datetime.now(timezone.utc).date().isoformat()
    counts = {
        state: db.scalar(
            select(func.count())
            .select_from(Usage)
            .where(
                Usage.organization_id == user.organization_id,
                Usage.status == state,
                Usage.created_at >= today,
            )
        )
        for state in ("reserved", "settled", "refunded")
    }
    return {
        "today": today,
        "attempted": db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.organization_id == user.organization_id, Job.created_at >= today)
        ),
        "daily_attempt_limit": settings.daily_attempt_limit,
        **counts,
        "daily_limit": settings.daily_job_limit,
        "concurrent_limit": settings.concurrent_job_limit,
        "max_aoi_km2": settings.max_aoi_km2,
        "billing_enabled": False,
    }


@app.get("/v1/exports", response_model=list[ArtifactView])
def exports(project_id: UUID | None = None, user=Depends(current_user), db=Depends(get_db)):
    stmt = (
        select(Artifact)
        .join(Analysis)
        .join(Project)
        .where(Artifact.organization_id == user.organization_id, Project.status != "deleted")
    )
    if project_id:
        project_owned(db, user, project_id)
        stmt = stmt.where(Analysis.project_id == str(project_id))
    return [
        {k: v for k, v in serialize(a).items() if k != "storage_key"}
        for a in db.scalars(stmt.order_by(Artifact.created_at.desc()).limit(100))
    ]


@app.post("/v1/analyses/{analysis_id}/exports", response_model=list[ArtifactView])
def request_exports(analysis_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    a = analysis_owned(db, user, analysis_id, True)
    if a.status != "succeeded":
        raise HTTPException(409, "ANALYSIS_NOT_SUCCEEDED")
    audit(db, user, "exports.request", a.id)
    db.commit()
    return analysis_result(db, a)["artifacts"]


def sign(ident, expires):
    return hmac.new(download_secret.encode(), f"{ident}:{expires}".encode(), hashlib.sha256).hexdigest()


@app.get("/v1/artifacts/{artifact_id}/download", response_model=DownloadView)
def download(artifact_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    artifact = artifact_owned(db, user, artifact_id)
    expires = int(time.time()) + 300
    audit(db, user, "artifact.download", artifact.id)
    db.commit()
    return {
        "url": f"/v1/downloads/{artifact.id}?expires={expires}&signature={sign(artifact.id, expires)}",
        "expires_at": expires,
    }


@app.get("/v1/downloads/{artifact_id}")
def signed_download(artifact_id: UUID, expires: int, signature: str, db=Depends(get_db)):
    if (
        expires < time.time()
        or expires > time.time() + 301
        or not hmac.compare_digest(signature, sign(str(artifact_id), expires))
    ):
        raise HTTPException(403, "DOWNLOAD_EXPIRED_OR_INVALID")
    artifact = db.get(Artifact, str(artifact_id))
    if not artifact:
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    analysis = db.get(Analysis, artifact.analysis_id)
    if db.get(Project, analysis.project_id).status == "deleted":
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    store = storage_for(artifact.storage_key)
    if isinstance(store, (GCSStorage, SupabaseStorage)):
        ttl = int(expires - time.time())
        if ttl < 1:
            raise HTTPException(403, "DOWNLOAD_EXPIRED_OR_INVALID")
        return RedirectResponse(
            store.signed_url(
                artifact.storage_key,
                ttl=ttl,
                filename=f"ARCAMBE-{analysis.operation_id}-{store.key(artifact.storage_key).split(chr(47))[-1]}",
            ),
            status_code=307,
        )
    path = store.raster_location(artifact.storage_key)
    return FileResponse(
        path,
        media_type=artifact.mime_type,
        filename=f"ARCAMBE-{analysis.operation_id}-{store.path(artifact.storage_key).name}",
    )


@app.get("/v1/artifacts/{artifact_id}/preview.png")
def preview(artifact_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    artifact = artifact_owned(db, user, artifact_id)
    if artifact.artifact_type != "preview":
        raise HTTPException(400, "PREVIEW_REQUIRED")
    return Response(storage_for(artifact.storage_key).preview(artifact.storage_key), media_type="image/png")


@app.get("/v1/artifacts/{artifact_id}/tiles/{z}/{x}/{y}.png")
def tile(artifact_id: UUID, z: int, x: int, y: int, user=Depends(current_user), db=Depends(get_db)):
    artifact = artifact_owned(db, user, artifact_id)
    if artifact.artifact_type != "cog" or not 0 <= z <= 22 or not (0 <= x < 2**z and 0 <= y < 2**z):
        raise HTTPException(400, "INVALID_TILE")
    extent = 20037508.342789244
    size = extent * 2 / 2**z
    transform = rasterio.transform.from_bounds(
        -extent + x * size, extent - (y + 1) * size, -extent + (x + 1) * size, extent - y * size, 256, 256
    )
    with rasterio.open(storage_for(artifact.storage_key).raster_location(artifact.storage_key)) as src:
        with WarpedVRT(
            src,
            crs="EPSG:3857",
            transform=transform,
            width=256,
            height=256,
            dtype="float32",
            nodata=np.nan,
            resampling=Resampling.nearest,
        ) as vrt:
            data = vrt.read()
    analysis = db.get(Analysis, artifact.analysis_id)
    stats = analysis.stats.get("bands", [analysis.stats])
    limits = [(s["percentiles"][0], s["percentiles"][3]) for s in stats if s.get("percentiles")]
    return Response(png_bytes(data, limits or None), media_type="image/png")


@app.get("/v1/artifacts/{artifact_id}/pixel", response_model=PixelView)
def pixel(artifact_id: UUID, lon: float, lat: float, user=Depends(current_user), db=Depends(get_db)):
    from pyproj import Transformer

    artifact = artifact_owned(db, user, artifact_id)
    if artifact.artifact_type != "cog" or not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise HTTPException(400, "INVALID_PIXEL_REQUEST")
    with rasterio.open(storage_for(artifact.storage_key).raster_location(artifact.storage_key)) as src:
        x, y = Transformer.from_crs(4326, src.crs, always_xy=True).transform(lon, lat)
        if not (src.bounds.left <= x <= src.bounds.right and src.bounds.bottom <= y <= src.bounds.top):
            raise HTTPException(400, "PIXEL_OUTSIDE_AOI")
        values = next(src.sample([(x, y)]))
    return {"values": [float(v) if np.isfinite(v) else None for v in values], "lon": lon, "lat": lat}
