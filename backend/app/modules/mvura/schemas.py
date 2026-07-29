# Pydantic schemas for Mvura — Water Security
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BoreholeOut(BaseModel):
    id: str
    name: str
    village: str
    district: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    status: str
    depth_m: Optional[float] = None
    last_verified: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BoreholeCreate(BaseModel):
    name: str
    village: str
    district: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    depth_m: Optional[float] = None
    pump_type: Optional[str] = None


class BoreholeReportRequest(BaseModel):
    new_status: str = Field(..., pattern="^(working|low|dry|broken)$")
    note: Optional[str] = None
