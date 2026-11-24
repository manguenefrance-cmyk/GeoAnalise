import json
from unittest.mock import patch

import httpx
import pytest
from pydantic import SecretStr

from services.api.config import settings
from services.api.storage import StorageError, storage_for, _supabase
from services.api.supabase_storage import SupabaseStorage

ORIGIN = "https://project-test.supabase.co"
BUCKET = "arcambe-artifacts"


class StorageServer:
    def __init__(self):
        self.objects = {}
        self.public = False
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        assert request.headers["apikey"] == "server-only-secret"
        assert request.headers["authorization"] == "Bearer server-only-secret"
        path = request.url.path.removeprefix("/storage/v1")
        if path == f"/bucket/{BUCKET}":
            return httpx.Response(200, json={"id": BUCKET, "public": self.public})
        if request.method == "POST" and path.startswith("/object/sign/"):
            assert 1 <= json.loads(request.content)["expiresIn"] <= 300
            return httpx.Response(200, json={"signedURL": path + "?token=short-lived"})
        if request.method == "POST":
            key = path.removeprefix(f"/object/{BUCKET}/")
            assert request.headers["x-upsert"] == "false"
            assert int(request.headers["content-length"]) == len(request.content)
            if key in self.objects:
                return httpx.Response(409, json={"error": "Duplicate"})
            self.objects[key] = request.content
            return httpx.Response(200, json={"Key": key})
        if request.method == "GET":
            key = path.removeprefix(f"/object/authenticated/{BUCKET}/")
            if key not in self.objects:
                return httpx.Response(404)
            return httpx.Response(200, content=self.objects[key])
        if request.method == "DELETE":
            for key in json.loads(request.content)["prefixes"]:
                self.objects.pop(key, None)
            return httpx.Response(200, json=[])
        raise AssertionError(f"Unexpected request: {request.method} {path}")

    def store(self):
        return SupabaseStorage(
            ORIGIN, "server-only-secret", BUCKET,
            httpx.Client(transport=httpx.MockTransport(self.handle)),
        )


def test_remote_objects_survive_store_restart_and_upload_retry(tmp_path):
    server = StorageServer()
    file = tmp_path / "preview.png"
    file.write_bytes(b"persisted-geospatial-product")
    first = server.store()
    location = first.publish(file, "tenant-A", "analysis-A", "image/png")
    assert location.startswith(f"supabase://project-test.supabase.co/{BUCKET}/artifacts/tenant-A/")
    assert first.publish(file, "tenant-A", "analysis-A", "image/png") == location
    assert len(server.objects) == 1
    file.unlink()
    restarted = server.store()
    assert restarted.preview(location) == b"persisted-geospatial-product"
    signed = restarted.signed_url(location, ttl=120, filename='result".png')
    assert signed.startswith(ORIGIN + "/storage/v1/object/sign/")
    assert signed.endswith("&download=result_.png")
    assert "server-only-secret" not in signed
    restarted.delete(location)
    with pytest.raises(StorageError, match="ARTIFACT_EXPIRED"):
        restarted.preview(location)


def test_modern_secret_key_is_not_sent_as_a_user_jwt():
    def handler(request):
        assert request.headers["apikey"] == "sb_secret_server-only"
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"id": BUCKET, "public": False})

    store = SupabaseStorage(
        ORIGIN, "sb_secret_server-only", BUCKET,
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    store.private_bucket()


def test_supabase_never_overwrites_conflicting_content(tmp_path):
    server = StorageServer()
    store = server.store()
    file = tmp_path / "result.tif"
    file.write_bytes(b"correct")
    location = store.publish(file, "tenant-A", "analysis-A", "image/tiff")
    server.objects[store.key(location)] = b"wrong"
    with pytest.raises(StorageError, match="ARTIFACT_CONTENT_CONFLICT"):
        store.publish(file, "tenant-A", "analysis-A", "image/tiff")
    assert server.objects[store.key(location)] == b"wrong"


def test_supabase_refuses_public_bucket_on_upload_and_read(tmp_path):
    server = StorageServer()
    store = server.store()
    file = tmp_path / "preview.png"
    file.write_bytes(b"preview")
    location = store.publish(file, "A", "B", "image/png")
    server.public = True
    with pytest.raises(StorageError, match="SUPABASE_PRIVATE_BUCKET_REQUIRED"):
        store.preview(location)
    with pytest.raises(StorageError, match="SUPABASE_PRIVATE_BUCKET_REQUIRED"):
        store.signed_url(location)
    with pytest.raises(StorageError, match="SUPABASE_PRIVATE_BUCKET_REQUIRED"):
        store.publish(file, "A", "B", "image/png")


@pytest.mark.parametrize("url", [
    "http://project.supabase.co", "https://evil.test", "https://project.supabase.co@evil.test",
    "https://project.supabase.co/extra", "https://project.supabase.co?key=secret",
])
def test_only_project_https_endpoint_can_receive_server_secret(url):
    with pytest.raises(StorageError, match="INVALID_SUPABASE_CONFIGURATION"):
        SupabaseStorage(url, "secret", BUCKET)


@pytest.mark.parametrize("location", [
    "supabase://other.supabase.co/arcambe-artifacts/artifacts/a/file.tif",
    "supabase://project-test.supabase.co/another-bucket/artifacts/a/file.tif",
    "supabase://project-test.supabase.co/arcambe-artifacts/artifacts/../secret",
    "supabase://project-test.supabase.co/arcambe-artifacts/artifacts/a?secret=value",
    "https://evil.test/file",
])
def test_untrusted_stored_locations_are_refused(location):
    server = StorageServer()
    with pytest.raises(StorageError, match="INVALID_STORAGE_KEY"):
        server.store().key(location)
    assert not server.requests


def test_supabase_preview_and_upload_enforce_limits(tmp_path):
    server = StorageServer()
    store = server.store()
    file = tmp_path / "large.png"
    file.write_bytes(b"x" * 5_000_001)
    location = store.publish(file, "a", "b", "image/png")
    with pytest.raises(StorageError, match="PREVIEW_SIZE_LIMIT"):
        store.preview(location)
    with patch.object(settings, "max_artifact_bytes", 10):
        with pytest.raises(StorageError, match="ARTIFACT_SIZE_LIMIT"):
            store.publish(file, "a", "b", "image/png")
    with pytest.raises(StorageError, match="INVALID_DOWNLOAD_TTL"):
        store.signed_url(location, 301)


def test_provider_failure_and_redirect_do_not_leak_credentials():
    def failed(request):
        raise httpx.ConnectError("secret=server-only-secret")

    store = SupabaseStorage(
        ORIGIN, "server-only-secret", BUCKET, httpx.Client(transport=httpx.MockTransport(failed)),
    )
    with pytest.raises(StorageError, match="SUPABASE_STORAGE_UNAVAILABLE") as error:
        store.private_bucket()
    assert "secret" not in str(error.value)
    store = SupabaseStorage(
        ORIGIN, "server-only-secret", BUCKET,
        httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(302, headers={
            "location": "https://evil.test"
        }))),
    )
    with pytest.raises(StorageError, match="SUPABASE_BUCKET_ACCESS_FAILED"):
        store.private_bucket()


def test_storage_dispatch_uses_supabase_for_new_and_existing_locations():
    with patch.object(settings, "supabase_url", ORIGIN), patch.object(
        settings, "supabase_service_key", SecretStr("server-only-secret")
    ), patch.object(settings, "storage_backend", "supabase"):
        try:
            assert isinstance(storage_for(), SupabaseStorage)
            assert storage_for("supabase://project-test.supabase.co/arcambe-artifacts/artifacts/a/x") is storage_for()
        finally:
            _supabase.cache_clear()


def test_remote_job_publication_cleans_scratch_and_preserves_authorized_downloads(client, headers, seeded):
    from services.api.jobs import work_once

    response = client.post("/v1/analyses", headers={**headers, "Idempotency-Key": "hosted-storage-job"}, json={
        "project_id": seeded["project"]["id"], "aoi_id": seeded["aoi"]["id"],
        "scene_id": seeded["scenes"][0]["id"], "operation_kind": "index", "operation_id": "NDVI",
    })
    assert response.status_code == 202
    analysis_id = response.json()["id"]
    server = StorageServer()
    store = server.store()
    with patch("services.api.jobs.storage_for", return_value=store), patch.object(
        settings, "storage_backend", "supabase"
    ):
        assert work_once()
    result = client.get(f"/v1/analyses/{analysis_id}", headers=headers).json()
    assert result["status"] == "succeeded" and len(server.objects) == 7
    assert not (settings.data_dir / "artifacts" / analysis_id).exists()
    preview = next(a for a in result["artifacts"] if a["artifact_type"] == "preview")
    cog = next(a for a in result["artifacts"] if a["artifact_type"] == "cog")
    with patch("services.api.main.storage_for", return_value=server.store()):
        assert client.get(f"/v1/artifacts/{preview['id']}/preview.png", headers=headers).content.startswith(b"\x89PNG")
        assert client.get(f"/v1/artifacts/{cog['id']}/download", headers={
            "Authorization": "Bearer test:another-tenant"
        }).status_code == 404
        download = client.get(f"/v1/artifacts/{cog['id']}/download", headers=headers).json()
        redirected = client.get(download["url"], follow_redirects=False)
        assert redirected.status_code == 307
        assert redirected.headers["location"].startswith(ORIGIN + "/storage/v1/object/sign/")
