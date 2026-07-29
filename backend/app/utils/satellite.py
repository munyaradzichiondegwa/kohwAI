import requests, logging
from datetime import date, timedelta
from app.core.config import settings
from app.core.redis_client import set_cached

logger = logging.getLogger(__name__)

DISTRICTS: dict[str, tuple[float, float]] = {
    "Chipinge": (-20.19, 32.62), "Gokwe":    (-18.22, 28.94),
    "Matopos":  (-20.47, 28.50), "Binga":    (-17.62, 27.34),
    "Nyanga":   (-18.22, 32.75), "Harare":   (-17.83, 31.05),
    "Bulawayo": (-20.15, 28.58), "Mutare":   (-18.97, 32.67),
    "Gweru":    (-19.45, 29.82), "Masvingo": (-20.07, 30.83),
}
NASA_PARAMS = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M"

def fetch_nasa_power(district: str, days_back: int = 1) -> dict | None:
    lat, lon = DISTRICTS.get(district, (-17.83, 31.05))
    end   = date.today()
    start = end - timedelta(days=days_back)
    fmt   = lambda d: d.strftime("%Y%m%d")
    url = (f"{settings.NASA_POWER_BASE_URL}?parameters={NASA_PARAMS}&community=AG"
           f"&longitude={lon}&latitude={lat}&start={fmt(start)}&end={fmt(end)}&format=JSON")
    try:
        r = requests.get(url, timeout=30); r.raise_for_status()
        data = r.json().get("properties", {}).get("parameter", {})
        set_cached(f"weather:{district}", data, ttl_seconds=6 * 3600)
        logger.info(f"NASA POWER fetched for {district}")
        return data
    except Exception as e:
        logger.error(f"NASA POWER failed for {district}: {e}")
        return None

def compute_risk_score(district: str, weather: dict) -> float:
    rainfall = weather.get("PRECTOTCORR", {})
    temp     = weather.get("T2M", {})
    avg_rain = sum(rainfall.values()) / len(rainfall) if rainfall else 0
    avg_temp = sum(temp.values())     / len(temp)     if temp     else 25
    return round(min(100.0, min(50.0, avg_rain * 5) + min(30.0, max(0, avg_temp - 20) * 2)), 1)
