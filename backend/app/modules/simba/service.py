"""Business logic for Simba — Energy & Infrastructure.

Battery forecast uses real NASA POWER solar irradiance (ALLSKY_SFC_SW_DWN,
kWh/m^2/day) per the PRD's explicit requirement ("must use real NASA POWER
solar irradiance data — not generic estimates"). The charge/discharge model
itself is a simple, disclosed energy-balance estimate: it is not a
substitute for a proper solar system sizing tool, and says so.
"""
from datetime import datetime, timedelta, timezone

from app.utils.satellite import fetch_nasa_power, require_district, clean_series

HOURS_STEP = 6
HOURS_HORIZON = 48
DAYLIGHT_START_H, DAYLIGHT_END_H = 6.0, 18.0     # simplified 12-hour solar day (local time)
DAYLIGHT_HOURS = DAYLIGHT_END_H - DAYLIGHT_START_H
SYSTEM_LOSS_FACTOR = 0.75
FALLBACK_IRRADIANCE_KWH_M2 = 5.5
ZIMBABWE_UTC_OFFSET = timedelta(hours=2)          # CAT, no daylight saving


def daylight_overlap_hours(t0: float, t1: float) -> float:
    """Hours of [t0, t1) (hours since local midnight today; may exceed 24) that fall inside daylight."""
    total, day = 0.0, 0
    while day * 24 < t1:
        lo, hi = day * 24 + DAYLIGHT_START_H, day * 24 + DAYLIGHT_END_H
        total += max(0.0, min(t1, hi) - max(t0, lo))
        day += 1
    return total


def simulate_battery(battery_capacity_wh: float, panel_watts: float, current_pct: float, load_watts: float,
                     irradiance_kwh_m2: float, start_hour_local: float) -> list[dict]:
    """Energy balance per 6h interval. Daily generation is spread evenly over the 12 daylight hours,
    so a full day always yields exactly `panel_watts * irradiance * loss` Wh (not more)."""
    daily_gen_wh = panel_watts * irradiance_kwh_m2 * SYSTEM_LOSS_FACTOR
    battery_wh = (current_pct / 100.0) * battery_capacity_wh
    out = [{"hours_from_now": 0,
            "estimated_battery_pct": round(100 * battery_wh / battery_capacity_wh, 1) if battery_capacity_wh else 0}]
    for step in range(HOURS_STEP, HOURS_HORIZON + 1, HOURS_STEP):
        t0, t1 = start_hour_local + step - HOURS_STEP, start_hour_local + step
        gen_wh = daily_gen_wh * daylight_overlap_hours(t0, t1) / DAYLIGHT_HOURS
        use_wh = load_watts * HOURS_STEP
        battery_wh = max(0.0, min(battery_capacity_wh, battery_wh + gen_wh - use_wh))
        out.append({"hours_from_now": step,
                    "estimated_battery_pct": round(100 * battery_wh / battery_capacity_wh, 1) if battery_capacity_wh else 0})
    return out


def get_battery_forecast(district: str, battery_capacity_wh: float, panel_watts: float,
                         current_pct: float, load_watts: float, now: datetime | None = None) -> dict:
    require_district(district)            # unknown district -> ValueError (router: 422), never "Harare"

    weather = fetch_nasa_power(district, days_back=3)
    avg_irradiance_kwh_m2 = None
    if weather:
        vals = [v for v in clean_series(weather.get("ALLSKY_SFC_SW_DWN")).values() if v >= 0]
        if vals:
            avg_irradiance_kwh_m2 = sum(vals) / len(vals)
    irradiance = avg_irradiance_kwh_m2 if avg_irradiance_kwh_m2 is not None else FALLBACK_IRRADIANCE_KWH_M2

    local = (now or datetime.now(timezone.utc)).astimezone(timezone(ZIMBABWE_UTC_OFFSET))
    start_hour = local.hour + local.minute / 60.0
    forecast = simulate_battery(battery_capacity_wh, panel_watts, current_pct, load_watts, irradiance, start_hour)

    return {
        "district": district,
        "battery_capacity_wh": battery_capacity_wh,
        "panel_watts": panel_watts,
        "data_source": ("NASA POWER live irradiance (ALLSKY_SFC_SW_DWN)" if avg_irradiance_kwh_m2
                        else "NASA POWER unreachable — using a typical-irradiance fallback (5.5 kWh/m²/day)"),
        "forecast": forecast,
        "disclaimer": (
            "This is a simplified energy-balance estimate, not a professional solar "
            "system sizing calculation. Actual output depends on panel angle, shading, "
            "battery health, and inverter losses."
        ),
    }
