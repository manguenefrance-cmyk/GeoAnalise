import os
import tempfile
from pathlib import Path

TEST_DIR = Path(tempfile.mkdtemp(prefix="arcambe-tests-"))
os.environ["APP_ENV"] = "test"
os.environ["DATA_DIR"] = str(TEST_DIR)
os.environ["DATABASE_URL"] = "sqlite:///" + str(TEST_DIR / "test.db")
os.environ["DAILY_JOB_LIMIT"] = "100"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from services.api.main import app, requests_by_ip  # noqa: E402
from services.api.db import Base, engine  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    requests_by_ip.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def headers():
    return {"Authorization": "Bearer test:alice"}


@pytest.fixture
def seeded(client, headers):
    response = client.post("/v1/test/seed", headers=headers)
    assert response.status_code == 201, response.text
    seed = response.json()
    seed["aoi"] = client.get(f"/v1/projects/{seed['project']['id']}/aois", headers=headers).json()[0]
    return seed
