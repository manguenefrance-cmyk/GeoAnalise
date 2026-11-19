import numpy as np
import pytest
import rasterio

from services.api.config import settings
from services.api.geometry import validate_aoi
from services.processor.exports import write_cog
from services.processor.fixtures import FIXTURE_GEOMETRY, create_fixture
from services.processor.raster import allowed_href, read_scene, resolve_asset
from services.processor.registry import REGISTRY, calculate


@pytest.mark.parametrize("key", list(REGISTRY))
def test_all_indices_real_raster_round_trip(tmp_path, key):
    scene = create_fixture(settings.data_dir / "fixtures" / "math")
    spec = REGISTRY[key]
    bands, grid, domain, provenance = read_scene(scene, FIXTURE_GEOMETRY, spec["bands"], sample=True)
    assert abs(grid["transform"].a) == spec["native_output_resolution_m"]
    result = calculate(key, bands)
    assert np.isfinite(result).any() and np.isnan(result).any()
    assert provenance["sources"][spec["bands"][0]]["offset"] == -0.1
    path = tmp_path / "result.tif"
    write_cog(path, result, grid)
    with rasterio.open(path) as src:
        assert src.crs.to_epsg() == 32736
        assert src.tags(ns="IMAGE_STRUCTURE")["LAYOUT"] == "COG"
        assert src.count == 1 and src.dtypes == ("float32",)
        np.testing.assert_allclose(src.read(1), result, equal_nan=True)
        assert np.any(src.dataset_mask() == 0)


def test_cloud_mask_and_resolution():
    scene = create_fixture(settings.data_dir / "fixtures" / "cloud")
    masked = read_scene(scene, FIXTURE_GEOMETRY, ["B08", "B11"], sample=True)
    clear = read_scene(scene, FIXTURE_GEOMETRY, ["B08", "B11"], {"cloud_mask": False}, sample=True)
    assert np.isfinite(masked[0]["B08"]).sum() < np.isfinite(clear[0]["B08"]).sum()
    assert masked[1]["transform"].a == 20
    fine = read_scene(scene, FIXTURE_GEOMETRY, ["B08", "B11"], {"resolution_m": 10}, sample=True)
    assert fine[3]["finer_interpolation"]
    for asset in scene["assets"].values():
        if "raster:bands" in asset:
            asset["raster:bands"] = [{}]
    with pytest.raises(ValueError, match="UNKNOWN_CALIBRATION"):
        read_scene(scene, FIXTURE_GEOMETRY, ["B08"], sample=True)


def test_aoi_and_ssrf_rejections():
    _, area = validate_aoi(FIXTURE_GEOMETRY)
    assert 0.2 < area < 0.4
    for geometry in [
        {"type": "Point", "coordinates": [32, -25]},
        {"type": "Polygon", "coordinates": [[[179, 0], [-179, 0], [-179, 1], [179, 0]]]},
        {"type": "Polygon", "coordinates": [[[32, -25], [33, -25], [33, -26], [32, -25]]]},
    ]:
        with pytest.raises(ValueError):
            validate_aoi(geometry)
    for url in ["http://169.254.169.254/latest", "https://localhost/a.tif", "file:///etc/passwd"]:
        with pytest.raises(ValueError):
            allowed_href(url)
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        resolve_asset(
            {"assets": {"one": {"eo:bands": [{"name": "B08"}]}, "two": {"eo:bands": [{"name": "B08"}]}}},
            "B08",
        )


def test_provider_asset_variants_and_visual_are_not_analytic_bands():
    native = {"href": "native.tif", "gsd": 10, "eo:bands": [{"name": "B04"}]}
    item = {
        "assets": {
            "B04_10m": native,
            "B04_20m": {"href": "resampled.tif", "gsd": 20, "eo:bands": [{"name": "B04"}]},
            "visual": {"roles": ["visual"], "eo:bands": [{"name": "B04"}, {"name": "B03"}, {"name": "B02"}]},
        }
    }
    assert resolve_asset(item, "B04") is native


def test_sixty_metre_grid_and_complete_cloud():
    scene = create_fixture(settings.data_dir / "fixtures" / "sixty")
    bands, grid, _, _ = read_scene(scene, FIXTURE_GEOMETRY, ["B01", "B08"], sample=True)
    assert grid["transform"].a == 60
    assert np.isfinite(bands["B01"]).any()
    with rasterio.open(scene["assets"]["SCL"]["href"], "r+") as dst:
        dst.write(np.full((36, 36), 9, dtype="uint8"), 1)
    bands, _, _, _ = read_scene(scene, FIXTURE_GEOMETRY, ["B08"], sample=True)
    assert not np.isfinite(bands["B08"]).any()
