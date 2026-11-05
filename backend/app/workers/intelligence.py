"""Celery worker: runs the district-wide cross-pillar rules on a schedule
(previously they only ran when an admin hit POST /intelligence/evaluate/district by hand)."""
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.modules.intelligence import service
from app.utils.satellite import DISTRICTS

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.intelligence.evaluate_districts")
def evaluate_districts():
    db = SessionLocal()
    out = {"pest_outbreaks": 0, "rains_onset": 0, "errors": 0}
    try:
        for district in DISTRICTS:
            try:
                if service.evaluate_pest_outbreak(db, district):
                    out["pest_outbreaks"] += 1
                if service.evaluate_rains_onset(db, district):
                    out["rains_onset"] += 1
            except Exception:  # noqa: BLE001
                db.rollback()
                out["errors"] += 1
                logger.exception("District rule evaluation failed for %s", district)
    finally:
        db.close()
    return out
