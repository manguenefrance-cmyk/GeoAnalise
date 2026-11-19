"""Run with QGIS' Python, not the project's venv. Does not require the desktop GUI."""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    Qgis,
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from osgeo import gdal

gdal.UseExceptions()

source = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[1]
application = QgsApplication([], False)
application.initQgis()
report = {
    "qgis_version": Qgis.QGIS_VERSION,
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "mode": "headless PyQGIS independent raster calculator",
    "tolerance": 1e-5,
    "cases": [],
    "passed": False,
}
try:
    for case in json.loads(source.read_text(encoding="utf-8")):
        extent = QgsRectangle(*case["bounds"])
        width, height = case["width"], case["height"]
        cog = QgsRasterLayer(case["output_cog"], case["id"])
        assert cog.isValid(), "COG not readable by QGIS"
        assert cog.crs().authid() == case["crs"]
        assert cog.width() == width and cog.height() == height
        block = cog.dataProvider().block(1, extent, width, height)
        for i, expected in enumerate(case["values"]):
            row, column = divmod(i, width)
            if expected is None:
                assert block.isNoData(row, column), f"NoData mask mismatch at {i}"
            else:
                assert abs(block.value(row, column) - expected) <= 1e-6, f"COG round-trip mismatch at {i}"
        layers = []
        entries = []
        for band, path in case["bands"].items():
            # QgsRasterCalculator's implicit mixed-resolution reads are not an explicit
            # resampling contract. Align raw DN independently using QGIS' bundled GDAL.
            aligned = str(source.parent / f"aligned-{case['id']}-{band}.tif")
            warped = gdal.Warp(
                aligned,
                path,
                format="GTiff",
                outputBounds=case["bounds"],
                width=width,
                height=height,
                dstSRS=case["crs"],
                srcNodata=0,
                dstNodata=0,
                resampleAlg="near",
                outputType=gdal.GDT_Float32,
            )
            assert warped is not None, f"QGIS GDAL alignment failed for {band}"
            warped = None
            layer = QgsRasterLayer(aligned, band)
            assert layer.isValid(), f"Invalid band {band}"
            layers.append(layer)
            entry = QgsRasterCalculatorEntry()
            entry.ref = f"{band}@1"
            entry.raster = layer
            entry.bandNumber = 1
            entries.append(entry)
        output = str(source.parent / f"qgis-{case['id']}.tif")
        calculator = QgsRasterCalculator(
            case["expression"],
            output,
            "GTiff",
            extent,
            QgsCoordinateReferenceSystem(case["crs"]),
            width,
            height,
            entries,
            QgsProject.instance().transformContext(),
        )
        status = calculator.processCalculation()
        assert int(status) == 0, f"QGIS calculation failed: {calculator.lastError()}"
        independent = QgsRasterLayer(output, "independent")
        calculated = independent.dataProvider().block(1, extent, width, height)
        errors = []
        for i, expected in enumerate(case["values"]):
            if expected is None:
                continue
            row, column = divmod(i, width)
            actual = calculated.value(row, column)
            assert math.isfinite(actual) and not calculated.isNoData(row, column)
            errors.append(abs(actual - expected))
        maximum = max(errors)
        report["cases"].append(
            {
                "index": case["id"],
                "valid_pixels_compared": len(errors),
                "max_absolute_error": maximum,
                "cog_crs_grid_mask_round_trip": True,
                "resolution_m": case["resolution_m"],
                "alignment": "QGIS-bundled GDAL Warp; explicit common extent, size and CRS; nearest",
                "passed": maximum <= report["tolerance"],
            }
        )
    report["passed"] = all(c["passed"] for c in report["cases"])
except Exception as exc:
    report["error"] = str(exc)
destination = root / "docs" / "evidence" / "qgis-validation.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
# QGIS/GDAL global references are released by interpreter shutdown, after the layers.
sys.exit(0 if report["passed"] else 1)
