"""Celery worker: dispatches pending SMS and push alerts."""
from app.core.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.alerts.dispatch_pending_alerts")
def dispatch_pending_alerts():
    """
    Reads the alert queue from PostgreSQL and sends:
    - SMS via Africa's Talking for feature phone users
    - Push notification via FCM/APNs for app users
    - WebSocket broadcast for active PWA sessions
    """
    # TODO: Query pending alerts from DB
    # TODO: For each alert, call AT SMS API and FCM push
    logger.info("Dispatching pending alerts…")
