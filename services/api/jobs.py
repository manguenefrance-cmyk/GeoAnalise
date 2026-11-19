"""Database-backed queue: claim and settle under row locks; no in-process task loss."""

import hashlib
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import numpy as np
import rasterio
from services import __version__
from sqlalchemy import select, text

from services.processor.engine import composite, pca, ratio, statistics, temporal_difference
from services.processor.exports import export_products
from services.processor.raster import read_scene
from services.processor.registry import REGISTRY, calculate
from services.processor.sensors import SENTINEL, native_bands, native_formula
from .config import settings
from .db import AOI, Analysis, Artifact, Audit, Job, Organization, Scene, Session, Usage, now
from .storage import storage_for

logger = logging.getLogger("arcambe.worker")


@contextmanager
def locked(db, organization_id=None):
    db.rollback()
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    elif organization_id:
        db.execute(select(Organization).where(Organization.id == organization_id).with_for_update())
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise


def settle(db, job, state, error=None):
    analysis = db.get(Analysis, job.analysis_id)
    job.status = analysis.status = state
    job.error_code, job.finished_at = error, now()
    usage = db.scalar(select(Usage).where(Usage.analysis_id == analysis.id))
    usage.status = "settled" if state == "succeeded" else "refunded"
    db.add(
        Audit(organization_id=job.organization_id, actor="worker", action=f"job.{state}", resource_id=job.id)
    )


def claim_next():
    with Session() as db:
        with locked(db):
            # Recover orphaned executions truthfully. A retry is a new idempotent request.
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
            for stale in db.scalars(select(Job).where(Job.status == "running", Job.started_at < cutoff)):
                settle(db, stale, "failed", "WORKER_LEASE_EXPIRED")
            stmt = select(Job).where(Job.status == "queued").order_by(Job.created_at).limit(1)
            if db.bind.dialect.name != "sqlite":
                stmt = stmt.with_for_update(skip_locked=True)
            job = db.scalar(stmt)
            if not job:
                return None
            if job.cancel_requested:
                settle(db, job, "cancelled")
                return None
            job.status, job.started_at, job.attempt = "running", now(), job.attempt + 1
            db.get(Analysis, job.analysis_id).status = "running"
            return job.id


def run_job(job_id):
    with Session() as db:
        published = []
        job = db.get(Job, job_id)
        analysis = db.get(Analysis, job.analysis_id)
        aoi = db.get(AOI, analysis.aoi_id)
        try:
            extra = {}
            if analysis.operation_kind == "temporal_diff":
                from rasterio.enums import Resampling
                from rasterio.warp import reproject

                previous = [db.get(Analysis, i) for i in analysis.input_analysis_ids]
                if len(previous) != 2 or any(a.status != "succeeded" for a in previous):
                    raise ValueError("TWO_SUCCESSFUL_INPUTS_REQUIRED")
                if previous[0].provenance.get("sensor", SENTINEL) != previous[1].provenance.get(
                    "sensor", SENTINEL
                ):
                    raise ValueError("CROSS_SENSOR_TEMPORAL_COMPARISON_REQUIRES_HARMONIZATION")
                if (
                    previous[0].operation_kind != "index"
                    or previous[1].operation_kind != "index"
                    or previous[0].operation_id != previous[1].operation_id
                ):
                    raise ValueError("TEMPORAL_SEMANTICS_MISMATCH")
                if previous[0].aoi_id != analysis.aoi_id or previous[1].aoi_id != analysis.aoi_id:
                    raise ValueError("TEMPORAL_AOI_MISMATCH")
                dates = [a.provenance.get("acquired_at") for a in previous]
                if not all(dates) or dates[1] <= dates[0]:
                    raise ValueError("TEMPORAL_ORDER_REQUIRED")
                reference = max(previous, key=lambda a: a.provenance["resolution_m"])
                ref_file = db.scalar(
                    select(Artifact).where(
                        Artifact.analysis_id == reference.id, Artifact.artifact_type == "cog"
                    )
                )
                with rasterio.open(
                    storage_for(ref_file.storage_key).raster_location(ref_file.storage_key)
                ) as src:
                    grid = {
                        "crs": src.crs,
                        "transform": src.transform,
                        "width": src.width,
                        "height": src.height,
                    }
                arrays = []
                for source in previous:
                    artifact = db.scalar(
                        select(Artifact).where(
                            Artifact.analysis_id == source.id, Artifact.artifact_type == "cog"
                        )
                    )
                    with rasterio.open(
                        storage_for(artifact.storage_key).raster_location(artifact.storage_key)
                    ) as src:
                        output = np.full((grid["height"], grid["width"]), np.nan, dtype="float32")
                        reproject(
                            rasterio.band(src, 1),
                            output,
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=grid["transform"],
                            dst_crs=grid["crs"],
                            src_nodata=np.nan,
                            dst_nodata=np.nan,
                            resampling=Resampling.bilinear,
                        )
                        arrays.append(output)
                result = temporal_difference(*arrays)
                provenance = {
                    **reference.provenance,
                    "temporal_inputs": [a.id for a in previous],
                    "acquisition_dates": dates,
                    "acquired_at": dates[1],
                    "formula": "date2 - date1",
                    "interpolation": "bilinear",
                    "sample": any(a.provenance.get("sample") for a in previous),
                }
                domain = np.any(np.stack([np.isfinite(a) for a in arrays]), axis=0)
            else:
                scene = db.get(Scene, analysis.scene_id)
                params = analysis.params
                if analysis.operation_kind == "index":
                    selected = REGISTRY[analysis.operation_id]["bands"]
                elif analysis.operation_kind == "band_ratio":
                    selected = [params.get("numerator", "B08"), params.get("denominator", "B04")]
                else:
                    selected = params.get("bands", ["B04", "B03", "B02"])
                bands, grid, domain, provenance = read_scene(
                    scene.item, aoi.geometry, selected, params, scene.sample
                )
                if analysis.operation_kind == "index":
                    result = calculate(analysis.operation_id, bands, params.get("constants"))
                    extra = {
                        "formula": native_formula(
                            REGISTRY[analysis.operation_id]["formula"], provenance["sensor"]
                        ),
                        "constants": {
                            **REGISTRY[analysis.operation_id].get("constants", {}),
                            **params.get("constants", {}),
                        },
                    }
                elif analysis.operation_kind == "band_ratio":
                    result = ratio(bands, *selected)
                    extra = {
                        "formula": native_formula(f"{selected[0]} / {selected[1]}", provenance["sensor"])
                    }
                elif analysis.operation_kind == "pca":
                    result, extra = pca(bands, selected, params.get("standardize", False))
                elif analysis.operation_kind == "composite":
                    result = composite(bands, selected)
                    extra = {"bands": selected, "visual_stretch": "2-98 percentile; COG retains reflectance"}
                else:
                    raise ValueError("UNKNOWN_OPERATION")
            if "bands" in extra:
                names = native_bands(provenance["sensor"])
                extra["bands"] = [names[b] for b in extra["bands"]]
            if not np.isfinite(result).any():
                raise ValueError("NO_VALID_PIXELS_ADJUST_AOI_OR_CLOUD_MASK")
            stats = statistics(result, domain)
            first_stats = stats[0] if isinstance(stats, list) else stats
            warnings = []
            if first_stats["valid_fraction"] < 0.5:
                warnings.append("LOW_VALID_FRACTION")
            if provenance.get("finer_interpolation"):
                warnings.append("FINER_GRID_IS_INTERPOLATION")
            if np.any((result < -1) | (result > 1)):
                warnings.append("VALUES_OUTSIDE_NOMINAL_RANGE_PRESERVED")
            provenance.update(
                {
                    "analysis_id": analysis.id,
                    "operation_kind": analysis.operation_kind,
                    "operation_id": analysis.operation_id,
                    "algorithm_version": "1.0.0",
                    "software_version": __version__,
                    "rasterio_version": rasterio.__version__,
                    "numpy_version": np.__version__,
                    "generated_at": now(),
                    "area_km2": aoi.area_km2,
                    "warnings": warnings,
                    "statistics": stats,
                    "model": extra,
                    "denominator_epsilon": 1e-6,
                }
            )
            directory = settings.data_dir / "artifacts" / analysis.id
            products = export_products(directory, result, grid, provenance, analysis.operation_id)
            store = storage_for()
            for kind, filename, mime in products:
                key = store.publish(directory / filename, analysis.organization_id, analysis.id, mime)
                published.append((kind, filename, mime, key))
            db.rollback()
            with locked(db, job.organization_id):
                job = db.get(Job, job_id, populate_existing=True)
                if job.status != "running":
                    return
                if job.cancel_requested:
                    settle(db, job, "cancelled")
                    return
                analysis = db.get(Analysis, job.analysis_id, populate_existing=True)
                analysis.provenance, analysis.stats = (
                    provenance,
                    {"bands": stats} if isinstance(stats, list) else stats,
                )
                for kind, filename, mime, storage_key in published:
                    path = directory / filename
                    db.add(
                        Artifact(
                            organization_id=analysis.organization_id,
                            analysis_id=analysis.id,
                            artifact_type=kind,
                            storage_key=storage_key,
                            mime_type=mime,
                            bytes=path.stat().st_size,
                            checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
                        )
                    )
                settle(db, job, "succeeded")
        except Exception as exc:
            db.rollback()
            # Do not expose credentials, signed URLs, filesystem paths or provider responses.
            code = (
                str(exc)
                if isinstance(exc, ValueError) and str(exc).isupper() and len(str(exc)) < 100
                else "PROCESSING_FAILED_CHECK_PROVIDER_ACCESS"
            )
            logger.warning("job_failed job_id=%s code=%s exception_type=%s", job_id, code, type(exc).__name__)
            with locked(db, job.organization_id):
                job = db.get(Job, job_id, populate_existing=True)
                if job.status == "running":
                    settle(db, job, "cancelled" if job.cancel_requested else "failed", code)
        finally:
            # Remove uploaded products which no transaction made visible to the user.
            with Session() as cleanup_db:
                for _, _, _, key in published:
                    if not cleanup_db.scalar(select(Artifact.id).where(Artifact.storage_key == key).limit(1)):
                        try:
                            storage_for(key).delete(key)
                        except Exception as cleanup_error:
                            logger.warning(
                                "artifact_cleanup_failed job_id=%s type=%s",
                                job_id,
                                type(cleanup_error).__name__,
                            )


def work_once():
    job_id = claim_next()
    if job_id:
        run_job(job_id)
    return job_id


def main():
    settings.validate_runtime()
    if settings.app_env == "test":
        from .db import Base, engine

        Base.metadata.create_all(engine)
    logging.basicConfig(level=logging.INFO)
    logger.info("ARCAMBE worker starting env=%s", settings.app_env)
    while True:
        if not work_once():
            time.sleep(1)


if __name__ == "__main__":
    main()
