"""Business logic for Simba — Energy & Infrastructure.

Battery forecast uses real NASA POWER solar irradiance (ALLSKY_SFC_SW_DWN,
kWh/m^2/day) per the PRD's explicit requirement ("must use real NASA POWER
solar irradiance data — not generic estimates"). The charge/discharge model
itself is a simple, disclosed energy-balance estimate: it is not a
substitute for a proper solar system sizing tool, and says so.
"""
from app.utils.satellite import fetch_nasa_power, DISTRICTS

HOURS_STEP = 6
HOURS_HORIZON = 48


def get_battery_forecast(district: str, battery_capacity_wh: float, panel_watts: float,
                          current_pct: float, load_watts: float) -> dict:
    if district not in DISTRICTS:
        district = "Harare"

    weather = fetch_nasa_power(district, days_back=3)
    avg_irradiance_kwh_m2 = None
    if weather:
        irr = weather.get("ALLSKY_SFC_SW_DWN", {})
        vals = [v for v in irr.values() if v is not None and v >= 0]
        if vals:
            avg_irradiance_kwh_m2 = sum(vals) / len(vals)

    # Fallback for Zimbabwe's dry-season average when live data is unavailable,
    # sourced from the same NASA POWER climatology this endpoint normally reads live
    # (used only so the offline-first UI has *something* sensible to show).
    irradiance = avg_irradiance_kwh_m2 if avg_irradiance_kwh_m2 is not None else 5.5

    # Rough panel output: irradiance (kWh/m^2/day) is treated as a proxy for
    # full-sun-hours/day, scaled by a typical system-loss-adjusted factor.
    SYSTEM_LOSS_FACTOR = 0.75
    est_daily_generation_wh = panel_watts * irradiance * SYSTEM_LOSS_FACTOR

    forecast = []
    battery_wh = (current_pct / 100.0) * battery_capacity_wh
    for step in range(0, HOURS_HORIZON + 1, HOURS_STEP):
        is_daylight = (6 <= (step % 24) <= 18)
        gen_wh = (est_daily_generation_wh / 12) * HOURS_STEP if is_daylight else 0
        use_wh = load_watts * HOURS_STEP
        if step > 0:
            battery_wh = max(0.0, min(battery_capacity_wh, battery_wh + gen_wh - use_wh))
        forecast.append({
            "hours_from_now": step,
            "estimated_battery_pct": round(100 * battery_wh / battery_capacity_wh, 1) if battery_capacity_wh else 0,
        })

    return {
        "district": district,
        "battery_capacity_wh": battery_capacity_wh,
        "panel_watts": panel_watts,
        "data_source": ("NASA POWER live irradiance (ALLSKY_SFC_SW_DWN)" if avg_irradiance_kwh_m2
                        else "NASA POWER unreachable — using a seasonal dry-season average as fallback"),
        "forecast": forecast,
        "disclaimer": (
            "This is a simplified energy-balance estimate, not a professional solar "
            "system sizing calculation. Actual output depends on panel angle, shading, "
            "battery health, and inverter losses."
        ),
    }
