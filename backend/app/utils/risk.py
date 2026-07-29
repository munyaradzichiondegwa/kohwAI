"""Shared, disclosed risk heuristics built on real NASA POWER data.

Important honesty note: these are simplified, transparent indicators, not
calibrated meteorological indices. A proper drought index (e.g. SPI —
Standardized Precipitation Index) requires decades of historical rainfall
distribution data per location to compute a percentile-based anomaly score.
We don't have that historical baseline in this system, so instead we use a
plain, disclosed metric: cumulative rainfall over a trailing window compared
to a fixed, generously-conservative reference amount for the region's
dry-season norm. This is intentionally simple so nobody mistakes it for more
authoritative than it is — treat it as a rough triage flag, not a scientific
drought classification.
"""
from app.utils.satellite import fetch_nasa_power, DISTRICTS

# A rough, disclosed reference for "typical" 30-day rainfall during
# Zimbabwe's main growing season — deliberately conservative so we
# under-trigger rather than cry wolf. Not a per-district calibrated normal.
REFERENCE_30DAY_MM = 60.0


def compute_drought_index(district: str) -> dict:
    """Returns a 0-100 'drought_index' (higher = drier/more severe) plus the
    raw rainfall total it was derived from, so the number is always auditable
    against the real satellite reading it came from."""
    if district not in DISTRICTS:
        district = "Harare"

    weather = fetch_nasa_power(district, days_back=30)
    total_mm = None
    if weather:
        rainfall = weather.get("PRECTOTCORR", {})
        vals = [v for v in rainfall.values() if v is not None and v >= 0]
        if vals:
            total_mm = round(sum(vals), 1)

    if total_mm is None:
        return {
            "district": district, "total_rainfall_30day_mm": None,
            "drought_index": None,
            "note": "Satellite rainfall data unavailable right now — index could not be computed.",
        }

    deficit_ratio = max(0.0, 1 - (total_mm / REFERENCE_30DAY_MM))
    drought_index = round(min(100, deficit_ratio * 100))

    return {
        "district": district,
        "total_rainfall_30day_mm": total_mm,
        "reference_30day_mm": REFERENCE_30DAY_MM,
        "drought_index": drought_index,
        "note": (
            "Simplified indicator (0=wet, 100=severe deficit) based on 30-day "
            "rainfall vs. a conservative reference total — not a calibrated "
            "meteorological drought index (e.g. SPI), which needs long-term "
            "historical baselines this system doesn't have."
        ),
    }
