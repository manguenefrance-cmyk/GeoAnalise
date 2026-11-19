import ast
import json

import numpy as np
import pytest
from sklearn.decomposition import PCA

from services.processor.engine import pca, ratio, temporal_difference
from services.processor.registry import REGISTRY, ROOT, calculate, interpret
from services.processor.raster import calibration

VECTORS = json.loads((ROOT / "tests/reference_vectors.json").read_text())
CASES = [
    (v["id"], v["bands"], key, value) for v in VECTORS["vectors"] for key, value in v["expected"].items()
]


@pytest.mark.parametrize("name,bands,key,expected", CASES, ids=[f"{c[0]}-{c[2]}" for c in CASES])
def test_all_reference_vectors(name, bands, key, expected):
    assert float(calculate(key, bands)) == pytest.approx(expected, abs=VECTORS["tolerance"])


def test_catalog_complete_and_safe():
    assert len(REGISTRY) == 21
    for formula in [
        "__import__('os').system('x')",
        "B08[0]",
        "B08.__class__",
        "sqrt(B08, B04)",
        "B08 ** 100000",
    ]:
        with pytest.raises(ValueError):
            interpret(ast.parse(formula, mode="eval"), {"B08": np.array([0.5]), "B04": np.array([0.2])})


def test_masks_and_unbounded_ratio():
    bands = {"B08": np.array([0.5, 0.2, np.nan, -0.1]), "B04": np.array([0.1, 0, 0.1, 0.1])}
    result = ratio(bands, "B08", "B04")
    assert result[0] == 5
    assert np.isnan(result[1:3]).all()
    assert result[3] == -1
    assert np.isnan(calculate("NDVI", bands)[3])
    assert np.isnan(calculate("MSAVI2", {"B08": 0, "B04": -1}))


@pytest.mark.parametrize(
    "pipeline,metadata,kwargs,raw",
    [
        ("safe", {"nodata": 0}, {"safe_offset": 0, "quantification": 10000}, 2000),
        ("safe", {"nodata": 0}, {"safe_offset": -1000, "quantification": 10000}, 3000),
        ("stac", {"scale": 0.0001, "offset": -0.1, "nodata": 0}, {}, 3000),
        ("normalized", {}, {}, 0.2),
    ],
)
def test_calibration_baselines(pipeline, metadata, kwargs, raw):
    assert float(calibration(raw, metadata, pipeline, **kwargs)) == pytest.approx(0.2, abs=1e-6)


def test_calibration_no_double_scaling():
    assert np.isnan(calibration(0, {"scale": 0.0001, "offset": -0.1, "nodata": 0}))
    assert float(calibration(500, {"scale": 0.0001, "offset": -0.1})) < 0
    assert float(calibration(15000, {"scale": 0.0001, "offset": -0.1})) > 1
    with pytest.raises(ValueError, match="UNKNOWN_CALIBRATION"):
        calibration(1000, {})
    with pytest.raises(ValueError, match="DOUBLE_CALIBRATION"):
        calibration(0.2, {"scale": 0.0001}, "normalized")


@pytest.mark.parametrize("standardize", [False, True])
def test_pca_matches_sklearn(standardize):
    rng = np.random.default_rng(42)
    bands = {f"B0{i + 2}": rng.normal(size=(20, 30)) for i in range(3)}
    bands["B02"][0, 0] = np.nan
    selected = list(bands)
    data, meta = pca(bands, selected, standardize)
    matrix = np.stack(list(bands.values()))[:, 1:, :].reshape(3, -1).T
    # Use exact valid intersection, including the rest of the first row.
    cube = np.stack(list(bands.values()))
    matrix = cube[:, np.all(np.isfinite(cube), axis=0)].T
    matrix = (matrix - meta["means"]) / meta["scales"]
    model = PCA().fit(matrix)
    np.testing.assert_allclose(meta["explained_variance_ratio"], model.explained_variance_ratio_, atol=1e-10)
    assert sum(meta["explained_variance_ratio"]) == pytest.approx(1)
    assert np.isnan(data[:, 0, 0]).all()
    np.testing.assert_array_equal(pca(bands, selected, standardize)[0], data)


def test_temporal_difference():
    result = temporal_difference(np.array([[0.2, np.nan]]), np.array([[0.5, 0.3]]))
    assert result[0, 0] == pytest.approx(0.3)
    assert np.isnan(result[0, 1])
