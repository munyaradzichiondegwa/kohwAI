from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "kohwai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.satellite",
        "app.workers.risk_model",
        "app.workers.alerts",
        "app.workers.insurance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Harare",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    # Ingest NASA POWER weather data every 6 hours
    "ingest-satellite-data": {
        "task": "app.workers.satellite.ingest_nasa_power",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Daily livestock disease risk model update
    "run-risk-model": {
        "task": "app.workers.risk_model.calculate_district_risk_scores",
        "schedule": crontab(minute=0, hour=2),
    },
    # Check insurance payout triggers daily
    "check-insurance-triggers": {
        "task": "app.workers.insurance.check_drought_payouts",
        "schedule": crontab(minute=30, hour=2),
    },
    # Dispatch pending alerts every 5 minutes
    "dispatch-alerts": {
        "task": "app.workers.alerts.dispatch_pending_alerts",
        "schedule": crontab(minute="*/5"),
    },
}
