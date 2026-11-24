"""CI-only: verify the isolated hosted schema and deny a browser database role."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import DBAPIError  # noqa: E402
from services.api.config import settings  # noqa: E402
from services.api.db import Base, engine  # noqa: E402

assert settings.app_env == "test" and settings.database_schema == "arcambe"
with engine.begin() as db:
    for role in ("anon", "authenticated"):
        if not db.execute(text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}).scalar():
            db.execute(text(f"CREATE ROLE {role} NOLOGIN"))
command.upgrade(Config("alembic.ini"), "head")
command.upgrade(Config("alembic.ini"), "head")  # Restart must be idempotent.
with engine.connect() as db:
    tables = db.execute(text(
        "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='arcambe'"
    )).all()
    app_tables = {table.name for table in Base.metadata.sorted_tables}
    assert {name for name, _ in tables} == app_tables | {"alembic_version"}
    assert all(rls for name, rls in tables if name in app_tables)
    assert db.execute(text("SELECT PostGIS_Version()")).scalar()
    assert db.execute(text(
        "SELECT count(*) FROM pg_indexes WHERE schemaname='arcambe' AND indexname='aoi_geom_gist'"
    )).scalar() == 1
    function_config = db.execute(text(
        "SELECT proconfig FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE n.nspname='arcambe' AND p.proname='arcambe_sync_aoi'"
    )).scalar()
    assert any(value.startswith("search_path=pg_catalog, arcambe,") for value in function_config)
    for role in ("anon", "authenticated"):
        assert not db.execute(text(
            "SELECT has_schema_privilege(:role, 'arcambe', 'USAGE')"
        ), {"role": role}).scalar()
        assert not db.execute(text(
            "SELECT has_table_privilege(:role, 'arcambe.users', 'SELECT')"
        ), {"role": role}).scalar()
for role in ("anon", "authenticated"):
    with engine.connect() as db:
        db.execute(text(f"SET ROLE {role}"))
        try:
            db.execute(text("SELECT * FROM arcambe.users"))
        except DBAPIError:
            db.rollback()
        else:
            raise AssertionError("Browser role could read application identities")
print("Hosted schema, PostGIS, RLS and browser-role denial verified")
