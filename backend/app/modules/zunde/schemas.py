# Pydantic schemas for Zunde — Agriculture & Early Warning
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.utils.validation import District
from app.modules.zunde.pests import PestSpecies


class CropDiagnoseRequest(BaseModel):
    crop_type_code: str = Field(..., pattern="^[1-9]$", description="1=Maize, 2=Sorghum/Small grains")
    symptom_code: str = Field(..., pattern="^[1-5]$", description="1-5, see /zunde/reference/crop-symptoms")
    district: Optional[District] = None
    image_s3_key: Optional[str] = None


class DiagnosisOut(BaseModel):
    id: str
    top_disease: str
    second_disease: Optional[str] = None
    action: str
    known: bool = True
    disclaimer: str = "This is a symptom guide, not an AI diagnosis. Confirm with your local Agritex officer."


class PestSightingRequest(BaseModel):
    species: PestSpecies            # controlled vocabulary: see GET /zunde/reference/pest-species
    severity: str = Field(..., pattern="^(low|medium|high)$")
    district: District
    lat: Optional[float] = Field(None, ge=-23.0, le=-15.0)
    lng: Optional[float] = Field(None, ge=25.0, le=34.0)
    affected_ha: Optional[float] = Field(None, ge=0, le=100000)
    description: Optional[str] = Field(None, max_length=2000)
    photo_s3_key: Optional[str] = None


class AdvisoryCardOut(BaseModel):
    id: str
    title: str
    category: str
    language: str
    content: str
    version: int

    model_config = {"from_attributes": True}


class RainfallDay(BaseModel):
    date: str
    rainfall_mm: Optional[float] = None
    temp_c: Optional[float] = None


class PlantingCalendarOut(BaseModel):
    district: str
    data_source: str
    recent_rainfall: List[RainfallDay]
    cumulative_5day_mm: Optional[float] = None
    rains_likely_onset: bool
    guidance: str
    latest_data_date: Optional[str] = None   # newest day with a real satellite value
    data_is_stale: bool = False              # newest value is more than 5 days old
    disclaimer: str
