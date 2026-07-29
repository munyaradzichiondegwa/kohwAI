# FastAPI router for Simba — Energy & Infrastructure
from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_current_user
from app.models.user import User
from app.modules.simba import service
from app.modules.simba.schemas import BatteryForecastOut

router = APIRouter()


@router.get("/battery-forecast", response_model=BatteryForecastOut,
            summary="48-hour battery forecast from real NASA POWER solar irradiance")
def battery_forecast(
    district: str = Query(...),
    battery_capacity_wh: float = Query(..., gt=0, description="Total battery bank capacity in Wh"),
    panel_watts: float = Query(..., gt=0, description="Total solar panel rated wattage"),
    current_pct: float = Query(80, ge=0, le=100, description="Current battery charge %"),
    load_watts: float = Query(..., ge=0, description="Average continuous household/farm load in W"),
    user: User = Depends(get_current_user),
):
    # Sync def: FastAPI offloads to a thread pool automatically for the blocking NASA call.
    return service.get_battery_forecast(district, battery_capacity_wh, panel_watts, current_pct, load_watts)
