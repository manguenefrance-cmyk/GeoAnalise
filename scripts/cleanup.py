"""Remove expired products of soft-deleted projects, preserving audit records."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select  # noqa: E402
from services.api.db import Analysis, Artifact, Project, Session  # noqa: E402
from services.api.storage import storage_for  # noqa: E402

cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
with Session() as db:
    artifacts = db.scalars(
        select(Artifact)
        .join(Analysis)
        .join(Project)
        .where(Project.status == "deleted", Project.updated_at < cutoff)
    )
    count = 0
    for artifact in artifacts:
        storage_for(artifact.storage_key).delete(artifact.storage_key)
        db.delete(artifact)
        count += 1
    db.commit()
print(f"Expired artifacts removed: {count}")
