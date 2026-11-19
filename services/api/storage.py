"""Private artifact storage. Database authorization always precedes these operations."""

import hashlib
import re
from datetime import timedelta
from functools import lru_cache
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from .config import settings


class StorageError(ValueError):
    pass


def object_key(value):
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or ":" in value
        or any(part in ("", ".") for part in value.split("/"))
        or not value.startswith("artifacts/")
    ):
        raise StorageError("INVALID_STORAGE_KEY")
    return value


class LocalStorage:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def path(self, key):
        path = (self.root / object_key(key)).resolve()
        if not path.is_relative_to(self.root / "artifacts"):
            raise StorageError("INVALID_STORAGE_KEY")
        return path

    def publish(self, path, organization_id, analysis_id, mime):
        path = Path(path).resolve()
        key = object_key(path.relative_to(self.root).as_posix())
        if not path.is_file() or path.stat().st_size > settings.max_artifact_bytes:
            raise StorageError("ARTIFACT_SIZE_LIMIT")
        return key

    def raster_location(self, key):
        path = self.path(key)
        if not path.is_file():
            raise StorageError("ARTIFACT_EXPIRED")
        return str(path)

    def preview(self, key):
        path = self.path(key)
        if not path.is_file():
            raise StorageError("ARTIFACT_EXPIRED")
        if path.stat().st_size > 5_000_000:
            raise StorageError("PREVIEW_SIZE_LIMIT")
        return path.read_bytes()

    def delete(self, key):
        self.path(key).unlink(missing_ok=True)


class GCSStorage:
    def __init__(self, bucket_name, signer_email="", client=None, credentials=None):
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket_name):
            raise StorageError("INVALID_GCS_BUCKET")
        self.bucket_name, self.signer_email = bucket_name, signer_email
        try:
            if client is None:
                import google.auth
                from google.cloud import storage

                credentials, project = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                client = storage.Client(project=project, credentials=credentials)
            self.client, self.credentials = client, credentials
            self.bucket = client.get_bucket(bucket_name, timeout=20)
            iam = self.bucket.iam_configuration
            if not iam.uniform_bucket_level_access_enabled or iam.public_access_prevention != "enforced":
                raise StorageError("GCS_PRIVATE_BUCKET_REQUIRED")
        except StorageError:
            raise
        except Exception:
            raise StorageError("GCS_CONFIGURATION_OR_ACCESS_FAILED") from None

    def key(self, location):
        url = urlparse(location)
        if url.scheme != "gs" or url.netloc != self.bucket_name or url.query or url.fragment:
            raise StorageError("INVALID_STORAGE_KEY")
        return object_key(url.path.lstrip("/"))

    def publish(self, path, organization_id, analysis_id, mime):
        from google.api_core.exceptions import PreconditionFailed

        path = Path(path)
        if not path.is_file() or path.stat().st_size > settings.max_artifact_bytes:
            raise StorageError("ARTIFACT_SIZE_LIMIT")
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        key = object_key(f"artifacts/{organization_id}/{analysis_id}/{digest}-{path.name}")
        blob = self.bucket.blob(key)
        blob.metadata = {"sha256": digest}
        blob.cache_control = "private, no-store"
        try:
            blob.upload_from_filename(
                str(path), content_type=mime, if_generation_match=0, timeout=120, checksum="crc32c"
            )
        except PreconditionFailed:
            blob.reload(timeout=20)
            if (blob.metadata or {}).get("sha256") != digest or blob.size != path.stat().st_size:
                raise StorageError("ARTIFACT_CONTENT_CONFLICT") from None
        except Exception:
            raise StorageError("GCS_UPLOAD_FAILED") from None
        return f"gs://{self.bucket_name}/{key}"

    def signed_url(self, key, ttl=300, filename=None):
        if not 1 <= ttl <= 300:
            raise StorageError("INVALID_DOWNLOAD_TTL")
        blob = self.bucket.blob(self.key(key))
        options = {"version": "v4", "expiration": timedelta(seconds=ttl), "method": "GET"}
        if filename:
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", filename)[:180]
            options["response_disposition"] = f'attachment; filename="{safe}"'
        try:
            if self.signer_email:
                from google.auth.transport.requests import Request

                if not self.credentials.valid:
                    self.credentials.refresh(Request())
                options.update(service_account_email=self.signer_email, access_token=self.credentials.token)
            url = blob.generate_signed_url(**options)
        except Exception:
            raise StorageError("GCS_SIGNING_FAILED_CHECK_SIGNBLOB_PERMISSION") from None
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "storage.googleapis.com":
            raise StorageError("INVALID_GCS_DOWNLOAD_HOST")
        return url

    def raster_location(self, key):
        return self.signed_url(key)

    def preview(self, key):
        blob = self.bucket.blob(self.key(key))
        try:
            blob.reload(timeout=20)
            if blob.size is None or blob.size > 5_000_000:
                raise StorageError("PREVIEW_SIZE_LIMIT")
            return blob.download_as_bytes(timeout=30, if_generation_match=blob.generation)
        except StorageError:
            raise
        except Exception:
            raise StorageError("GCS_READ_FAILED") from None

    def delete(self, key):
        from google.api_core.exceptions import NotFound

        try:
            self.bucket.blob(self.key(key)).delete(timeout=30)
        except NotFound:
            pass
        except Exception:
            raise StorageError("GCS_DELETE_FAILED") from None


@lru_cache(maxsize=4)
def _gcs(bucket, signer):
    return GCSStorage(bucket, signer)


def storage_for(key=None):
    if key is not None:
        if key.startswith("gs://"):
            if not settings.gcs_bucket:
                raise StorageError("GCS_CONFIGURATION_OR_ACCESS_FAILED")
            return _gcs(settings.gcs_bucket, settings.gcs_signer_email)
        return LocalStorage(settings.data_dir)
    if settings.storage_backend == "gcs":
        return _gcs(settings.gcs_bucket, settings.gcs_signer_email)
    return LocalStorage(settings.data_dir)
