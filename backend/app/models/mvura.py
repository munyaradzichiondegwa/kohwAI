from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin

class Borehole(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "boreholes"
    name          = Column(String(300), nullable=False)
    village       = Column(String(200), nullable=False)
    district      = Column(String(100), nullable=False, index=True)
    lat           = Column(Float, nullable=True)
    lng           = Column(Float, nullable=True)
    status        = Column(String(20), default="working")
    depth_m       = Column(Float, nullable=True)
    pump_type     = Column(String(100), nullable=True)
    last_verified = Column(DateTime(timezone=True), nullable=True)
    verified_by   = Column(UUID(as_uuid=True), nullable=True)
    photo_s3_key  = Column(String(512), nullable=True)
    reports = relationship("BoreholeReport", back_populates="borehole")

class BoreholeReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "borehole_reports"
    borehole_id  = Column(UUID(as_uuid=True), ForeignKey("boreholes.id"), nullable=True)
    reported_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"),    nullable=True)
    new_status   = Column(String(20), nullable=False)
    note         = Column(Text, nullable=True)
    validated    = Column(Boolean, default=False)
    validated_by = Column(UUID(as_uuid=True), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    borehole = relationship("Borehole", back_populates="reports")
