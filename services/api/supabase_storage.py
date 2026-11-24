"""Private Supabase object storage; service credentials never leave this server."""

import hashlib
import re
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse

import httpx

from .config import settings
from .storage import StorageError, object_key


class SupabaseStorage:
    def __init__(self, url, service_key, bucket, client=None):
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or not re.fullmatch(r"[a-z0-9-]+\.supabase\.co", parsed.netloc)
            or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", bucket)
            or not service_key
        ):
            raise StorageError("INVALID_SUPABASE_CONFIGURATION")
        self.origin = f"https://{parsed.netloc}"
        self.host, self.bucket = parsed.netloc, bucket
        self.client = client or httpx.Client(timeout=120, follow_redirects=False)
        self.headers = {"apikey": service_key}
        # Opaque secret keys are API keys, not JWTs. The gateway supplies the server role.
        if not service_key.startswith("sb_secret_"):
            self.headers["Authorization"] = f"Bearer {service_key}"

    def request(self, method, path, **kwargs):
        try:
            return self.client.request(
                method, self.origin + "/storage/v1" + path,
                headers={**self.headers, **kwargs.pop("headers", {})}, **kwargs,
            )
        except httpx.HTTPError:
            raise StorageError("SUPABASE_STORAGE_UNAVAILABLE") from None

    def private_bucket(self):
        response = self.request("GET", f"/bucket/{self.bucket}")
        try:
            bucket = response.json()
            if response.status_code != 200 or bucket.get("id") != self.bucket:
                raise StorageError("SUPABASE_BUCKET_ACCESS_FAILED")
            if bucket.get("public") is not False:
                raise StorageError("SUPABASE_PRIVATE_BUCKET_REQUIRED")
        except StorageError:
            raise
        except (ValueError, AttributeError):
            raise StorageError("SUPABASE_BUCKET_ACCESS_FAILED") from None

    def key(self, location):
        parsed = urlparse(location)
        prefix = f"/{self.bucket}/"
        if (
            parsed.scheme != "supabase" or parsed.netloc != self.host
            or not parsed.path.startswith(prefix) or parsed.query or parsed.fragment
        ):
            raise StorageError("INVALID_STORAGE_KEY")
        return object_key(parsed.path[len(prefix):])

    def object_path(self, location):
        return f"/{self.bucket}/{quote(self.key(location), safe='/')}"

    def chunks(self, location, limit):
        # Streaming enforces the limit even if Content-Length is missing or dishonest.
        try:
            with self.client.stream(
                "GET", self.origin + "/storage/v1/object/authenticated" + self.object_path(location),
                headers=self.headers,
            ) as response:
                if response.status_code == 404:
                    raise StorageError("ARTIFACT_EXPIRED")
                if response.status_code != 200:
                    raise StorageError("SUPABASE_READ_FAILED")
                size = 0
                for chunk in response.iter_bytes(64 * 1024):
                    size += len(chunk)
                    if size > limit:
                        raise StorageError("ARTIFACT_SIZE_LIMIT")
                    yield chunk
        except httpx.HTTPError:
            raise StorageError("SUPABASE_READ_FAILED") from None

    def publish(self, path, organization_id, analysis_id, mime):
        path = Path(path)
        if not path.is_file() or path.stat().st_size > settings.max_artifact_bytes:
            raise StorageError("ARTIFACT_SIZE_LIMIT")
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        key = object_key(f"artifacts/{organization_id}/{analysis_id}/{digest}-{path.name}")
        location = f"supabase://{self.host}/{self.bucket}/{key}"
        self.private_bucket()
        with path.open("rb") as source:
            response = self.request(
                "POST", "/object" + self.object_path(location), content=source,
                headers={
                    "content-type": mime, "content-length": str(path.stat().st_size),
                    "x-upsert": "false", "cache-control": "private, no-store",
                },
            )
        if response.status_code not in (200, 201):
            try:
                error = response.json()
            except ValueError:
                error = {}
            if not isinstance(error, dict) or error.get("error") != "Duplicate":
                raise StorageError("SUPABASE_UPLOAD_FAILED")
            existing = hashlib.sha256()
            for chunk in self.chunks(location, path.stat().st_size):
                existing.update(chunk)
            if existing.hexdigest() != digest:
                raise StorageError("ARTIFACT_CONTENT_CONFLICT")
        return location

    def signed_url(self, location, ttl=300, filename=None):
        if not 1 <= ttl <= 300:
            raise StorageError("INVALID_DOWNLOAD_TTL")
        self.private_bucket()
        path = "/object/sign" + self.object_path(location)
        response = self.request("POST", path, json={"expiresIn": ttl})
        try:
            signed = response.json()["signedURL"]
            parsed = urlparse(signed)
            if (
                response.status_code != 200 or parsed.scheme or parsed.netloc
                or parsed.path != path or parsed.fragment or not parsed.query
            ):
                raise StorageError("INVALID_SUPABASE_DOWNLOAD_URL")
        except StorageError:
            raise
        except (ValueError, KeyError, TypeError):
            raise StorageError("SUPABASE_SIGNING_FAILED") from None
        result = self.origin + "/storage/v1" + signed
        if filename:
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", filename)[:180]
            result += "&" + urlencode({"download": safe})
        return result

    def raster_location(self, location):
        return self.signed_url(location)

    def preview(self, location):
        self.private_bucket()
        try:
            return b"".join(self.chunks(location, 5_000_000))
        except StorageError as exc:
            if str(exc) == "ARTIFACT_SIZE_LIMIT":
                raise StorageError("PREVIEW_SIZE_LIMIT") from None
            raise

    def delete(self, location):
        key = self.key(location)
        response = self.request("DELETE", f"/object/{self.bucket}", json={"prefixes": [key]})
        if response.status_code not in (200, 404):
            raise StorageError("SUPABASE_DELETE_FAILED")
