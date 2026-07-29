from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin

class DiagnosisReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "diagnosis_reports"
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    subject_type  = Column(String(20), nullable=False)
    crop_type     = Column(String(100), nullable=True)
    animal_type   = Column(String(100), nullable=True)
    district      = Column(String(100), nullable=True)
    top_disease   = Column(String(200), nullable=True)
    confidence    = Column(Float, nullable=True)
    top3_json     = Column(JSONB, nullable=True)
    audio_used    = Column(Boolean, default=False)
    expert_review = Column(Boolean, default=False)
    expert_note   = Column(Text, nullable=True)
    image_s3_key  = Column(String(512), nullable=True)
    synced        = Column(Boolean, default=True)
    user = relationship("User", back_populates="diagnoses")

class PestSighting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pest_sightings"
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    species       = Column(String(200), nullable=False)
    severity      = Column(String(20),  nullable=False)
    district      = Column(String(100), nullable=False)
    lat           = Column(Float, nullable=True)
    lng           = Column(Float, nullable=True)
    affected_ha   = Column(Float, nullable=True)
    description   = Column(Text,  nullable=True)
    photo_s3_key  = Column(String(512), nullable=True)
    status        = Column(String(20), default="pending")
    validated_by  = Column(UUID(as_uuid=True), nullable=True)
    validated_at  = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

class AdvisoryCard(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "advisory_cards"
    title    = Column(String(300), nullable=False)
    category = Column(String(100), nullable=False)
    language = Column(String(5),   nullable=False, default="en")
    content  = Column(Text, nullable=False)
    version  = Column(Integer, nullable=False, default=1)
    is_active= Column(Boolean, default=True)
    authored_by = Column(String(200), nullable=True)
