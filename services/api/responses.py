"""Response contracts used by FastAPI and the generated TypeScript client types."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JobState = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class Output(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ErrorDetail(Output):
    code: str
    message: str
    request_id: str
    details: list[dict] | None = None


class ErrorEnvelope(Output):
    error: ErrorDetail


class HealthView(Output):
    status: Literal["ok"]
    version: str
    mode: Literal["production", "test"]


class DashboardView(Output):
    project_count: int
    completed_analyses: int
    active_jobs: int


class ReadyView(Output):
    status: Literal["ready"]


class ProfileView(Output):
    id: UUID
    firebase_uid: str
    email: str
    display_name: str
    locale: Literal["en", "pt"]
    organization_id: UUID
    created_at: str


class ProjectView(Output):
    id: UUID
    organization_id: UUID
    name: str
    description: str
    status: Literal["active", "archived", "deleted"]
    created_at: str
    updated_at: str


class AreaView(Output):
    id: UUID
    project_id: UUID
    name: str
    geometry: dict
    area_km2: float
    source: str
    created_at: str


class SceneView(Output):
    sensor: Literal["sentinel-2", "landsat-8-9"]
    id: UUID
    stac_item_id: str
    sample: bool
    geometry: dict | None
    properties: dict
    collection: str | None
    asset_keys: list[str]


class SearchView(Output):
    scenes: list[SceneView]
    has_more: bool
    provider: str
    cloud_metric: Literal["scene_level"]
    pixel_access: str


class IndexView(Output):
    id: str
    title: str
    title_pt: str
    notes: str
    notes_pt: str
    category: str
    formula: str
    bands: list[str]
    native_output_resolution_m: Literal[10, 20, 30, 60]
    input: Literal["calibrated_surface_reflectance"]
    algorithm_version: str
    required: bool
    constants: dict[str, float] = Field(default_factory=dict)


class CatalogView(Output):
    sensor: Literal["sentinel-2", "landsat-8-9"]
    native_bands: dict[str, str]
    version: str
    indices: list[IndexView]
    bands: dict[str, int]


class ArtifactView(Output):
    id: UUID
    organization_id: UUID
    analysis_id: UUID
    artifact_type: str
    mime_type: str
    bytes: int
    checksum: str
    created_at: str


class JobView(Output):
    id: UUID
    organization_id: UUID
    analysis_id: UUID
    idempotency_key: str
    request_hash: str
    status: JobState
    attempt: int
    error_code: str | None
    cancel_requested: bool
    created_at: str
    started_at: str | None
    finished_at: str | None


class AnalysisView(Output):
    id: UUID
    organization_id: UUID
    project_id: UUID
    aoi_id: UUID
    scene_id: UUID | None
    operation_kind: Literal["index", "band_ratio", "temporal_diff", "pca", "composite"]
    operation_id: str
    params: dict
    input_analysis_ids: list[UUID]
    provenance: dict
    stats: dict
    status: JobState
    created_at: str
    job: JobView
    artifacts: list[ArtifactView]


class UsageView(Output):
    today: str
    reserved: int
    settled: int
    refunded: int
    daily_limit: int
    concurrent_limit: int
    max_aoi_km2: float
    billing_enabled: Literal[False]
    attempted: int
    daily_attempt_limit: int


class DownloadView(Output):
    url: str
    expires_at: int


class PixelView(Output):
    values: list[float | None]
    lon: float
    lat: float


class DeletedView(Output):
    status: Literal["deleted"]
    artifact_retention_days: int | None = None


class SeedView(Output):
    project: ProjectView
    scenes: list[SceneView]
    sample: Literal[True]


class DeletionRequestView(Output):
    status: Literal["none", "requested", "cancelled"]
    fulfillment: Literal["manual_review"] = "manual_review"
    request_id: UUID | None = None
    requested_at: str | None = None
