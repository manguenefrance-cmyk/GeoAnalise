from threading import Event
from unittest.mock import patch

import pytest
import yaml

from services.api.config import settings
from services.api.embedded_worker import EmbeddedWorker
from services.api.hosted import validate_hosted


def test_embedded_worker_recovers_after_temporary_database_failure(caplog):
    calls = []
    succeeded = Event()

    def work():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("password=never-log-this")
        succeeded.set()

    worker = EmbeddedWorker(work, idle_seconds=0.01)
    worker.start()
    assert succeeded.wait(2)
    worker.stop()
    assert not worker.thread.is_alive()
    assert "queue_poll_failed" in caplog.text
    assert "password" not in caplog.text


def test_embedded_worker_shutdown_interrupts_idle_wait():
    checked = Event()
    worker = EmbeddedWorker(lambda: checked.set(), idle_seconds=60)
    worker.start()
    assert checked.wait(2)
    worker.stop()
    assert not worker.thread.is_alive()


def test_hosted_profile_refuses_test_auth_local_storage_and_excessive_limits():
    with pytest.raises(RuntimeError, match="production authentication"):
        validate_hosted()
    values = dict(
        app_env="production", database_url="postgresql+psycopg://example",
        database_schema="arcambe", worker_embedded=True, storage_backend="supabase",
        firebase_project_id="arcambe-geoanalytics", download_secret="x" * 32,
        supabase_url="https://project.supabase.co", max_pixels=250000,
        max_artifact_bytes=50000000,
    )
    from pydantic import SecretStr

    values["supabase_service_key"] = SecretStr("server-only-key")
    with patch.multiple(settings, **values):
        validate_hosted()
        with patch.object(settings, "database_schema", "public"):
            with pytest.raises(RuntimeError, match="DATABASE_SCHEMA"):
                validate_hosted()
        with patch.object(settings, "worker_embedded", False):
            with pytest.raises(RuntimeError, match="WORKER_EMBEDDED"):
                validate_hosted()
        with patch.object(settings, "max_pixels", 2000000):
            with pytest.raises(RuntimeError, match="limits exceeded"):
                validate_hosted()


def test_hosted_blueprint_has_no_paid_resources_and_pins_production():
    with open("render.yaml", encoding="utf-8") as source:
        blueprint = yaml.safe_load(source)
    assert set(blueprint) == {"services"}
    assert len(blueprint["services"]) == 1
    service = blueprint["services"][0]
    assert service["type"] == "web" and service["plan"] == "free"
    assert "disk" not in service
    env = {item["key"]: item for item in service["envVars"]}
    assert env["APP_ENV"]["value"] == "production"
    assert env["STORAGE_BACKEND"]["value"] == "supabase"
    assert env["DATABASE_URL"]["sync"] is False
    assert env["SUPABASE_SERVICE_KEY"]["sync"] is False
