from datetime import date
from uuid import uuid4

import httpx
import numpy as np
import pytest

from services.api.config import settings
from services.api.db import Analysis, Scene, Session
from services.api.jobs import work_once
from services.api.schemas import SceneSearch
from services.processor.fixtures import FIXTURE_GEOMETRY, create_landsat_fixture
from services.processor.planetary import _tokens, sign_landsat_href
from services.processor.raster import landsat_valid_mask, read_scene, resolve_asset
from services.processor.registry import REGISTRY, calculate
from services.processor.sensors import LANDSAT, catalog_for, sensor_of


def test_default_sentinel_and_provider_validation():
    fields = dict(aoi_id=uuid4(), date_start=date(2025, 1, 1), date_end=date(2025, 2, 1))
    assert SceneSearch(**fields).sensor == "sentinel-2"
    assert SceneSearch(**fields, sensor=LANDSAT).provider == "planetary_computer"
    with pytest.raises(ValueError, match="SENSOR_PROVIDER_MISMATCH"):
        SceneSearch(**fields, sensor=LANDSAT, provider="earthsearch_c1")


def test_catalog_native_formulas_and_no_fabricated_red_edge(client, headers):
    s2 = client.get("/v1/indices", headers=headers).json()
    oli = client.get("/v1/indices?sensor=landsat-8-9", headers=headers).json()
    assert s2["sensor"] == "sentinel-2" and len(s2["indices"]) == 21
    assert len(oli["indices"]) == 19
    assert not {"CI_RE", "NDRE_B05"} & {i["id"] for i in oli["indices"]}
    ndvi = next(i for i in oli["indices"] if i["id"] == "NDVI")
    assert ndvi["bands"] == ["SR_B5", "SR_B4"]
    assert ndvi["formula"].replace(" ", "") == "(SR_B5-SR_B4)/(SR_B5+SR_B4)"
    assert {i["native_output_resolution_m"] for i in oli["indices"]} == {30}


@pytest.mark.parametrize("index_id", [i["id"] for i in catalog_for(LANDSAT)["indices"]])
def test_landsat_calibrated_indices_and_quality_grid(index_id):
    scene = create_landsat_fixture(settings.data_dir / "fixtures" / "landsat-math")
    selected = REGISTRY[index_id]["bands"]
    bands, grid, _, provenance = read_scene(scene, FIXTURE_GEOMETRY, selected, sample=True)
    result = calculate(index_id, bands)
    assert np.isfinite(result).any() and np.isnan(result).any()
    assert grid["transform"].a == 30
    assert provenance["sensor"] == LANDSAT and provenance["mask_scl"] == []
    assert provenance["sources"][selected[0]]["offset"] == -0.2
    if index_id == "NDVI":
        np.testing.assert_allclose(result[np.isfinite(result)], (0.5 - 0.1) / 0.6, atol=0.0001)
        clear = read_scene(scene, FIXTURE_GEOMETRY, selected, {"cloud_mask": False}, sample=True)
        assert np.isfinite(clear[0]["B08"]).sum() > np.isfinite(bands["B08"]).sum()
        assert np.isnan(clear[0]["B08"]).any()  # Fill and saturation still masked.


def test_qa_water_zero_valid_and_selected_saturation_only():
    pixel = np.array([0, 1, 2, 4, 8, 16, 32, 64, 128, 0, 0, 0], dtype="uint16")
    sat = np.array([0] * 9 + [1 << 0, 1 << 4, 1 << 11], dtype="uint16")
    mask = landsat_valid_mask(pixel, sat, list(range(6)), [3, 4, 11])
    assert mask.tolist() == [True, False, False, False, False, False, False, True, True, True, False, False]


def test_sensor_band_safety():
    scene = create_landsat_fixture(settings.data_dir / "fixtures" / "landsat-safety")
    assert resolve_asset(scene, "B08") is scene["assets"]["nir08"]
    with pytest.raises(ValueError, match="INVALID_BAND"):
        read_scene(scene, FIXTURE_GEOMETRY, ["B05"], sample=True)
    with pytest.raises(ValueError, match="INVALID_RESOLUTION"):
        read_scene(scene, FIXTURE_GEOMETRY, ["B08"], {"resolution_m": 10}, sample=True)
    scene["properties"]["platform"] = "landsat-7"
    with pytest.raises(ValueError, match="LANDSAT_8_9_REQUIRED"):
        sensor_of(scene)


def test_landsat_job_end_to_end_and_unsupported_index_before_quota(client, headers, seeded):
    with Session() as db:
        organization_id = db.get(Scene, seeded["scenes"][0]["id"]).organization_id
        scene = Scene(
            organization_id=organization_id,
            sample=True,
            item=create_landsat_fixture(settings.data_dir / "fixtures" / "landsat-job"),
        )
        db.add(scene)
        db.commit()
        scene_id = scene.id
    body = dict(
        project_id=seeded["project"]["id"],
        aoi_id=seeded["aoi"]["id"],
        scene_id=scene_id,
        operation_kind="index",
        operation_id="NDRE_B05",
    )
    response = client.post("/v1/analyses", headers={**headers, "Idempotency-Key": str(uuid4())}, json=body)
    assert response.status_code == 400 and "BANDS_UNAVAILABLE_FOR_SENSOR" in response.text
    assert client.get("/v1/usage", headers=headers).json()["reserved"] == 0
    body["operation_id"] = "NDVI"
    response = client.post("/v1/analyses", headers={**headers, "Idempotency-Key": str(uuid4())}, json=body)
    assert response.status_code == 202, response.text
    work_once()
    result = client.get(f"/v1/analyses/{response.json()['id']}", headers=headers).json()
    assert result["status"] == "succeeded", result
    assert result["provenance"]["sensor"] == LANDSAT
    assert "SR_B5" in result["provenance"]["model"]["formula"]
    assert len(result["artifacts"]) >= 3


def test_signed_urls_refresh_in_memory_and_reject_unapproved_hosts(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={"token": "sp=r&sig=test", "msft:expiry": "2099-01-01T00:00:00Z"},
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    _tokens.clear()
    href = "https://landsateuwest.blob.core.windows.net/landsat-c2/a.TIF"
    assert sign_landsat_href(href).endswith("?sp=r&sig=test")
    sign_landsat_href(href)
    assert len(calls) == 1
    _tokens["landsateuwest.blob.core.windows.net"] = ("expired", 0)
    assert sign_landsat_href(href).endswith("?sp=r&sig=test")
    assert len(calls) == 2
    _tokens.clear()
    with pytest.raises(ValueError, match="UNAPPROVED_LANDSAT_ASSET"):
        sign_landsat_href("https://evil.example/landsat-c2/a.TIF")


def test_cross_sensor_temporal_comparison_refused_before_quota(client, headers, seeded):
    with Session() as db:
        scene = db.get(Scene, seeded["scenes"][0]["id"])
        inputs = []
        for sensor in ("sentinel-2", LANDSAT):
            analysis = Analysis(
                organization_id=scene.organization_id,
                project_id=seeded["project"]["id"],
                aoi_id=seeded["aoi"]["id"],
                scene_id=scene.id,
                operation_kind="index",
                operation_id="NDVI",
                status="succeeded",
                provenance={"sensor": sensor},
            )
            db.add(analysis)
            db.flush()
            inputs.append(analysis.id)
        db.commit()
    response = client.post(
        "/v1/analyses",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={
            "project_id": seeded["project"]["id"],
            "aoi_id": seeded["aoi"]["id"],
            "operation_kind": "temporal_diff",
            "operation_id": "TEMPORAL_DIFFERENCE",
            "input_analysis_ids": inputs,
        },
    )
    assert response.status_code == 400
    assert "CROSS_SENSOR_TEMPORAL_COMPARISON_REQUIRES_HARMONIZATION" in response.text
    assert client.get("/v1/usage", headers=headers).json()["reserved"] == 0


def test_expired_signing_response_is_not_used(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={"token": "expired", "msft:expiry": "2000-01-01T00:00:00Z"},
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    _tokens.clear()
    with pytest.raises(ValueError, match="LANDSAT_SIGNING_UNAVAILABLE"):
        sign_landsat_href("https://landsateuwest.blob.core.windows.net/landsat-c2/a.TIF")
    assert not _tokens
