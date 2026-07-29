# Pydantic schemas for parametric insurance (part of Musika)
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EnrollmentRequest(BaseModel):
    district: str
    season: str  # e.g. "2026-27"
    ecocash_number: Optional[str] = None


class EnrollmentOut(BaseModel):
    id: str
    district: str
    season: str
    payout_amount_usd: float
    is_active: bool
    ecocash_number: Optional[str] = None

    model_config = {"from_attributes": True}


class PayoutOut(BaseModel):
    id: str
    district: str
    drought_index: int
    amount_usd: float
    status: str
    ecocash_ref: Optional[str] = None
    sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MarkSentRequest(BaseModel):
    ecocash_ref: str


class EvaluatePayoutRequest(BaseModel):
    district: str
    season: str
    drought_index_threshold: int = 60
