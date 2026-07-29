# Pydantic schemas for Musika — Resilient Marketplace
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ListingCreate(BaseModel):
    type: str = Field(..., pattern="^(seed|produce|livestock|input)$")
    title: str
    description: Optional[str] = None
    quantity: float
    unit: str
    price_usd: float
    district: str
    expires_at: Optional[datetime] = None


class ListingOut(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    quantity: float
    unit: str
    price_usd: float
    district: str
    seller_phone: Optional[str] = None
    is_active: bool
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
