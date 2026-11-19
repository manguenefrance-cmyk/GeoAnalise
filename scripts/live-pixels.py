"""Small, real, public Collection 1 raster smoke test. Fetch AOI windows, not full scenes."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from services.processor.fixtures import FIXTURE_GEOMETRY  # noqa: E402
from services.processor.registry import calculate  # noqa: E402
from services.processor.raster import read_scene  # noqa: E402
from services.processor.engine import statistics  # noqa: E402
from services.processor.exports import export_products  # noqa: E402
from services.api.db import now  # noqa: E402

report = {
    "provider": "https://earth-search.aws.element84.com/v1",
    "collection": "sentinel-2-c1-l2a",
    "validated": False,
    "sample": False,
    "checked_at": now(),
}
try:
    response = httpx.post(
        report["provider"] + "/search",
        json={
            "collections": [report["collection"]],
            "intersects": FIXTURE_GEOMETRY,
            "datetime": "2026-01-01T00:00:00Z/2026-10-31T23:59:59Z",
            "limit": 20,
        },
        timeout=30,
    )
    response.raise_for_status()
    items = response.json()["features"]
    item = min(items, key=lambda i: i["properties"].get("eo:cloud_cover", 100))
    bands, grid, domain, provenance = read_scene(item, FIXTURE_GEOMETRY, ["B08", "B04"], sample=False)
    result = calculate("NDVI", bands)
    assert np.isfinite(result).any(), "No valid pixels in the selected acquisition"
    with np.errstate(all="ignore"):
        independent = (bands["B08"] - bands["B04"]) / (bands["B08"] + bands["B04"])
    np.testing.assert_allclose(result, independent, atol=1e-5, equal_nan=True)
    provenance.update(
        {
            "operation_id": "NDVI",
            "algorithm_version": "1.0.0",
            "generated_at": now(),
            "statistics": statistics(result, domain),
        }
    )
    destination = Path("data/live-smoke")
    export_products(destination, result, grid, provenance, "NDVI")
    with rasterio.open(destination / "result.tif") as src:
        assert src.tags(ns="IMAGE_STRUCTURE")["LAYOUT"] == "COG"
        report["cog_verified"] = True
    report.update(
        {
            "validated": True,
            "scene_id": item["id"],
            "acquired_at": provenance["acquired_at"],
            "statistics": statistics(result, domain),
            "grid": {k: v for k, v in provenance.items() if k in ("crs", "width", "height", "resolution_m")},
            "sources": provenance["sources"],
            "output": str(destination),
        }
    )
except Exception as exc:
    report["error_type"] = type(exc).__name__
    report["error"] = str(exc)[:250]
Path("docs/evidence").mkdir(parents=True, exist_ok=True)
Path("docs/evidence/live-pixels.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
sys.exit(0 if report["validated"] else 1)
