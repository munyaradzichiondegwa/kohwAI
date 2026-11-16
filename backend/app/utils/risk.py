"""Shared, disclosed risk heuristics built on real NASA POWER data.

Important honesty note: these are simplified, transparent indicators, not
calibrated meteorological indices. A proper drought index (e.g. SPI — Standardized
Precipitation Index) needs decades of historical rainfall per location. We don't have
that baseline, so we use a plain, disclosed metric: cumulative rainfall over a trailing
30-day window compared with a fixed reference amount. Treat it as a rough triage flag.

SEASONALITY: the reference (60 mm / 30 days) only makes sense in the rainy season
(Nov-Mar). In the dry season rainfall is ~0 mm everywhere, so the index is ~100 by
construction. Anything that ACTS on the index (insurance, alerts) must check the season
first — see `in_rain_season`.
"""
from datetime import date, timedelta

from app.utils.satellite import fetch_nasa_power, require_district, clean_series

REFERENCE_30DAY_MM = 60.0
WINDOW_DAYS = 30
MIN_VALID_DAYS = 20          # need at least 2/3 of the window to trust the total


def in_rain_season(d: date, start_month: int = 11, end_month: int = 3) -> bool:
    return d.month >= start_month or d.month <= end_month


def index_from_rainfall(daily_mm: list[float]) -> dict | None:
    """0-100 deficit index from up to 30 daily values (missing days already removed).
    Returns None when too few valid days. The total is scaled to a full 30 days so a
    window with a few missing days is not mistaken for extra dryness."""
    n = len(daily_mm)
    if n < MIN_VALID_DAYS:
        return None
    total = sum(daily_mm) * (WINDOW_DAYS / n)
    deficit_ratio = max(0.0, 1 - (total / REFERENCE_30DAY_MM))
    return {"total_mm": round(total, 1), "valid_days": n, "drought_index": round(min(100, deficit_ratio * 100))}


def index_for_date(rain_by_date: dict[date, float], end: date) -> dict | None:
    """Trailing 30-day index ending on `end`, from a {date: mm} map of VALID days only."""
    window = [rain_by_date[end - timedelta(days=i)] for i in range(WINDOW_DAYS)
              if (end - timedelta(days=i)) in rain_by_date]
    return index_from_rainfall(window)


def compute_drought_index(district: str) -> dict:
    """Returns a 0-100 'drought_index' (higher = drier/more severe) plus the raw rainfall
    total it was derived from, so the number is always auditable."""
    require_district(district)          # ValueError for unknown districts (no silent Harare)
    weather = fetch_nasa_power(district, days_back=WINDOW_DAYS)
    series = clean_series((weather or {}).get("PRECTOTCORR"))
    # newest 30 valid days of the last 31 requested
    values = [series[k] for k in sorted(series)[-WINDOW_DAYS:]]
    res = index_from_rainfall([v for v in values if v >= 0])
    today = date.today()

    if res is None:
        return {"district": district, "total_rainfall_30day_mm": None, "drought_index": None,
                "in_rain_season": in_rain_season(today),
                "note": "Satellite rainfall data unavailable or incomplete right now — index could not be computed."}
    return {
        "district": district,
        "total_rainfall_30day_mm": res["total_mm"],
        "valid_days": res["valid_days"],
        "reference_30day_mm": REFERENCE_30DAY_MM,
        "drought_index": res["drought_index"],
        "in_rain_season": in_rain_season(today),
        "note": ("Simplified indicator (0=wet, 100=severe deficit) based on 30-day rainfall vs. a "
                 "conservative reference total — not a calibrated drought index (e.g. SPI). "
                 + ("" if in_rain_season(today) else
                    "Outside the Nov–Mar rainy season a high value is normal and does not indicate drought.")),
    }
