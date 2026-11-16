"""Celery worker: dispatches pending alerts (real-time push + SMS)."""
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.modules.alerts import dispatch
from app.utils.sms import gateway_configured

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.alerts.dispatch_pending_alerts")
def dispatch_pending_alerts():
    """1) push new alerts to connected sessions; 2) SMS severe ones to opted-in, consented farmers in the district.
    Safe to run repeatedly and concurrently (row locks + one delivery row per farmer per alert)."""
    db = SessionLocal()
    summary: dict = {"broadcast": 0, "sms": []}
    try:
        summary["broadcast"] = dispatch.broadcast_realtime(db)
        if not gateway_configured():
            logger.info("Alert SMS skipped: no SMS gateway configured (AT_API_KEY). Real-time push still ran.")
            summary["sms_skipped"] = "no_gateway"
            return summary
        for alert in dispatch.pending_alerts(db):
            try:
                summary["sms"].append(dispatch.dispatch_alert(db, alert))
            except Exception:  # noqa: BLE001
                db.rollback()
                logger.exception("Dispatch failed for alert %s", alert.id)
    finally:
        db.close()
    logger.info("Alert dispatch: %s", summary)
    return summary
