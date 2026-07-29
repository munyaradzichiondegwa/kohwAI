# Pydantic schemas for Livestock Health
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class LivestockDiagnoseRequest(BaseModel):
    animal_type_code: str = Field(..., description="1=Cattle, 4=Poultry")
    symptom_code: str = Field(..., description="1-5, see /livestock/reference/symptoms")
    animal_id: Optional[str] = None
    district: Optional[str] = None


class LivestockDiagnoseOut(BaseModel):
    id: str
    disease: str
    action: str
    notifiable: bool
    disclaimer: str = "This is a symptom guide, not an AI diagnosis. Confirm with Zimbabwe Veterinary Services."


class LivestockProfileCreate(BaseModel):
    name: str
    animal_type: str
    breed: Optional[str] = None
    tag_number: Optional[str] = None
    birth_date: Optional[date] = None
    district: Optional[str] = None


class LivestockProfileOut(BaseModel):
    id: str
    name: str
    animal_type: str
    breed: Optional[str] = None
    tag_number: Optional[str] = None
    health_status: str
    last_diagnosed: Optional[datetime] = None
    district: Optional[str] = None

    model_config = {"from_attributes": True}
