from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin

class LivestockProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "livestock_profiles"
    owner_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name           = Column(String(200), nullable=False)
    animal_type    = Column(String(50),  nullable=False)
    breed          = Column(String(100), nullable=True)
    tag_number     = Column(String(100), nullable=True)
    birth_date     = Column(Date, nullable=True)
    health_status  = Column(String(30), default="healthy")
    last_diagnosed = Column(DateTime(timezone=True), nullable=True)
    last_vaccinated= Column(DateTime(timezone=True), nullable=True)
    district       = Column(String(100), nullable=True)
    is_active      = Column(Boolean, default=True)
    owner      = relationship("User", back_populates="livestock")
    treatments = relationship("TreatmentRecord", back_populates="animal")

class TreatmentRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "treatment_records"
    animal_id     = Column(UUID(as_uuid=True), ForeignKey("livestock_profiles.id"), nullable=False)
    diagnosis     = Column(String(300), nullable=False)
    treatment     = Column(Text, nullable=False)
    treated_by    = Column(String(200), default="Farmer")
    ai_confidence = Column(Float, nullable=True)
    ai_top3_json  = Column(JSONB,  nullable=True)
    outcome       = Column(String(50), nullable=True)
    date_treated  = Column(DateTime(timezone=True), nullable=False)
    animal = relationship("LivestockProfile", back_populates="treatments")

class VaccinationReminder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vaccination_reminders"
    animal_id        = Column(UUID(as_uuid=True), ForeignKey("livestock_profiles.id"), nullable=False)
    disease          = Column(String(200), nullable=False)
    vaccine          = Column(String(200), nullable=False)
    due_date         = Column(Date, nullable=False)
    reminder_sent    = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
