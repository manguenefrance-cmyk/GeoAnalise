"""Prepare deterministic calibration/algebra/COG interoperability cases for independent QGIS."""

import json
import os
import sys
from pathlib import Path

os.environ["APP_ENV"] = "test"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402
from services.api.config import settings  # noqa: E402
from services.processor.fixtures import create_fixture, FIXTURE_GEOMETRY  # noqa: E402
from services.processor.raster import read_scene  # noqa: E402
from services.processor.registry import REGISTRY, calculate  # noqa: E402
from services.processor.exports import write_cog  # noqa: E402

directory = (settings.data_dir / "qgis-validation").resolve()
directory.mkdir(parents=True, exist_ok=True)
scene = create_fixture(settings.data_dir / "fixtures" / "qgis-reference")
cases = []
for index_id in ["NDVI", "NDWI_MCF", "NDBI", "EVI"]:
    spec = REGISTRY[index_id]
    bands, grid, _, provenance = read_scene(
        scene, FIXTURE_GEOMETRY, spec["bands"], {"interpolation": "nearest"}, sample=True
    )
    result = calculate(index_id, bands)
    path = directory / f"{index_id}.tif"
    write_cog(path, result, grid)
    expression = spec["formula"]
    for band in spec["bands"]:
        expression = expression.replace(band, f'("{band}@1" * 0.0001 - 0.1)')
    cases.append(
        {
            "id": index_id,
            "expression": expression,
            "bands": {b: scene["assets"][b]["href"] for b in spec["bands"]},
            "output_cog": str(path),
            "crs": provenance["crs"],
            "bounds": provenance["bounds"],
            "width": grid["width"],
            "height": grid["height"],
            "resolution_m": provenance["resolution_m"],
            "values": [float(v) if np.isfinite(v) else None for v in result.flat],
        }
    )
(directory / "cases.json").write_text(json.dumps(cases, allow_nan=False), encoding="utf-8")
print(directory / "cases.json")
