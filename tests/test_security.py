from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from services.api.config import Settings, settings
from services.api.main import app
from services.processor.stac import ProviderError, search_cached


def test_production_cannot_use_test_auth(client):
    with patch.object(settings, "app_env", "production"):
        assert (
            client.get("/v1/projects", headers={"Authorization": "Bearer test:intruder"}).status_code == 401
        )
        assert (
            client.post("/v1/test/seed", headers={"Authorization": "Bearer test:intruder"}).status_code == 401
        )


def test_production_requires_explicit_cloud_config():
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        Settings(app_env="production", database_url="sqlite://", firebase_project_id="").validate_runtime()


def test_concurrent_quota_reservation(client, headers, seeded):
    payload = {
        "project_id": seeded["project"]["id"],
        "aoi_id": seeded["aoi"]["id"],
        "scene_id": seeded["scenes"][0]["id"],
        "operation_kind": "index",
        "operation_id": "NDVI",
    }
    # Profile already exists: race only the expensive reservation itself.
    client.get("/v1/me", headers=headers)

    def submit(i):
        with TestClient(app) as c:
            return c.post(
                "/v1/analyses", json=payload, headers={**headers, "Idempotency-Key": f"parallel-request-{i}"}
            ).status_code

    with ThreadPoolExecutor(max_workers=4) as executor:
        statuses = list(executor.map(submit, range(4)))
    assert statuses.count(202) == 1
    assert statuses.count(429) == 3
    assert client.get("/v1/usage", headers=headers).json()["reserved"] == 1


def test_invalid_bands_rejected_before_reservation(client, headers, seeded):
    response = client.post(
        "/v1/analyses",
        json={
            "project_id": seeded["project"]["id"],
            "aoi_id": seeded["aoi"]["id"],
            "scene_id": seeded["scenes"][0]["id"],
            "operation_kind": "band_ratio",
            "operation_id": "BAND_RATIO",
            "params": {"numerator": "B10"},
        },
        headers={**headers, "Idempotency-Key": "invalid-band-test"},
    )
    assert response.status_code == 400
    assert client.get("/v1/usage", headers=headers).json()["reserved"] == 0


def test_viewer_cannot_mutate_and_removed_member_cannot_read(client, headers, seeded):
    from services.api.db import Membership, Session
    from sqlalchemy import select

    with Session() as db:
        member = db.scalar(select(Membership))
        member.role = "viewer"
        db.commit()
    assert client.get(f"/v1/projects/{seeded['project']['id']}", headers=headers).status_code == 200
    assert (
        client.patch(
            f"/v1/projects/{seeded['project']['id']}", json={"name": "forbidden"}, headers=headers
        ).status_code
        == 403
    )
    with Session() as db:
        db.delete(db.scalar(select(Membership)))
        db.commit()
    assert client.get("/v1/projects", headers=headers).status_code == 403


def test_provider_failure_is_actionable(client, headers, seeded):
    search_cached.cache_clear()
    with patch("services.api.main.search_cached", side_effect=ProviderError("STAC_PROVIDER_UNAVAILABLE")):
        response = client.post(
            "/v1/satellite/search",
            json={"aoi_id": seeded["aoi"]["id"], "date_start": "2025-01-01", "date_end": "2025-02-01"},
            headers=headers,
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "STAC_PROVIDER_UNAVAILABLE"


def test_provider_adapter_connection_failure():
    from unittest.mock import MagicMock

    fake = MagicMock()
    fake.__enter__.return_value.post.side_effect = httpx.ConnectError("unavailable")
    search_cached.cache_clear()
    with patch("services.processor.stac.httpx.Client", return_value=fake):
        with pytest.raises(ProviderError, match="STAC_PROVIDER_UNAVAILABLE"):
            search_cached('{"type":"Polygon","coordinates":[]}', "2025-01-01", "2025-02-01", 20, 1, 0)


def test_valid_shapefile_import(client, headers, seeded):
    import zipfile
    import shapefile
    from pyproj import CRS

    shp, shx, dbf = BytesIO(), BytesIO(), BytesIO()
    with shapefile.Writer(shp=shp, shx=shx, dbf=dbf) as writer:
        writer.field("name", "C")
        writer.poly(
            [[[32.57, -25.95], [32.57, -25.945], [32.575, -25.945], [32.575, -25.95], [32.57, -25.95]]]
        )
        writer.record("test")
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for ext, content in [
            ("shp", shp.getvalue()),
            ("shx", shx.getvalue()),
            ("dbf", dbf.getvalue()),
            ("prj", CRS.from_epsg(4326).to_wkt().encode()),
        ]:
            archive.writestr(f"area.{ext}", content)
    response = client.post(
        f"/v1/projects/{seeded['project']['id']}/aois/import",
        files={"file": ("area.zip", stream.getvalue(), "application/zip")},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert 0.2 < response.json()["area_km2"] < 0.4
