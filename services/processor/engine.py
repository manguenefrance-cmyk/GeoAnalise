import numpy as np

from .registry import BANDS, divide


def ratio(bands, numerator, denominator):
    if numerator not in BANDS or denominator not in BANDS:
        raise ValueError("INVALID_BAND")
    return divide(bands[numerator], bands[denominator]).astype(np.float32)


def temporal_difference(earlier, later):
    if earlier.shape != later.shape:
        raise ValueError("GRID_ALIGNMENT_REQUIRED")
    return (later.astype(np.float64) - earlier).astype(np.float32)


def pca(bands, selected, standardize=False, max_samples=100000, seed=0):
    if not 3 <= len(selected) <= 10 or len(set(selected)) != len(selected):
        raise ValueError("PCA_REQUIRES_3_TO_10_DISTINCT_BANDS")
    cube = np.stack([bands[b] for b in selected]).astype(np.float64)
    valid = np.all(np.isfinite(cube), axis=0)
    matrix = cube[:, valid].T
    if len(matrix) < len(selected) + 1:
        raise ValueError("INSUFFICIENT_VALID_PIXELS")
    fit = matrix
    if len(matrix) > max_samples:
        fit = matrix[np.random.default_rng(seed).choice(len(matrix), max_samples, replace=False)]
    means = fit.mean(axis=0)
    scales = fit.std(axis=0, ddof=1) if standardize else np.ones(len(selected))
    if np.any(scales < 1e-12):
        raise ValueError("PCA_CONSTANT_BAND")
    centered = (fit - means) / scales
    _, singular, vectors = np.linalg.svd(centered, full_matrices=False)
    for row in vectors:
        if row[np.argmax(np.abs(row))] < 0:
            row *= -1
    variance = singular**2 / (len(fit) - 1)
    if variance.sum() < 1e-15:
        raise ValueError("PCA_ZERO_VARIANCE")
    projected = ((matrix - means) / scales) @ vectors.T
    result = np.full(cube.shape, np.nan, dtype=np.float32)
    result[:, valid] = projected.T
    metadata = {
        "bands": selected,
        "means": means.tolist(),
        "scales": scales.tolist(),
        "eigenvectors": vectors.tolist(),
        "explained_variance": variance.tolist(),
        "explained_variance_ratio": (variance / variance.sum()).tolist(),
        "sample_count": len(fit),
        "seed": seed,
        "standardize": standardize,
        "inverse_mapping": "reflectance = (PC @ eigenvectors) * scales + means",
    }
    return result, metadata


def composite(bands, selected):
    if len(selected) != 3 or not set(selected) <= BANDS.keys():
        raise ValueError("COMPOSITE_REQUIRES_3_BANDS")
    # Preserve reflectance in the output COG; stretch only the displayed preview.
    return np.stack([bands[b] for b in selected]).astype(np.float32)


def statistics(data, domain_mask=None):
    if data.ndim == 3:
        return [statistics(band, domain_mask) for band in data]
    valid = data[np.isfinite(data)]
    total = int(domain_mask.sum()) if domain_mask is not None else data.size
    if not valid.size:
        return {
            "count": 0,
            "valid_fraction": 0,
            "masked_fraction": 1,
            "histogram": {"counts": [], "edges": []},
        }
    counts, edges = np.histogram(valid, bins=24)
    return {
        "count": int(valid.size),
        "valid_fraction": float(valid.size / max(total, 1)),
        "masked_fraction": float(1 - valid.size / max(total, 1)),
        "min": float(valid.min()),
        "max": float(valid.max()),
        "mean": float(valid.mean()),
        "median": float(np.median(valid)),
        "std": float(valid.std()),
        "percentiles": np.percentile(valid, [2, 25, 75, 98]).tolist(),
        "histogram": {"counts": counts.tolist(), "edges": edges.tolist()},
    }
