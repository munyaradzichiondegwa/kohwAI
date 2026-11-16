"""Celery worker: evaluates parametric insurance payout triggers daily."""
import logging
from datetime import date

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.musika import InsuranceEnrollment
from app.modules.musika import insurance_service as ins

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.insurance.check_drought_payouts")
def check_drought_payouts():
    """For every (district, season) that has active enrolments, apply the trigger rules in
    insurance_service.evaluate_district_payout (season window, N consecutive days, waiting
    period, one payout per enrolment). Safe to run repeatedly: it is idempotent."""
    db = SessionLocal()
    results = {}
    try:
        today = date.today()
        pairs = (db.query(InsuranceEnrollment.district, InsuranceEnrollment.season)
                 .filter(InsuranceEnrollment.is_active.is_(True)).distinct().all())
        for district, season in pairs:
            try:
                res = ins.evaluate_district_payout(db, district, season, today=today)
                results[f"{district}/{season}"] = res.get("payouts_created", 0) if res.get("triggered") else res.get("reason")
                if res.get("triggered"):
                    logger.info("Insurance trigger met for %s %s: %s", district, season, res)
            except Exception:  # noqa: BLE001
                db.rollback()
                logger.exception("Insurance evaluation failed for %s %s", district, season)
    finally:
        db.close()
    return results
