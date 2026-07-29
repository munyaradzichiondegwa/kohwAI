# Pydantic schemas for Analytics
from pydantic import BaseModel
from typing import Dict


class OverviewOut(BaseModel):
    total_users: int
    new_users_last_7_days: int
    diagnoses_last_7_days: int
    active_alerts: int
    boreholes_by_status: Dict[str, int]
    active_market_listings: int
    pending_validation_queue: int
    generated_at: str
