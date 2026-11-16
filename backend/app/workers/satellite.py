"""Celery worker: ingests NASA POWER satellite data every 6 hours and stores daily history."""
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.utils.readings import store_readings
from app.utils.satellite import DISTRICTS, fetch_nasa_power

logger = logging.getLogger(__name__)

BACKFILL_DAYS = 45   # re-fetch a rolling window: fills late-published days and heals gaps


@celery_app.task(name="app.workers.satellite.ingest_nasa_power", bind=True, max_retries=3)
def ingest_nasa_power(self):
    """Fetch the last ~45 days for every district and upsert them (idempotent).
    One failing district no longer aborts the others; failures are retried together."""
    failed: list[str] = []
    stored = 0
    db = SessionLocal()
    try:
        for district in DISTRICTS:
            try:
                data = fetch_nasa_power(district, days_back=BACKFILL_DAYS, use_cache=False)
                if data is None:
                    raise RuntimeError("NASA POWER returned no data")
                stored += store_readings(db, district, data)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                logger.error("Satellite ingest failed for %s: %s", district, exc)
                failed.append(district)
    finally:
        db.close()
    logger.info("Satellite ingest: %d rows upserted, %d/%d districts failed", stored, len(failed), len(DISTRICTS))
    if failed:
        raise self.retry(exc=RuntimeError(f"failed districts: {failed}"), countdown=300)
    return {"rows": stored, "failed": failed}
