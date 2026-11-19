"""Read-only public STAC metadata smoke. No claim that pixel processing is validated."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx  # noqa: E402
from services.processor.fixtures import FIXTURE_GEOMETRY  # noqa: E402
from services.api.config import settings  # noqa: E402

report = {
    "provider": settings.stac_url,
    "collection": settings.stac_collection,
    "pixel_processing_validated": False,
}
try:
    with httpx.Client(timeout=30) as client:
        response = client.get(f"{settings.stac_url}/collections/{settings.stac_collection}")
        response.raise_for_status()
        report["collection_verified"] = response.json()["id"]
        response = client.post(
            f"{settings.stac_url}/search",
            json={
                "collections": [settings.stac_collection],
                "intersects": FIXTURE_GEOMETRY,
                "datetime": "2026-01-01T00:00:00Z/2026-10-31T23:59:59Z",
                "limit": 2,
            },
        )
        response.raise_for_status()
        features = response.json()["features"]
        report["search_validated"] = True
        report["scene_count"] = len(features)
        report["asset_keys"] = list(features[0].get("assets", {})) if features else []
        report["scene_id"] = features[0]["id"] if features else None
except Exception as exc:
    report["error"] = type(exc).__name__
    report["search_validated"] = False
Path("docs/evidence").mkdir(parents=True, exist_ok=True)
Path("docs/evidence/live-stac.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
sys.exit(0 if report.get("search_validated") else 1)
