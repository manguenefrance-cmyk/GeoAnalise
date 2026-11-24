"""Keep hosted application tables inaccessible to Supabase's public Data API.

Revision ID: 0002
"""

from alembic import op
from sqlalchemy import text

from services.api.config import settings
from services.api.db import Base

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql" or not settings.database_schema:
        return
    quote = bind.dialect.identifier_preparer.quote
    schema = quote(settings.database_schema)
    roles = ["PUBLIC"]
    for role in ("anon", "authenticated"):
        if bind.execute(text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}).scalar():
            roles.append(quote(role))
    for role in roles:
        op.execute(f"REVOKE ALL ON SCHEMA {schema} FROM {role}")
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema} FROM {role}")
        op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA {schema} FROM {role}")
        op.execute(f"REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {schema} FROM {role}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} REVOKE ALL ON TABLES FROM {role}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} REVOKE ALL ON FUNCTIONS FROM {role}")
    for table in Base.metadata.sorted_tables:
        op.execute(f"ALTER TABLE {schema}.{quote(table.name)} ENABLE ROW LEVEL SECURITY")
    # No browser policies: the backend table owner checks Firebase and tenant membership.


def downgrade():
    # Deliberately retain access restrictions. A downgrade must never expose tenant data.
    pass
