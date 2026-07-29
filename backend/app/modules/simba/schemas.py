# Pydantic schemas for Simba — Energy & Infrastructure
from pydantic import BaseModel
from typing import List, Optional


class BatteryForecastPoint(BaseModel):
    hours_from_now: int
    estimated_battery_pct: float


class BatteryForecastOut(BaseModel):
    district: str
    battery_capacity_wh: float
    panel_watts: float
    data_source: str
    forecast: List[BatteryForecastPoint]
    disclaimer: str
