import requests, logging
from datetime import date, timedelta
from app.core.config import settings
from app.core.redis_client import get_cached, set_cached

logger = logging.getLogger(__name__)

DISTRICTS: dict[str, tuple[float, float]] = {
    "Chipinge": (-20.19, 32.62), "Gokwe":    (-18.22, 28.94),
    "Matopos":  (-20.47, 28.50), "Binga":    (-17.62, 27.34),
    "Nyanga":   (-18.22, 32.75), "Harare":   (-17.83, 31.05),
    "Bulawayo": (-20.15, 28.58), "Mutare":   (-18.97, 32.67),
    "Gweru":    (-19.45, 29.82), "Masvingo": (-20.07, 30.83),
}
NASA_PARAMS = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M"

# NASA POWER marks "no data" with -999 (and recent days are often not published yet).
# That value must never be averaged or summed as if it were a measurement.
NASA_FILL_THRESHOLD = -900.0
CACHE_TTL_SECONDS = 3 * 3600


def clean_series(series: dict | None) -> dict[str, float]:
    """Drop missing/fill values from one NASA parameter series ({YYYYMMDD: value})."""
    out: dict[str, float] = {}
    for k, v in (series or {}).items():
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f > NASA_FILL_THRESHOLD:
            out[k] = f
    return out


def require_district(district: str) -> tuple[float, float]:
    """Unknown districts are an error — never silently answered with another district's data."""
    if district not in DISTRICTS:
        raise ValueError(f"Unknown district '{district}'")
    return DISTRICTS[district]


def fetch_nasa_power(district: str, days_back: int = 1, use_cache: bool = True) -> dict | None:
    """Daily NASA POWER data for the last `days_back` days with fill values removed.
    Served from Redis when fresh (3h) so user requests don't each hit NASA."""
    lat, lon = require_district(district)
    key = f"weather:{district}:{days_back}"
    if use_cache:
        cached = get_cached(key)
        if cached:
            return cached
    end   = date.today()
    start = end - timedelta(days=days_back)
    fmt   = lambda d: d.strftime("%Y%m%d")
    url = (f"{settings.NASA_POWER_BASE_URL}?parameters={NASA_PARAMS}&community=AG"
           f"&longitude={lon}&latitude={lat}&start={fmt(start)}&end={fmt(end)}&format=JSON")
    try:
        r = requests.get(url, timeout=30); r.raise_for_status()
        raw = r.json().get("properties", {}).get("parameter", {})
        data = {param: clean_series(series) for param, series in raw.items()}
        set_cached(key, data, ttl_seconds=CACHE_TTL_SECONDS)
        logger.info(f"NASA POWER fetched for {district} ({days_back}d)")
        return data
    except Exception as e:
        logger.error(f"NASA POWER failed for {district}: {e}")
        return None


def compute_risk_score(district: str, weather: dict) -> float:
    rainfall = clean_series(weather.get("PRECTOTCORR"))
    temp     = clean_series(weather.get("T2M"))
    avg_rain = sum(rainfall.values()) / len(rainfall) if rainfall else 0
    avg_temp = sum(temp.values())     / len(temp)     if temp     else 25
    return round(min(100.0, min(50.0, avg_rain * 5) + min(30.0, max(0, avg_temp - 20) * 2)), 1)
