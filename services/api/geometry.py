import math

from pyproj import Geod
from shapely.geometry import mapping, shape
from shapely.geometry.polygon import orient


def validate_aoi(geometry, max_area=100):
    try:
        geom = shape(geometry)
    except Exception as exc:
        raise ValueError("INVALID_GEOMETRY") from exc
    if geom.geom_type not in ("Polygon", "MultiPolygon") or geom.is_empty or not geom.is_valid:
        raise ValueError("INVALID_POLYGON")
    polygons = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    rings = [r for p in polygons for r in [p.exterior, *p.interiors]]
    count = 0
    for ring in rings:
        coords = list(ring.coords)
        count += len(coords)
        for a, b in zip(coords, coords[1:]):
            if (
                len(a) != 2
                or not all(math.isfinite(v) for v in a)
                or not -180 <= a[0] <= 180
                or not -80 <= a[1] <= 84
            ):
                raise ValueError("UNSUPPORTED_COORDINATES")
            if abs(a[0] - b[0]) > 180:
                raise ValueError("ANTIMERIDIAN_UNSUPPORTED")
    if count > 10000:
        raise ValueError("TOO_MANY_VERTICES")
    west, _, east, _ = geom.bounds
    if int((west + 180) // 6) != int((east + 180) // 6):
        raise ValueError("UTM_ZONE_CROSSING_UNSUPPORTED")
    geod = Geod(ellps="WGS84")
    area = sum(abs(geod.geometry_area_perimeter(orient(p, sign=1))[0]) for p in polygons) / 1e6
    if not 0 < area <= max_area:
        raise ValueError("AOI_AREA_LIMIT")
    return mapping(geom), area


def read_shapefile_zip(content):
    """Read in memory, never extract user-controlled paths onto the filesystem."""
    import io
    import zipfile
    from pathlib import PurePosixPath

    import shapefile
    from pyproj import CRS, Transformer
    from shapely.ops import transform, unary_union

    if len(content) > 5_000_000:
        raise ValueError("UPLOAD_TOO_LARGE")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > 20 or sum(i.file_size for i in members) > 20_000_000:
                raise ValueError("ZIP_LIMIT_EXCEEDED")
            parts = {}
            stems = set()
            for item in members:
                name = item.filename.replace("\\", "/")
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts or ":" in name or item.flag_bits & 1:
                    raise ValueError("UNSAFE_ZIP")
                if item.is_dir():
                    continue
                if item.compress_size and item.file_size / item.compress_size > 200:
                    raise ValueError("ZIP_COMPRESSION_LIMIT")
                if path.suffix.lower() in (".shp", ".shx", ".dbf", ".prj"):
                    if path.suffix.lower() in parts:
                        raise ValueError("AMBIGUOUS_SHAPEFILE")
                    stems.add(str(path.with_suffix("")))
                    parts[path.suffix.lower()] = archive.read(item)
            if set(parts) != {".shp", ".shx", ".dbf", ".prj"} or len(stems) != 1:
                raise ValueError("SHAPEFILE_REQUIRES_SHP_SHX_DBF_PRJ")
            source = CRS.from_wkt(parts[".prj"].decode("utf-8"))
            reader = shapefile.Reader(
                shp=io.BytesIO(parts[".shp"]), shx=io.BytesIO(parts[".shx"]), dbf=io.BytesIO(parts[".dbf"])
            )
            if reader.numRecords > 100:
                raise ValueError("TOO_MANY_FEATURES")
            geom = unary_union([shape(s.__geo_interface__) for s in reader.shapes()])
            geom = transform(Transformer.from_crs(source, 4326, always_xy=True).transform, geom)
            return mapping(geom)
    except (zipfile.BadZipFile, OSError, UnicodeError) as exc:
        raise ValueError("INVALID_SHAPEFILE_ZIP") from exc
