from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class ProjectCreate(Strict):
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=2000)


class ProjectPatch(Strict):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    status: Literal["active", "archived"] | None = None


class ProfilePatch(Strict):
    display_name: str | None = Field(default=None, max_length=180)
    locale: Literal["en", "pt"] | None = None


class AreaCreate(Strict):
    name: str = Field(min_length=1, max_length=180)
    geometry: dict


class SceneSearch(Strict):
    aoi_id: UUID
    date_start: date
    date_end: date
    max_cloud_cover: float = Field(default=20, ge=0, le=100)
    limit: int = Field(default=20, ge=1, le=100)
    sensor: Literal["sentinel-2", "landsat-8-9"] = "sentinel-2"
    provider: Literal["copernicus", "earthsearch_c1", "planetary_computer"] | None = None

    @model_validator(mode="after")
    def match_provider(self):
        self.provider = self.provider or (
            "planetary_computer" if self.sensor == "landsat-8-9" else "copernicus"
        )
        if (self.sensor == "landsat-8-9") != (self.provider == "planetary_computer"):
            raise ValueError("SENSOR_PROVIDER_MISMATCH")
        return self


class AnalysisCreate(Strict):
    project_id: UUID
    aoi_id: UUID
    scene_id: UUID | None = None
    operation_kind: Literal["index", "band_ratio", "temporal_diff", "pca", "composite"]
    operation_id: str = Field(min_length=1, max_length=50)
    input_analysis_ids: list[UUID] = Field(default_factory=list, max_length=2)
    params: dict = Field(default_factory=dict)
