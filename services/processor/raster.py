import math
import re
from urllib.parse import urlparse
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from shapely.geometry import mapping, shape
from shapely.ops import transform

from services.api.config import settings
from .registry import BANDS, CATALOG
from .sensors import LANDSAT, LANDSAT_ASSETS, LANDSAT_NATIVE, band_resolutions, sensor_of
from .planetary import sign_landsat_href


def calibration(raw, metadata, pipeline="stac", safe_offset=None, quantification=None):
    raw = np.asarray(raw, dtype=np.float32)
    valid = np.isfinite(raw)
    if metadata.get("nodata") is not None:
        valid &= raw != metadata["nodata"]
    if pipeline == "safe":
        if safe_offset is None or not quantification or quantification <= 0:
            raise ValueError("UNKNOWN_CALIBRATION")
        valid &= raw != 0
        result = (raw + safe_offset) / quantification
    elif pipeline == "normalized":
        if metadata.get("scale", 1) != 1 or metadata.get("offset", 0) != 0:
            raise ValueError("DOUBLE_CALIBRATION_REFUSED")
        result = raw
    elif pipeline == "stac" and "scale" in metadata and "offset" in metadata:
        if (
            not np.isfinite(metadata["scale"])
            or not np.isfinite(metadata["offset"])
            or metadata["scale"] <= 0
        ):
            raise ValueError("INVALID_CALIBRATION")
        result = raw * metadata["scale"] + metadata["offset"]
    else:
        raise ValueError("UNKNOWN_CALIBRATION")
    return np.where(valid, result, np.nan).astype(np.float32)


def resolve_asset(item, band):
    if sensor_of(item) == LANDSAT:
        key = LANDSAT_ASSETS.get(band)
        asset = item.get("assets", {}).get(key)
        if not asset or set(asset.get("roles", [])) & {"visual", "overview"}:
            raise ValueError(f"BAND_UNAVAILABLE_OR_AMBIGUOUS_{band}")
        return asset
    matches = []
    for name, asset in item.get("assets", {}).items():
        eo = asset.get("eo:bands", [])
        if band != "SCL" and (len(eo) > 1 or set(asset.get("roles", [])) & {"visual", "overview"}):
            continue
        names = [str(b.get("name", "")).upper() for b in eo]
        names += [str(b.get("name", "")).upper() for b in asset.get("bands", [])]
        key = name.upper().split("_")[0]
        aliases = {
            "BLUE": "B02",
            "GREEN": "B03",
            "RED": "B04",
            "NIR": "B08",
            "NIR08": "B8A",
            "RED_EDGE_1": "B05",
            "RED_EDGE_2": "B06",
            "RED_EDGE_3": "B07",
            "SWIR16": "B11",
            "SWIR22": "B12",
            "SCL": "SCL",
        }
        alias = aliases.get(name.upper())
        if band in names or key == band or alias == band:
            matches.append((name, asset))
    if len(matches) > 1:
        native_resolution = 20 if band == "SCL" else BANDS.get(band)
        native = [
            (name, asset)
            for name, asset in matches
            if asset.get("gsd") == native_resolution or name.upper().endswith(f"_{native_resolution}M")
        ]
        if native:
            matches = native
    if len(matches) != 1:
        raise ValueError(f"BAND_UNAVAILABLE_OR_AMBIGUOUS_{band}")
    return matches[0][1]


def allowed_href(href, sample=False):
    url = urlparse(href)
    if sample and settings.app_env == "test":
        path = Path(href).resolve()
        root = (settings.data_dir / "fixtures").resolve()
        if path.is_relative_to(root) and path.is_file():
            return str(path)
    allowed = settings.raster_allowed_hosts.split(",")
    if (
        url.scheme != "https"
        or url.hostname not in allowed
        or url.username
        or url.password
        or url.port not in (None, 443)
    ):
        raise ValueError("ASSET_ACCESS_UNSUPPORTED_CONFIGURE_APPROVED_PROVIDER")
    if not re.search(r"\.(tif|tiff|jp2)(\?|$)", href, re.I):
        raise ValueError("WINDOWED_RASTER_ASSET_REQUIRED")
    return href


def read_scene(item, geometry, selected, params=None, sample=False):
    params = params or {}
    sensor = sensor_of(item)
    resolutions = band_resolutions(sensor)
    if not selected or not set(selected) <= resolutions.keys():
        raise ValueError("INVALID_BAND")
    if sensor == LANDSAT and (params.get("mask_scl_2") or params.get("mask_scl_7")):
        raise ValueError("SCL_OPTIONS_REQUIRE_SENTINEL")

    def asset_href(asset):
        href = allowed_href(asset["href"], sample)
        return sign_landsat_href(href) if sensor == LANDSAT and not sample else href

    geom = shape(geometry)
    lon, lat = geom.centroid.coords[0]
    crs = f"EPSG:{(32600 if lat >= 0 else 32700) + int((lon + 180) // 6) + 1}"
    project = Transformer.from_crs(4326, crs, always_xy=True).transform
    projected = transform(project, geom)
    native = max(resolutions[b] for b in selected)
    resolution = int(params.get("resolution_m", native))
    if resolution not in ((30,) if sensor == LANDSAT else (10, 20, 60)):
        raise ValueError("INVALID_RESOLUTION")
    west, south, east, north = projected.bounds
    west, south = math.floor(west / resolution) * resolution, math.floor(south / resolution) * resolution
    east, north = math.ceil(east / resolution) * resolution, math.ceil(north / resolution) * resolution
    width, height = round((east - west) / resolution), round((north - south) / resolution)
    if width * height > settings.max_pixels:
        raise ValueError("PIXEL_MEMORY_LIMIT")
    grid = {
        "crs": crs,
        "transform": from_origin(west, north, resolution, resolution),
        "width": width,
        "height": height,
    }
    domain = geometry_mask([mapping(projected)], (height, width), grid["transform"], invert=True)
    interpolation = params.get("interpolation", "bilinear")
    if interpolation not in ("bilinear", "nearest"):
        raise ValueError("INVALID_INTERPOLATION")
    results, source_info = {}, {}
    with rasterio.Env(
        GDAL_HTTP_TIMEOUT="25",
        GDAL_HTTP_CONNECTTIMEOUT="10",
        GDAL_HTTP_MAX_RETRY="2",
        GDAL_HTTP_MULTIRANGE="YES",
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        GDAL_CACHEMAX=64_000_000,
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff,.jp2",
        GDAL_HTTP_MAX_REDIR="0",
    ):
        for band in selected:
            asset = resolve_asset(item, band)
            href = asset_href(asset)
            meta = (asset.get("raster:bands") or [{}])[0]
            if not meta and "raster:scale" in asset and "raster:offset" in asset:
                meta = {
                    "scale": asset["raster:scale"],
                    "offset": asset["raster:offset"],
                    "nodata": asset.get("nodata"),
                }
            if (
                item.get("properties", {}).get("earthsearch:boa_offset_applied") is True
                and meta.get("offset", 0) != 0
            ):
                raise ValueError("CONFLICTING_PROVIDER_CALIBRATION_USE_COLLECTION_1")
            with rasterio.open(href) as src:
                if not src.crs:
                    raise ValueError("ASSET_CRS_MISSING")
                if not meta and (src.scales[0] != 1 or src.offsets[0] != 0):
                    meta = {"scale": src.scales[0], "offset": src.offsets[0], "nodata": src.nodata}
                with WarpedVRT(
                    src,
                    **grid,
                    dtype="float32",
                    src_nodata=src.nodata,
                    nodata=float("nan"),
                    resampling=Resampling[interpolation],
                ) as vrt:
                    raw = vrt.read(1)
            results[band] = calibration(raw, meta)
            source_info[band] = {
                "asset": href.split("?")[0],
                "scale": meta.get("scale"),
                "offset": meta.get("offset"),
                "pipeline": "stac_scale_offset_once",
                "native_resolution_m": resolutions[band],
                "native_band": LANDSAT_NATIVE[band] if sensor == LANDSAT else band,
            }
        masked_classes = list(CATALOG["processing"]["mask_scl_default"])
        if params.get("mask_scl_2"):
            masked_classes.append(2)
        if params.get("mask_scl_7"):
            masked_classes.append(7)
        qa_bits = []
        saturation_bits = []
        if sensor == LANDSAT:
            qa = {}
            for name, fill in (("QA_PIXEL", 1), ("QA_RADSAT", 65535)):
                asset = resolve_asset(item, name)
                with rasterio.open(asset_href(asset)) as src:
                    # Zero in QA is valid. Outside coverage is explicitly invalid.
                    with WarpedVRT(
                        src,
                        **grid,
                        dtype="uint16",
                        src_nodata=None,
                        nodata=fill,
                        resampling=Resampling.nearest,
                    ) as vrt:
                        qa[name] = vrt.read(1)
            qa_bits = list(range(6)) if params.get("cloud_mask", True) else [0]
            saturation_bits = sorted({int(LANDSAT_NATIVE[b].split("B")[1]) - 1 for b in selected} | {11})
            valid = domain & landsat_valid_mask(qa["QA_PIXEL"], qa["QA_RADSAT"], qa_bits, saturation_bits)
        elif params.get("cloud_mask", True):
            asset = resolve_asset(item, "SCL")
            with rasterio.open(allowed_href(asset["href"], sample)) as src:
                with WarpedVRT(src, **grid, resampling=Resampling.nearest, nodata=0) as vrt:
                    scl = vrt.read(1)
            valid = domain & ~np.isin(scl, masked_classes)
        else:
            valid = domain.copy()
        # Metre-based dilation on the target grid, with explicit bounded radius.
        dilation = float(params.get("cloud_dilation_m", 0))
        if not 0 <= dilation <= 200:
            raise ValueError("INVALID_CLOUD_DILATION")
        if dilation:
            from scipy.ndimage import binary_dilation

            radius = math.ceil(dilation / resolution)
            yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
            invalid = domain & ~valid
            valid &= ~binary_dilation(invalid, structure=xx**2 + yy**2 <= radius**2)
        for band in results:
            results[band] = np.where(valid, results[band], np.nan)
    provenance = {
        "sensor": sensor,
        "platform": item.get("properties", {}).get("platform"),
        "scene_id": item["id"],
        "collection": item.get("collection"),
        "acquired_at": item["properties"].get("datetime"),
        "processing_baseline": item["properties"].get("s2:processing_baseline"),
        "sample": sample,
        "sources": source_info,
        "scene_cloud_cover": item["properties"].get("eo:cloud_cover"),
        "crs": crs,
        "transform": list(grid["transform"])[:6],
        "width": width,
        "height": height,
        "bounds": [west, south, east, north],
        "resolution_m": resolution,
        "interpolation": interpolation,
        "scl_resampling": "nearest" if sensor != LANDSAT else None,
        "mask_scl": masked_classes if sensor != LANDSAT and params.get("cloud_mask", True) else [],
        "qa_resampling": "nearest" if sensor == LANDSAT else None,
        "qa_pixel_mask_bits": qa_bits,
        "qa_radsat_mask_bits": saturation_bits,
        "cloud_dilation_m": dilation,
        "finer_interpolation": resolution < native,
        "license": item["properties"].get(
            "license",
            "USGS Landsat public domain; check provider terms"
            if sensor == LANDSAT
            else "Copernicus Sentinel data; check provider terms",
        ),
    }
    return results, grid, domain, provenance


def landsat_valid_mask(pixel, saturation, pixel_bits, saturation_bits):
    """USGS Collection 2 OLI QA flags; unrelated saturated bands do not invalidate an index."""
    pixel_flags = sum(1 << b for b in pixel_bits)
    saturation_flags = sum(1 << b for b in saturation_bits)
    return ((pixel & pixel_flags) == 0) & ((saturation & saturation_flags) == 0)
