# Pydantic schemas for Musika — Resilient Marketplace
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.validation import District

MAX_LISTING_DAYS = 180
DEFAULT_LISTING_DAYS = 30


class ListingCreate(BaseModel):
    type: str = Field(..., pattern="^(seed|produce|livestock|input)$")
    title: str = Field(..., min_length=2, max_length=300)
    description: Optional[str] = Field(None, max_length=2000)
    quantity: float = Field(..., gt=0, le=10_000_000)
    unit: str = Field(..., min_length=1, max_length=30)
    price_usd: float = Field(..., ge=0, le=1_000_000)
    district: District
    expires_at: Optional[datetime] = None          # default: now + 30 days
    # Sellers must opt in to showing their phone number to other users (PRD: privacy by default).
    share_phone: bool = False

    @field_validator("expires_at")
    @classmethod
    def _future_and_bounded(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if v <= now:
            raise ValueError("expires_at must be in the future")
        if v > now + timedelta(days=MAX_LISTING_DAYS):
            raise ValueError(f"Listings can run for at most {MAX_LISTING_DAYS} days")
        return v


class ListingOut(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    quantity: float
    unit: str
    price_usd: float
    district: str
    seller_phone: Optional[str] = None    # only present when the seller opted in (share_phone)
    is_mine: bool = False
    is_active: bool
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
