"""Optional real, public Landsat integration check; normal tests stay offline."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rasterio  # noqa: E402
from services.processor.engine import statistics  # noqa: E402
from services.processor.exports import write_cog  # noqa: E402
from services.processor.fixtures import FIXTURE_GEOMETRY  # noqa: E402
from services.processor.raster import read_scene  # noqa: E402
from services.processor.registry import calculate  # noqa: E402
from services.processor.stac import search_cached  # noqa: E402

items, _ = search_cached(
    json.dumps(FIXTURE_GEOMETRY),
    "2026-10-01",
    "2026-10-31",
    20,
    10,
    int(time.time() // 300),
    "planetary_computer",
)
if not items:
    raise SystemExit("No accessible Landsat scene found for this public validation area.")
item = min(items, key=lambda i: i["properties"].get("eo:cloud_cover", 100))
bands, grid, domain, provenance = read_scene(item, FIXTURE_GEOMETRY, ["B08", "B04"])
result = calculate("NDVI", bands)
stats = statistics(result, domain)
if not stats["count"]:
    raise SystemExit("No valid Landsat pixels; no successful validation claimed.")
destination = Path("data/live/landsat")
destination.mkdir(parents=True, exist_ok=True)
write_cog(destination / "ndvi.tif", result, grid)
with rasterio.open(destination / "ndvi.tif") as source:
    assert source.crs.to_epsg() == 32736 and source.res == (30, 30)
    assert source.tags(ns="IMAGE_STRUCTURE")["LAYOUT"] == "COG"
report = {"scene": item["id"], "provenance": provenance, "statistics": stats}
Path("docs/evidence/landsat-live-pixels.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(
    json.dumps(
        {
            "scene": item["id"],
            "valid_pixels": stats["count"],
            "resolution_m": 30,
            "mean_ndvi": stats["mean"],
            "cog_verified": True,
        }
    )
)
