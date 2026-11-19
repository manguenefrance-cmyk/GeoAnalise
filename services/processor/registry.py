"""Versioned, validated catalog. Formulas are interpreted through a small whitelist."""

import ast
import json
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
CATALOG = yaml.safe_load((ROOT / "contracts/spectral_indices.yaml").read_text(encoding="utf-8"))
BANDS = {"B01": 60, "B09": 60, **CATALOG["band_native_resolution_m"]}
EPSILON = float(CATALOG["processing"]["denominator_epsilon"])
REGISTRY = {item["id"]: item for item in CATALOG["indices"]}
TRANSLATIONS = json.loads((ROOT / "contracts/index_descriptions.pt.json").read_text(encoding="utf-8"))
for index_id, translation in TRANSLATIONS.items():
    REGISTRY[index_id].update(translation)


def divide(a, b):
    a, b = np.broadcast_arrays(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64))
    return np.divide(a, b, out=np.full(a.shape, np.nan), where=np.abs(b) >= EPSILON)


def safe_sqrt(value):
    value = np.asarray(value, dtype=np.float64)
    return np.sqrt(np.where(value >= -1e-12, np.maximum(value, 0), np.nan))


def interpret(node, values):
    if isinstance(node, ast.Expression):
        return interpret(node.body, values)
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = interpret(node.operand, values)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        a, b = interpret(node.left, values), interpret(node.right, values)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.Div):
            return divide(a, b)
        if isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant) and node.right.value == 2:
            return a**2
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "sqrt"
        and len(node.args) == 1
        and not node.keywords
    ):
        return safe_sqrt(interpret(node.args[0], values))
    raise ValueError("UNSUPPORTED_FORMULA_NODE")


TREES = {}
for key, item in REGISTRY.items():
    if len(set(item["bands"])) != len(item["bands"]) or not set(item["bands"]) <= set(BANDS):
        raise ValueError(f"Invalid catalog bands: {key}")
    if item["native_output_resolution_m"] != max(BANDS[b] for b in item["bands"]):
        raise ValueError(f"Invalid catalog resolution: {key}")
    if item["input"] != "calibrated_surface_reflectance" or not item.get("notes"):
        raise ValueError(f"Incomplete catalog: {key}")
    tree = ast.parse(item["formula"].replace("^", "**"), mode="eval")
    interpret(tree, {**{b: np.array([0.1]) for b in item["bands"]}, **item.get("constants", {})})
    TREES[key] = tree


def calculate(index_id, bands, constants=None):
    if index_id not in REGISTRY:
        raise ValueError("UNKNOWN_INDEX")
    item = REGISTRY[index_id]
    if not set(item["bands"]) <= bands.keys():
        raise ValueError("MISSING_BANDS")
    defaults = item.get("constants", {})
    constants = constants or {}
    if not constants.keys() <= defaults.keys():
        raise ValueError("INVALID_CONSTANT")
    if "L" in constants and not 0 <= float(constants["L"]) <= 1:
        raise ValueError("INVALID_SAVI_L")
    values = {b: np.asarray(bands[b], dtype=np.float64) for b in item["bands"]}
    with np.errstate(all="ignore"):
        output = np.asarray(interpret(TREES[index_id], {**values, **defaults, **constants}), dtype=np.float32)
    return np.where(np.isfinite(output), output, np.nan).astype(np.float32)
