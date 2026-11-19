from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from google.api_core.exceptions import PreconditionFailed

from services.api.config import settings
from services.api.storage import GCSStorage, LocalStorage, StorageError, object_key


@pytest.mark.parametrize(
    "key",
    [
        "../private",
        "artifacts/../../x",
        "/artifacts/x",
        "C:\\artifacts\\x",
        "artifacts//x",
        "artifacts/./x",
        "data/secret",
    ],
)
def test_untrusted_storage_paths_refused(key):
    with pytest.raises(StorageError):
        object_key(key)


def test_local_storage_roundtrip_and_symlink_boundary(tmp_path):
    directory = tmp_path / "artifacts" / "analysis"
    directory.mkdir(parents=True)
    product = directory / "preview.png"
    product.write_bytes(b"raster-preview")
    store = LocalStorage(tmp_path)
    key = store.publish(product, "org", "analysis", "image/png")
    assert key == "artifacts/analysis/preview.png"
    assert store.preview(key) == b"raster-preview"
    assert store.raster_location(key) == str(product.resolve())
    store.delete(key)
    with pytest.raises(StorageError, match="ARTIFACT_EXPIRED"):
        store.raster_location(key)


def fake_store():
    client = MagicMock()
    bucket = client.get_bucket.return_value
    bucket.iam_configuration.uniform_bucket_level_access_enabled = True
    bucket.iam_configuration.public_access_prevention = "enforced"
    credentials = MagicMock(valid=True, token="temporary-token")
    return GCSStorage("private-arcambe", "signer@example.test", client, credentials), bucket


@pytest.mark.parametrize("uniform,pap", [(False, "enforced"), (True, "inherited")])
def test_gcs_refuses_bucket_without_explicit_private_policy(uniform, pap):
    client = MagicMock()
    client.get_bucket.return_value.iam_configuration.uniform_bucket_level_access_enabled = uniform
    client.get_bucket.return_value.iam_configuration.public_access_prevention = pap
    with pytest.raises(StorageError, match="GCS_PRIVATE_BUCKET_REQUIRED"):
        GCSStorage("private-arcambe", client=client)


def test_gcs_publish_is_immutable_and_retry_safe(tmp_path):
    store, bucket = fake_store()
    path = tmp_path / "result.tif"
    path.write_bytes(b"geotiff-content")
    key = store.publish(path, "tenant-A", "analysis-A", "image/tiff")
    blob = bucket.blob.return_value
    assert key.startswith("gs://private-arcambe/artifacts/tenant-A/analysis-A/")
    assert key.endswith("-result.tif")
    assert blob.upload_from_filename.call_args.kwargs["if_generation_match"] == 0
    assert blob.cache_control == "private, no-store"
    blob.upload_from_filename.side_effect = PreconditionFailed("already exists")
    blob.size = path.stat().st_size
    assert store.publish(path, "tenant-A", "analysis-A", "image/tiff") == key
    blob.size = 1
    with pytest.raises(StorageError, match="ARTIFACT_CONTENT_CONFLICT"):
        store.publish(path, "tenant-A", "analysis-A", "image/tiff")


def test_gcs_signs_only_approved_object_and_short_ttl():
    store, bucket = fake_store()
    blob = bucket.blob.return_value
    blob.generate_signed_url.return_value = (
        "https://storage.googleapis.com/private-arcambe/artifacts/a/x.tif?signature=example"
    )
    location = "gs://private-arcambe/artifacts/a/x.tif"
    assert store.signed_url(location, ttl=120).startswith("https://storage.googleapis.com/")
    kwargs = blob.generate_signed_url.call_args.kwargs
    assert kwargs["expiration"] == timedelta(seconds=120)
    assert kwargs["version"] == "v4"
    assert kwargs["service_account_email"] == "signer@example.test"
    assert kwargs["access_token"] == "temporary-token"
    for bad in [
        "gs://other-bucket/artifacts/a/x.tif",
        "https://example.test/x",
        "gs://private-arcambe/../private",
    ]:
        with pytest.raises(StorageError):
            store.signed_url(bad)
    with pytest.raises(StorageError, match="INVALID_DOWNLOAD_TTL"):
        store.signed_url(location, ttl=301)


def test_storage_failures_do_not_expose_credentials():
    store, bucket = fake_store()
    bucket.blob.return_value.generate_signed_url.side_effect = RuntimeError("secret=do-not-expose")
    with pytest.raises(StorageError, match="GCS_SIGNING_FAILED") as error:
        store.signed_url("gs://private-arcambe/artifacts/a/x.tif")
    assert "secret" not in str(error.value)


def test_gcs_preview_uses_generation_and_bounded_size():
    store, bucket = fake_store()
    blob = bucket.blob.return_value
    blob.size = 100
    blob.generation = 7
    blob.download_as_bytes.return_value = b"preview"
    location = "gs://private-arcambe/artifacts/a/preview.png"
    assert store.preview(location) == b"preview"
    assert blob.download_as_bytes.call_args.kwargs["if_generation_match"] == 7
    blob.size = 5_000_001
    with pytest.raises(StorageError, match="PREVIEW_SIZE_LIMIT"):
        store.preview(location)


def test_artifact_size_enforced_before_upload(tmp_path):
    store, bucket = fake_store()
    path = tmp_path / "large.tif"
    path.write_bytes(b"123456")
    with patch.object(settings, "max_artifact_bytes", 5):
        with pytest.raises(StorageError, match="ARTIFACT_SIZE_LIMIT"):
            store.publish(path, "org", "analysis", "image/tiff")
    bucket.blob.return_value.upload_from_filename.assert_not_called()
