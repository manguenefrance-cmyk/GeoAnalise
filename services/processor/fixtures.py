"""Deterministic synthetic raster factory, never represented as observed satellite data."""

import json
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

from .registry import BANDS

FIXTURE_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [
        [[32.57, -25.95], [32.575, -25.95], [32.575, -25.945], [32.57, -25.945], [32.57, -25.95]]
    ],
}


def create_fixture(directory: Path, variant=0):
    directory.mkdir(parents=True, exist_ok=True)
    x, y = Transformer.from_crs(4326, 32736, always_xy=True).transform(32.57, -25.945)
    x, y = np.floor(x / 20) * 20 - 40, np.ceil(y / 20) * 20 + 40
    assets = {}
    for i, (band, resolution) in enumerate(BANDS.items()):
        size = 720 // resolution
        yy, xx = np.mgrid[:size, :size] / size
        base = {
            "B02": 0.07,
            "B03": 0.12,
            "B04": 0.08,
            "B05": 0.16,
            "B08": 0.48,
            "B8A": 0.46,
            "B11": 0.22,
            "B12": 0.14,
        }.get(band, 0.2)
        values = base + 0.05 * np.sin(xx * 8 + i) + 0.03 * yy + variant * 0.01
        water = (xx - 0.7) ** 2 + (yy - 0.55) ** 2 < 0.035
        values[water] = 0.1 if band == "B03" else 0.025
        raw = np.round((values + 0.1) / 0.0001).astype("uint16")
        raw[:2] = 0
        path = (directory / f"{band}.tif").resolve()
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=size,
            height=size,
            count=1,
            dtype="uint16",
            crs="EPSG:32736",
            transform=from_origin(x, y, resolution, resolution),
            nodata=0,
            tiled=True,
            compress="deflate",
        ) as dst:
            dst.write(raw, 1)
        assets[band] = {
            "href": str(path),
            "eo:bands": [{"name": band}],
            "raster:bands": [{"scale": 0.0001, "offset": -0.1, "nodata": 0}],
        }
    scl = np.full((36, 36), 4, dtype="uint8")
    scl[4:10, 5:12] = 9
    scl[10:13, 8:13] = 3
    path = (directory / "SCL.tif").resolve()
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=36,
        height=36,
        count=1,
        dtype="uint8",
        crs="EPSG:32736",
        transform=from_origin(x, y, 20, 20),
        nodata=0,
    ) as dst:
        dst.write(scl, 1)
    assets["SCL"] = {"href": str(path)}
    scene = {
        "type": "Feature",
        "id": f"SYNTHETIC-TEST-{variant}",
        "collection": "synthetic-test-rasters",
        "geometry": FIXTURE_GEOMETRY,
        "properties": {
            "datetime": f"2025-0{variant + 1}-15T10:00:00Z",
            "eo:cloud_cover": 8.5,
            "s2:processing_baseline": "04.00",
            "sample": True,
            "license": "Synthetic fixture, generated locally; not satellite observations",
        },
        "assets": assets,
    }
    (directory / "scene.json").write_text(json.dumps(scene, indent=2), encoding="utf-8")
    return scene


def create_landsat_fixture(directory: Path):
    """Small OLI fixture with native bands and known QA flags, never real satellite data."""
    from .sensors import LANDSAT_ASSETS, LANDSAT_NATIVE

    directory.mkdir(parents=True, exist_ok=True)
    x, y = Transformer.from_crs(4326, 32736, always_xy=True).transform(32.57, -25.945)
    x, y = np.floor(x / 30) * 30 - 60, np.ceil(y / 30) * 30 + 60
    grid = dict(
        driver="GTiff",
        width=26,
        height=26,
        count=1,
        dtype="uint16",
        crs="EPSG:32736",
        transform=from_origin(x, y, 30, 30),
    )
    assets = {}
    for band, native in LANDSAT_NATIVE.items():
        value = {"B08": 0.5, "B04": 0.1, "B02": 0.05, "B03": 0.15, "B11": 0.25, "B12": 0.2}.get(band, 0.08)
        raw = np.full((26, 26), round((value + 0.2) / 0.0000275), dtype="uint16")
        path = (directory / f"{native}.tif").resolve()
        with rasterio.open(path, "w", **grid, nodata=0) as dst:
            dst.write(raw, 1)
        assets[LANDSAT_ASSETS[band]] = {
            "href": str(path),
            "eo:bands": [{"name": native}],
            "raster:bands": [{"scale": 0.0000275, "offset": -0.2, "nodata": 0}],
        }
    for name in ("QA_PIXEL", "QA_RADSAT"):
        data = np.zeros((26, 26), dtype="uint16")
        if name == "QA_PIXEL":
            data[5:10, 5:10] = 1 << 3
            data[12:15, 10:12] = 1
        else:
            data[16:18, 10:13] = 1 << 4
        path = (directory / f"{name}.tif").resolve()
        with rasterio.open(path, "w", **grid) as dst:
            dst.write(data, 1)
        assets[LANDSAT_ASSETS[name]] = {"href": str(path)}
    return {
        "type": "Feature",
        "id": "SYNTHETIC-LANDSAT-8",
        "collection": "landsat-c2-l2",
        "geometry": FIXTURE_GEOMETRY,
        "properties": {
            "platform": "landsat-8",
            "datetime": "2025-01-15T10:00:00Z",
            "eo:cloud_cover": 5,
            "sample": True,
            "license": "Synthetic fixture; not satellite observations",
        },
        "assets": assets,
    }
