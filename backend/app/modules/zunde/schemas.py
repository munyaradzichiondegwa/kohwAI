# Pydantic schemas for Zunde — Agriculture & Early Warning
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CropDiagnoseRequest(BaseModel):
    crop_type_code: str = Field(..., description="1=Maize, 2=Sorghum/Small grains")
    symptom_code: str = Field(..., description="1-5, see /zunde/reference/crop-symptoms")
    district: Optional[str] = None
    image_s3_key: Optional[str] = None


class DiagnosisOut(BaseModel):
    id: str
    top_disease: str
    second_disease: Optional[str] = None
    action: str
    disclaimer: str = "This is a symptom guide, not an AI diagnosis. Confirm with your local Agritex officer."


class PestSightingRequest(BaseModel):
    species: str
    severity: str = Field(..., pattern="^(low|medium|high)$")
    district: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    affected_ha: Optional[float] = None
    description: Optional[str] = None
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
    disclaimer: str
