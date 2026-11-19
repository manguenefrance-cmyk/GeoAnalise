from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "production"
    database_url: str = "sqlite:///./data/arcambe.db"
    data_dir: Path = Path("data")
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    firebase_project_id: str = ""
    stac_url: str = "https://stac.dataspace.copernicus.eu/v1"
    stac_collection: str = "sentinel-2-l2a"
    raster_allowed_hosts: str = (
        "sentinel-cogs.s3.us-west-2.amazonaws.com,e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com,landsateuwest.blob.core.windows.net"
    )
    daily_job_limit: int = 5
    daily_attempt_limit: int = 20
    concurrent_job_limit: int = 1
    max_aoi_km2: float = 100
    max_pixels: int = 2_000_000
    download_secret: str = ""
    storage_backend: Literal["local", "gcs"] = "local"
    gcs_bucket: str = ""
    gcs_signer_email: str = ""
    max_artifact_bytes: int = 150_000_000

    def validate_runtime(self):
        if self.app_env not in ("production", "test"):
            raise RuntimeError("APP_ENV must be production or explicit test")
        if self.app_env == "production":
            if not self.database_url.startswith("postgresql") or not self.firebase_project_id:
                raise RuntimeError("Production requires PostgreSQL and FIREBASE_PROJECT_ID")
            if len(self.download_secret) < 32:
                raise RuntimeError("Production requires a random DOWNLOAD_SECRET of 32+ characters")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.storage_backend == "gcs" and not self.gcs_bucket:
            raise RuntimeError("GCS storage requires GCS_BUCKET")


settings = Settings()
