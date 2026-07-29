# Pydantic schemas for Cross-Pillar Intelligence Engine
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InsightOut(BaseModel):
    id: str
    district: str
    source_pillar: str
    target_pillar: str
    insight_type: str
    severity: str
    message: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DistrictEvaluateRequest(BaseModel):
    district: str
