"""Fix the AOI trigger's namespace independently of the caller's search_path.

Revision ID: 0003
"""

from alembic import op

from services.api.config import settings

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    schema = bind.dialect.identifier_preparer.quote(settings.database_schema or "public")
    op.execute(
        f"ALTER FUNCTION {schema}.arcambe_sync_aoi() "
        f"SET search_path = pg_catalog, {schema}, extensions, public"
    )


def downgrade():
    # Retain the fixed namespace when rolling back; do not reintroduce caller control.
    pass
