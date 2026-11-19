"""Sensor profiles. Internal equation keys retain the versioned Sentinel catalog semantics."""

import re

from .registry import BANDS, REGISTRY

SENTINEL = "sentinel-2"
LANDSAT = "landsat-8-9"
LANDSAT_NATIVE = {
    "B01": "SR_B1",
    "B02": "SR_B2",
    "B03": "SR_B3",
    "B04": "SR_B4",
    "B08": "SR_B5",
    "B11": "SR_B6",
    "B12": "SR_B7",
}
LANDSAT_ASSETS = {
    "B01": "coastal",
    "B02": "blue",
    "B03": "green",
    "B04": "red",
    "B08": "nir08",
    "B11": "swir16",
    "B12": "swir22",
    "QA_PIXEL": "qa_pixel",
    "QA_RADSAT": "qa_radsat",
}


def sensor_of(item):
    collection = item.get("collection", "")
    platform = item.get("properties", {}).get("platform", "")
    if collection == "landsat-c2-l2":
        if platform not in ("landsat-8", "landsat-9"):
            raise ValueError("LANDSAT_8_9_REQUIRED")
        return LANDSAT
    if platform.startswith("landsat") or collection.startswith("landsat"):
        raise ValueError("UNSUPPORTED_LANDSAT_COLLECTION")
    return SENTINEL


def native_bands(sensor):
    return LANDSAT_NATIVE.copy() if sensor == LANDSAT else {b: b for b in BANDS}


def band_resolutions(sensor):
    return {b: 30 for b in LANDSAT_NATIVE} if sensor == LANDSAT else BANDS.copy()


def native_formula(formula, sensor):
    names = native_bands(sensor)
    return re.sub(r"\bB(?:\d{2}|8A)\b", lambda m: names[m[0]], formula)


def catalog_for(sensor):
    names = native_bands(sensor)
    resolutions = band_resolutions(sensor)
    indices = []
    for spec in REGISTRY.values():
        if not set(spec["bands"]) <= names.keys():
            continue
        entry = {
            **spec,
            "bands": [names[b] for b in spec["bands"]],
            "formula": native_formula(spec["formula"], sensor),
            "native_output_resolution_m": max(resolutions[b] for b in spec["bands"]),
        }
        if sensor == LANDSAT:
            entry["notes"] = (
                "Landsat 8/9 OLI surface reflectance, 30 m. Sensor responses differ from Sentinel-2."
            )
            entry["notes_pt"] = (
                "Reflectância de superfície Landsat 8/9 OLI, 30 m. A resposta espectral difere do Sentinel-2."
            )
        indices.append(entry)
    return {
        "version": "1.1.0",
        "sensor": sensor,
        "indices": indices,
        "bands": resolutions,
        "native_bands": names,
    }
