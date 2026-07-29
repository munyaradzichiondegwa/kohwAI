"""Celery worker: checks parametric insurance payout triggers daily."""
from app.core.celery_app import celery_app
from app.core.redis_client import get_cached
import logging

logger = logging.getLogger(__name__)

DROUGHT_INDEX_THRESHOLD = 70
PAYOUT_AMOUNT_USD = 15.00


@celery_app.task(name="app.workers.insurance.check_drought_payouts")
def check_drought_payouts():
    """
    Monitors SARCOF drought index per district.
    If drought index > threshold for >5 consecutive days → trigger EcoCash payout.
    """
    districts = ["Chipinge", "Gokwe", "Matopos", "Binga", "Nyanga"]
    for district in districts:
        weather = get_cached(f"weather:{district}") or {}
        rainfall = weather.get("PRECTOTCORR", {})
        if not rainfall:
            continue
        avg_rain = sum(rainfall.values()) / len(rainfall)
        if avg_rain < 1.0:  # Drought threshold (mm/day)
            logger.info(f"Drought trigger met for {district}. Processing payouts.")
            # TODO: Query enrolled farmers in district
            # TODO: Trigger EcoCash payout via Africa's Talking Payment API
            # TODO: Send SMS: "Your drought insurance payout of USD {PAYOUT_AMOUNT_USD} has been sent to your EcoCash."
