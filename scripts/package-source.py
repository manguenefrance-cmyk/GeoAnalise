"""Build a source-only handoff; exclude runtime data, private env files and dependencies."""

import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = json.loads((root / "apps/web/package.json").read_text(encoding="utf-8-sig"))["version"]
destination = root / "dist-delivery"
destination.mkdir(exist_ok=True)
archive = destination / f"ARCAMBE_GeoAnalytics_v{version}_source.zip"
excluded = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "data",
    "artifacts",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist-delivery",
    "test-results",
    "pytest-results.xml",
    ".terraform",
    "credentials",
    "secrets",
}
allowed = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".ts",
    ".tsx",
    ".css",
    ".mjs",
    ".ini",
    ".ps1",
    ".jpg",
    ".png",
    ".xml",
    ".tf",
    ".toml",
    ".svg",
}
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts) or not path.is_file():
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        if path.name.startswith("maplibre-gl-") or path.name.endswith(".tsbuildinfo"):
            continue
        if path.suffix not in allowed and path.name not in {
            ".gitignore",
            ".dockerignore",
            "python.Dockerfile",
            "web.Dockerfile",
            "Caddyfile",
            ".env.example",
        }:
            continue
        bundle.write(path, Path("ARCAMBE_GeoAnalytics") / relative)
with archive.open("rb") as source:
    digest = hashlib.file_digest(source, "sha256").hexdigest()
(destination / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size, "sha256": digest}))
