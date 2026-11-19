import io
import zipfile

from services.api.jobs import work_once


def body(seed, kind="index", ident="NDVI", params=None):
    return {
        "project_id": seed["project"]["id"],
        "aoi_id": seed["aoi"]["id"],
        "scene_id": seed["scenes"][0]["id"],
        "operation_kind": kind,
        "operation_id": ident,
        "params": params or {},
    }


def enqueue(client, headers, seed, key="test-request-1", **kwargs):
    return client.post("/v1/analyses", json=body(seed, **kwargs), headers={**headers, "Idempotency-Key": key})


def test_auth_and_project_crud(client, headers):
    assert client.get("/v1/projects").status_code == 401
    assert client.get("/v1/indices", headers=headers).json()["indices"][0]["id"] == "NDVI"
    result = client.post("/v1/projects", headers=headers, json={"name": "Maputo"})
    assert result.status_code == 201
    ident = result.json()["id"]
    other = {"Authorization": "Bearer test:bob"}
    assert client.get(f"/v1/projects/{ident}", headers=other).status_code == 404
    assert client.patch(f"/v1/projects/{ident}", json={"name": "Changed"}, headers=headers).status_code == 200
    assert client.delete(f"/v1/projects/{ident}", headers=headers).status_code == 200
    assert client.get(f"/v1/projects/{ident}", headers=headers).status_code == 404


def test_full_processing_and_tenant_security(client, headers, seeded):
    response = enqueue(client, headers, seeded)
    assert response.status_code == 202, response.text
    analysis = response.json()
    assert analysis["status"] == "queued" and not analysis["artifacts"]
    assert enqueue(client, headers, seeded).json()["id"] == analysis["id"]
    assert enqueue(client, headers, seeded, ident="EVI").status_code == 409
    assert enqueue(client, headers, seeded, key="different-request").status_code == 429
    assert work_once()
    result = client.get(f"/v1/analyses/{analysis['id']}", headers=headers).json()
    assert result["status"] == "succeeded", result
    assert result["stats"]["count"] > 0
    assert result["provenance"]["sample"] is True
    assert len(result["artifacts"]) == 7
    other = {"Authorization": "Bearer test:bob"}
    for path in [
        f"/v1/aois/{seeded['aoi']['id']}",
        f"/v1/analyses/{analysis['id']}",
        f"/v1/jobs/{analysis['job']['id']}",
    ]:
        assert client.get(path, headers=other).status_code == 404
    cog = next(a for a in result["artifacts"] if a["artifact_type"] == "cog")
    for path in [f"/v1/artifacts/{cog['id']}/download", f"/v1/artifacts/{cog['id']}/tiles/12/2418/2353.png"]:
        assert client.get(path, headers=other).status_code == 404
    signed = client.get(f"/v1/artifacts/{cog['id']}/download", headers=headers).json()
    downloaded = client.get(signed["url"])
    assert downloaded.status_code == 200
    assert downloaded.content[:2] in (b"II", b"MM")
    assert client.get(f"/v1/downloads/{cog['id']}?expires=0&signature=bad").status_code == 403
    assert client.get(f"/v1/artifacts/{cog['id']}/tiles/12/2418/2353.png", headers=headers).status_code == 200
    assert client.get("/v1/usage", headers=headers).json()["settled"] == 1
    assert client.delete(f"/v1/projects/{seeded['project']['id']}", headers=headers).status_code == 200
    assert client.get(signed["url"]).status_code == 404


def test_cancel_and_refund(client, headers, seeded):
    result = enqueue(client, headers, seeded).json()
    cancelled = client.post(f"/v1/jobs/{result['job']['id']}/cancel", headers=headers)
    assert cancelled.json()["status"] == "cancelled"
    assert work_once() is None
    usage = client.get("/v1/usage", headers=headers).json()
    assert usage["refunded"] == 1 and usage["reserved"] == 0


def test_failure_refunds(client, headers, seeded):
    from services.api.db import Scene, Session

    with Session() as db:
        scene = db.get(Scene, seeded["scenes"][0]["id"])
        item = dict(scene.item)
        item["assets"]["B08"]["raster:bands"] = [{}]
        scene.item = item
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(scene, "item")
        db.commit()
    result = enqueue(client, headers, seeded).json()
    work_once()
    failed = client.get(f"/v1/analyses/{result['id']}", headers=headers).json()
    assert failed["status"] == "failed"
    assert failed["job"]["error_code"] == "UNKNOWN_CALIBRATION"
    assert client.get("/v1/usage", headers=headers).json()["refunded"] == 1


def test_transformations(client, headers, seeded):
    for kind, ident, params in [
        ("band_ratio", "BAND_RATIO", {}),
        ("pca", "PCA", {"bands": ["B02", "B03", "B08"], "standardize": True}),
        ("composite", "RGB", {"bands": ["B04", "B03", "B02"]}),
    ]:
        response = enqueue(
            client, headers, seeded, key=f"transform-{kind}", kind=kind, ident=ident, params=params
        )
        assert response.status_code == 202
        work_once()
        result = client.get(f"/v1/analyses/{response.json()['id']}", headers=headers).json()
        assert result["status"] == "succeeded", result


def test_temporal_job(client, headers, seeded):
    inputs = []
    for i in (0, 1):
        payload = body(seeded)
        payload["scene_id"] = seeded["scenes"][i]["id"]
        result = client.post(
            "/v1/analyses", json=payload, headers={**headers, "Idempotency-Key": f"temporal-input-{i}"}
        )
        assert result.status_code == 202
        work_once()
        inputs.append(result.json()["id"])
    payload = {
        **body(seeded, "temporal_diff", "TEMPORAL_DIFFERENCE"),
        "scene_id": None,
        "input_analysis_ids": inputs,
    }
    result = client.post(
        "/v1/analyses", json=payload, headers={**headers, "Idempotency-Key": "temporal-result"}
    )
    assert result.status_code == 202
    work_once()
    output = client.get(f"/v1/analyses/{result.json()['id']}", headers=headers).json()
    assert output["status"] == "succeeded", output
    assert output["provenance"]["acquisition_dates"] == ["2025-01-15T10:00:00Z", "2025-02-15T10:00:00Z"]


def test_unsafe_import_rejected(client, headers, seeded):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("../../evil.shp", b"bad")
    path = f"/v1/projects/{seeded['project']['id']}/aois/import"
    result = client.post(
        path, headers=headers, files={"file": ("bad.zip", stream.getvalue(), "application/zip")}
    )
    assert result.status_code == 400
    assert result.json()["error"]["code"] == "UNSAFE_ZIP"
