"""Start the free hosted test profile: migrate, then one API with a queue consumer."""

import logging
import os

from .config import settings


def validate_hosted():
    settings.validate_runtime()
    if settings.app_env != "production" or settings.storage_backend != "supabase":
        raise RuntimeError("Hosted tests require production authentication and private Supabase storage")
    if settings.database_schema != "arcambe":
        raise RuntimeError("Hosted tests require DATABASE_SCHEMA=arcambe")
    if not settings.worker_embedded:
        raise RuntimeError("Hosted tests require WORKER_EMBEDDED=true")
    if settings.max_pixels > 250_000 or settings.max_artifact_bytes > 50_000_000:
        raise RuntimeError("Hosted test limits exceeded: 250000 pixels and 50000000 bytes per artifact")


def main():
    from alembic import command
    from alembic.config import Config
    import firebase_admin
    import uvicorn

    from .storage import storage_for

    validate_hosted()
    logging.basicConfig(level=logging.INFO)
    # Credentials are loaded from the host's private secret file, never from the browser.
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
    firebase_admin.get_app().credential.get_credential()
    storage_for().private_bucket()
    command.upgrade(Config("alembic.ini"), "head")
    uvicorn.run(
        "services.api.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")),
        workers=1, proxy_headers=False,
    )


if __name__ == "__main__":
    main()
