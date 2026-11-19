"""Initial relational schema and PostGIS AOI mirror.

Revision ID: 0001
"""

from alembic import op
from services.api.db import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute("ALTER TABLE aoi ADD COLUMN geom geometry(MultiPolygon,4326)")
        op.execute("UPDATE aoi SET geom = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(geometry::text),4326))")
        op.execute("ALTER TABLE aoi ALTER COLUMN geom SET NOT NULL")
        op.execute("CREATE INDEX aoi_geom_gist ON aoi USING GIST(geom)")
        op.execute("""CREATE FUNCTION arcambe_sync_aoi() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN NEW.geom := ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(NEW.geometry::text),4326));
            IF NOT ST_IsValid(NEW.geom) THEN RAISE EXCEPTION 'Invalid AOI'; END IF;
            RETURN NEW; END; $$""")
        op.execute(
            "CREATE TRIGGER aoi_sync BEFORE INSERT OR UPDATE OF geometry ON aoi FOR EACH ROW EXECUTE FUNCTION arcambe_sync_aoi()"
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS aoi_sync ON aoi")
        op.execute("DROP FUNCTION IF EXISTS arcambe_sync_aoi()")
    Base.metadata.drop_all(op.get_bind())
