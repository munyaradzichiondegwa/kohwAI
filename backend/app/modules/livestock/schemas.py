# Pydantic schemas for Livestock Health
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime, date

from app.utils.validation import District


class LivestockDiagnoseRequest(BaseModel):
    animal_type_code: str = Field(..., pattern="^[1-9]$", description="1=Cattle, 4=Poultry (see /livestock/reference/animal-types)")
    symptom_code: str = Field(..., pattern="^[1-5]$", description="1-5, see /livestock/reference/symptoms")
    animal_id: Optional[uuid.UUID] = None
    district: Optional[District] = None


class LivestockDiagnoseOut(BaseModel):
    id: str
    disease: str
    action: str
    notifiable: bool
    known: bool = True       # False = no rule matched; the action tells the farmer who to contact
    disclaimer: str = "This is a symptom guide, not an AI diagnosis. Confirm with Zimbabwe Veterinary Services."


class LivestockProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    animal_type: str = Field(..., pattern="^(cattle|goat|sheep|pig|poultry|donkey|other)$")
    breed: Optional[str] = Field(None, max_length=100)
    tag_number: Optional[str] = Field(None, max_length=100)
    birth_date: Optional[date] = None
    district: Optional[District] = None


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
