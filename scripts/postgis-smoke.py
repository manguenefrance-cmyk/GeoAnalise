import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402
from services.api.db import engine  # noqa: E402

with engine.connect() as connection:
    assert connection.execute(text("SELECT PostGIS_Version()")).scalar()
    assert (
        connection.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = 'aoi_geom_gist'")).scalar()
        == 1
    )
print("PostGIS migration and spatial index verified")
