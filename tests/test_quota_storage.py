from unittest.mock import patch

from sqlalchemy import select

from services.api.config import settings
from services.api.db import Artifact, Job, Session
from services.api.jobs import work_once
from services.api.storage import LocalStorage, StorageError


def enqueue(client, headers, seed, key):
    return client.post(
        "/v1/analyses",
        json={
            "project_id": seed["project"]["id"],
            "aoi_id": seed["aoi"]["id"],
            "scene_id": seed["scenes"][0]["id"],
            "operation_kind": "index",
            "operation_id": "NDVI",
        },
        headers={**headers, "Idempotency-Key": key},
    )


def test_refunds_do_not_allow_unlimited_job_attempts(client, headers, seeded):
    with patch.object(settings, "daily_attempt_limit", 1):
        first = enqueue(client, headers, seeded, "first-attempt-test").json()
        assert client.post(f"/v1/jobs/{first['job']['id']}/cancel", headers=headers).status_code == 202
        result = enqueue(client, headers, seeded, "second-attempt-test")
        assert result.status_code == 429
        assert result.json()["error"]["code"] == "DAILY_ATTEMPT_LIMIT"
        usage = client.get("/v1/usage", headers=headers).json()
        assert usage["refunded"] == 1 and usage["attempted"] == 1


def test_cancellation_during_upload_cleans_unpublished_products(client, headers, seeded):
    queued = enqueue(client, headers, seeded, "upload-cancellation-test").json()
    keys = []

    class CancellingStorage(LocalStorage):
        def publish(self, *args):
            key = super().publish(*args)
            keys.append(key)
            if len(keys) == 1:
                with Session() as db:
                    db.get(Job, queued["job"]["id"]).cancel_requested = True
                    db.commit()
            return key

    store = CancellingStorage(settings.data_dir)
    with patch("services.api.jobs.storage_for", return_value=store):
        work_once()
    result = client.get(f"/v1/analyses/{queued['id']}", headers=headers).json()
    assert result["status"] == "cancelled" and not result["artifacts"]
    assert len(keys) == 7
    assert all(not store.path(key).exists() for key in keys)


def test_partial_upload_failure_cleans_uploaded_keys_and_refunds(client, headers, seeded):
    queued = enqueue(client, headers, seeded, "partial-upload-failure").json()
    keys = []

    class FailingStorage(LocalStorage):
        def publish(self, *args):
            if keys:
                raise StorageError("GCS_UPLOAD_FAILED")
            key = super().publish(*args)
            keys.append(key)
            return key

    store = FailingStorage(settings.data_dir)
    with patch("services.api.jobs.storage_for", return_value=store):
        work_once()
    result = client.get(f"/v1/analyses/{queued['id']}", headers=headers).json()
    assert result["status"] == "failed" and result["job"]["error_code"] == "GCS_UPLOAD_FAILED"
    assert all(not store.path(key).exists() for key in keys)
    with Session() as db:
        assert not db.scalar(select(Artifact.id).where(Artifact.analysis_id == queued["id"]))
    assert client.get("/v1/usage", headers=headers).json()["refunded"] == 1
