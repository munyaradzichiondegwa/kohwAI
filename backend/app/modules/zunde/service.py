"""Business logic for Zunde — Agriculture & Early Warning."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.zunde import DiagnosisReport, PestSighting, AdvisoryCard
from app.modules.ussd.rules_engine import RulesEngine
from app.utils.satellite import fetch_nasa_power, DISTRICTS
from app.utils.risk import compute_drought_index

logger = logging.getLogger(__name__)
rules = RulesEngine()

# Rainfall-onset heuristic threshold. This is a simplified, transparent proxy
# (cumulative rainfall over the trailing 5 days), NOT an official Agritex
# planting-date table — Zimbabwe's actual recommended planting windows vary
# by natural region, soil, and cultivar and should be confirmed with a local
# Agritex extension officer. See docs/DATA_SOURCES.md for the reasoning.
ONSET_5DAY_THRESHOLD_MM = 25.0


def diagnose_crop(db: Session, user_id: Optional[str], crop_type_code: str, symptom_code: str,
                   district: Optional[str], image_s3_key: Optional[str]) -> DiagnosisReport:
    result = rules.diagnose_crop(symptom_code, crop_type_code)
    report = DiagnosisReport(
        user_id=user_id,
        subject_type="crop",
        crop_type=crop_type_code,
        district=district,
        top_disease=result["disease1"],
        top3_json={"disease1": result["disease1"], "disease2": result["disease2"], "action": result["action"]},
        image_s3_key=image_s3_key,
        synced=True,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def report_pest_sighting(db: Session, user_id: Optional[str], payload: dict) -> PestSighting:
    sighting = PestSighting(user_id=user_id, status="pending", **payload)
    db.add(sighting)
    db.commit()
    db.refresh(sighting)
    return sighting


def list_advisory_cards(db: Session, language: str = "en", category: Optional[str] = None):
    q = db.query(AdvisoryCard).filter(AdvisoryCard.is_active.is_(True), AdvisoryCard.language == language)
    if category:
        q = q.filter(AdvisoryCard.category == category)
    return q.order_by(AdvisoryCard.title).all()


def get_planting_calendar(district: str) -> dict:
    """Fetch real NASA POWER rainfall data for the district and apply a
    disclosed, simplified onset-of-rains heuristic. Returns raw data either way
    so the farmer (or a future smarter model) isn't limited to our heuristic."""
    if district not in DISTRICTS:
        district = "Harare"

    weather = fetch_nasa_power(district, days_back=9)
    recent = []
    cumulative_5day = None
    onset = False

    if weather:
        rainfall = weather.get("PRECTOTCORR", {})
        temp = weather.get("T2M", {})
        dates_sorted = sorted(rainfall.keys())
        for d in dates_sorted:
            val = rainfall.get(d)
            recent.append({
                "date": d,
                "rainfall_mm": val if val is not None and val >= 0 else None,
                "temp_c": temp.get(d),
            })
        last5 = [r["rainfall_mm"] for r in recent[-5:] if r["rainfall_mm"] is not None]
        if last5:
            cumulative_5day = round(sum(last5), 1)
            onset = cumulative_5day >= ONSET_5DAY_THRESHOLD_MM

    guidance = (
        f"Rainfall over the last 5 days in {district} totals about {cumulative_5day}mm — "
        "conditions look consistent with the rains starting. Many farmers in favourable "
        "natural regions (I–II) begin land preparation now; check with Agritex before planting."
        if onset else
        f"Rainfall over the last 5 days in {district} has been light" +
        (f" ({cumulative_5day}mm)" if cumulative_5day is not None else " (no recent satellite data available)") +
        ". Holding off on planting reduces the risk of a false start and having to replant."
    )
    if not weather:
        guidance = ("Live satellite rainfall data could not be retrieved right now "
                    "(NASA POWER may be unreachable or rate-limited). Check again shortly, "
                    "or contact your local Agritex officer for the current guidance.")

    return {
        "district": district,
        "data_source": "NASA POWER (power.larc.nasa.gov), community=AG, parameter=PRECTOTCORR/T2M",
        "recent_rainfall": recent,
        "cumulative_5day_mm": cumulative_5day,
        "rains_likely_onset": onset,
        "guidance": guidance,
        "disclaimer": (
            "This is an automated estimate from satellite rainfall data using a simple "
            "5-day cumulative-rainfall threshold, not an official Agritex planting-date "
            "table. Confirm planting decisions with your local Agritex extension officer."
        ),
    }
