# Pydantic schemas for parametric insurance (part of Musika)
from pydantic import BaseModel, Field, AfterValidator
from typing import Annotated, Optional
from datetime import datetime

from app.utils.validation import District, Season, check_ecocash

EcoCash = Annotated[Optional[str], AfterValidator(check_ecocash)]


class EnrollmentRequest(BaseModel):
    district: District
    season: Season  # e.g. "2026-27"
    ecocash_number: EcoCash = None


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
    ecocash_ref: str = Field(..., min_length=4, max_length=200)


class EvaluatePayoutRequest(BaseModel):
    district: District
    season: Season
    drought_index_threshold: Optional[int] = Field(None, ge=1, le=100)  # default: settings.INSURANCE_DROUGHT_THRESHOLD
