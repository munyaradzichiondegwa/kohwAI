# Pydantic schemas for Community & Validation
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

from app.utils.validation import District


class QueueItemOut(BaseModel):
    kind: Literal["pest_sighting", "borehole_report", "community_report"]
    id: str
    district: str
    summary: str
    reporter_phone: Optional[str] = None   # masked, e.g. +2637***01
    created_at: Optional[datetime] = None


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


class CommunityReportCreate(BaseModel):
    report_type: str = Field(..., min_length=2, max_length=50)
    district: District
    description: Optional[str] = Field(None, max_length=2000)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)


class AppointValidator(BaseModel):
    phone: str = Field(..., pattern=r"^(\+2637\d{8}|07\d{8})$")
    districts: list[District] = Field(..., min_length=1)
