"""Celery worker: daily geospatial livestock disease risk scoring per district."""
from app.core.celery_app import celery_app
from app.core.redis_client import get_cached, set_cached, publish_alert
from app.core.config import settings
import logging, json

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.risk_model.calculate_district_risk_scores")
def calculate_district_risk_scores():
    """
    Score each district 0-100 for livestock disease risk.
    Inputs: satellite weather, historical outbreak records, livestock density.
    Output: per-district risk score stored in Redis + alert if > threshold.
    """
    districts = ["Chipinge", "Gokwe", "Matopos", "Binga", "Nyanga"]
    for district in districts:
        weather = get_cached(f"weather:{district}") or {}
        # TODO: Load historical outbreak data from PostgreSQL
        # TODO: Run trained scikit-learn + TensorFlow risk model
        score = _calculate_risk_score(district, weather)
        set_cached(f"risk:{district}", {"score": score, "district": district}, ttl_seconds=25 * 3600)
        if score >= settings.RISK_ALERT_THRESHOLD:
            _trigger_risk_alert(district, score)
        logger.info(f"Risk score for {district}: {score}")


def _calculate_risk_score(district: str, weather: dict) -> float:
    """
    Placeholder risk model. Replace with trained scikit-learn pipeline.
    Real model inputs: rainfall anomaly, temperature, NDVI, historical outbreaks,
    livestock density, proximity to known outbreak zones.
    """
    rainfall = weather.get("PRECTOTCORR", {})
    avg_rain = sum(rainfall.values()) / len(rainfall) if rainfall else 50
    # Higher rainfall → higher FMD / anthrax risk
    base_score = min(100.0, avg_rain * 2.5)
    return round(base_score, 1)


def _trigger_risk_alert(district: str, score: float):
    """Publish a risk alert to Redis Pub/Sub and SMS queue."""
    # Deduplication: don't re-alert same district within 7 days
    dup_key = f"risk_alert_sent:{district}"
    if get_cached(dup_key):
        return
    set_cached(dup_key, True, ttl_seconds=7 * 24 * 3600)
    # TODO: Queue SMS via Africa's Talking to farmers in district
    publish_alert(f"alerts:{district}", {
        "type": "livestock_risk", "district": district, "score": score,
        "message": f"High risk of livestock disease in {district} (score: {score}/100). Check your animals."
    })
    logger.warning(f"Risk alert triggered for {district} (score {score})")
