from alembic import context
from services.api.db import Base, engine
from services.api.config import settings
from sqlalchemy import text

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(url=str(engine.url), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        if settings.database_schema:
            if settings.database_schema in ("public", "extensions", "auth", "storage", "pg_catalog"):
                raise RuntimeError("Choose a dedicated application database schema")
            schema = connection.dialect.identifier_preparer.quote(settings.database_schema)
            with connection.begin():
                connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True,
            version_table_schema=settings.database_schema or None,
        )
        with context.begin_transaction():
            context.run_migrations()
