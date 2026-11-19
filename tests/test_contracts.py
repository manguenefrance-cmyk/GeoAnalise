from services.api.main import app


def test_json_response_contracts_are_expanded():
    schema = app.openapi()
    for path, operations in schema["paths"].items():
        if "/downloads/" in path or path.endswith((".png", "/preview.png")):
            continue
        for operation in operations.values():
            for status, response in operation["responses"].items():
                if not status.startswith("2"):
                    continue
                body = response["content"]["application/json"]["schema"]
                assert body.get("$ref") or body.get("items", {}).get("$ref"), (path, status, body)
    assert schema["paths"]["/v1/analyses"]["post"]["responses"]["202"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("AnalysisView")
    assert "storage_key" not in schema["components"]["schemas"]["ArtifactView"]["properties"]
    assert schema["paths"]["/v1/projects"]["get"]["responses"]["401"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("ErrorEnvelope")


def test_account_deletion_request_is_private_idempotent_and_reversible(client, headers):
    endpoint = "/v1/me/deletion-request"
    assert client.get(endpoint, headers=headers).json()["status"] == "none"
    requested = client.post(endpoint, headers=headers)
    assert requested.status_code == 202
    request_id = requested.json()["request_id"]
    assert requested.json()["fulfillment"] == "manual_review"
    assert client.post(endpoint, headers=headers).json()["request_id"] == request_id
    assert client.get(endpoint, headers={"Authorization": "Bearer test:bob"}).json()["status"] == "none"
    assert client.delete(endpoint, headers=headers).json()["status"] == "cancelled"
    assert client.post(endpoint, headers=headers).json()["status"] == "requested"
    assert client.get(endpoint).status_code == 401


def test_dashboard_counts_are_not_limited_to_the_projects_page(client, headers, seeded):
    from services.api.db import Project, Session

    with Session() as db:
        db.add_all(
            [
                Project(organization_id=seeded["project"]["organization_id"], name=f"Study {i}")
                for i in range(35)
            ]
        )
        db.commit()
    assert len(client.get("/v1/projects?limit=1", headers=headers).json()) == 1
    assert client.get("/v1/dashboard", headers=headers).json()["project_count"] == 36
    assert (
        client.get("/v1/dashboard", headers={"Authorization": "Bearer test:bob"}).json()["project_count"] == 0
    )
