"""Celery worker: livestock disease risk indicator per district, from REAL stored satellite readings.

HONESTY NOTE: this is a transparent rainfall heuristic, not a validated epidemiological model. It used to read a
cache key nothing wrote any more, default to 50 mm and score EVERY district 100/100 — it would have texted farmers
fake "high disease risk" alarms. Now:
  * it only scores districts that have at least MIN_DAYS of real rainfall readings;
  * the score is stored for display only;
  * it creates a farmer-facing Alert only if RISK_MODEL_ALERTS_ENABLED=true (off until a vet signs off the method)."""
import logging
from datetime import date, datetime, timedelta, timezone

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis_client import set_cached
from app.models.alerts import Alert
from app.models.satellite import SatelliteReading
from app.utils.satellite import DISTRICTS

logger = logging.getLogger(__name__)
WINDOW_DAYS = 14
MIN_DAYS = 7


def score_from_rainfall(daily_mm: list[float]) -> float | None:
    """0-100. Wetter = higher (FMD/anthrax/tick-borne disease pressure rises with moisture). None if too little data."""
    if len(daily_mm) < MIN_DAYS:
        return None
    return round(min(100.0, (sum(daily_mm) / len(daily_mm)) * 2.5), 1)


@celery_app.task(name="app.workers.risk_model.calculate_district_risk_scores")
def calculate_district_risk_scores():
    db = SessionLocal()
    out: dict = {}
    try:
        since = date.today() - timedelta(days=WINDOW_DAYS)
        for district in DISTRICTS:
            rows = db.query(SatelliteReading.rainfall_mm).filter(
                SatelliteReading.district == district, SatelliteReading.reading_date >= since,
                SatelliteReading.rainfall_mm.isnot(None)).all()
            score = score_from_rainfall([float(r[0]) for r in rows])
            if score is None:
                out[district] = "insufficient data"
                continue
            set_cached(f"risk:{district}", {"score": score, "district": district, "days": len(rows)}, ttl_seconds=25 * 3600)
            out[district] = score
            if score >= settings.RISK_ALERT_THRESHOLD and settings.RISK_MODEL_ALERTS_ENABLED:
                _create_alert_once(db, district, score)
    finally:
        db.close()
    logger.info("Risk scores: %s", out)
    return out


def _create_alert_once(db, district: str, score: float) -> None:
    recent = db.query(Alert.id).filter(Alert.district == district, Alert.type == "livestock_risk",
                                       Alert.created_at >= datetime.now(timezone.utc) - timedelta(days=7)).first()
    if recent:
        return
    db.add(Alert(pillar="livestock", type="livestock_risk", severity="amber",
                 title=f"Wet conditions in {district}: watch your animals",
                 body=f"Recent rainfall in {district} is high, which raises livestock disease risk (indicator {score:.0f}/100). "
                      f"Check animals daily and contact Veterinary Services if any look sick.",
                 district=district, source="risk_model", extra_data={"heuristic": True, "score": score},
                 expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
    db.commit()
