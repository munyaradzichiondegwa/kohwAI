# Pydantic schemas for Mvura — Water Security
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.utils.validation import District


class BoreholeOut(BaseModel):
    id: str
    name: str
    village: str
    district: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    status: str                       # last status CONFIRMED by a validator/admin
    depth_m: Optional[float] = None
    last_verified: Optional[datetime] = None
    verified: bool = False            # has a validator/admin ever confirmed this borehole?
    pending_report: Optional[str] = None   # newest community report awaiting validation (unverified!)
    pending_reports: int = 0

    model_config = {"from_attributes": True}


class BoreholeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=300)
    village: str = Field(..., min_length=2, max_length=200)
    district: District
    # Zimbabwe bounding box (rough) — catches swapped/garbage coordinates
    lat: Optional[float] = Field(None, ge=-23.0, le=-15.0)
    lng: Optional[float] = Field(None, ge=25.0, le=34.0)
    depth_m: Optional[float] = Field(None, gt=0, le=1000)
    pump_type: Optional[str] = Field(None, max_length=100)


class BoreholeReportRequest(BaseModel):
    new_status: str = Field(..., pattern="^(working|low|dry|broken)$")
    note: Optional[str] = Field(None, max_length=1000)
