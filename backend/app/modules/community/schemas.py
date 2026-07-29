# Pydantic schemas for Community & Validation
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class QueueItemOut(BaseModel):
    kind: Literal["pest_sighting", "borehole_report", "community_report"]
    id: str
    district: str
    summary: str
    reporter_phone: Optional[str] = None
    created_at: Optional[datetime] = None


class RejectRequest(BaseModel):
    reason: str


class CommunityReportCreate(BaseModel):
    report_type: str
    district: str
    description: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
