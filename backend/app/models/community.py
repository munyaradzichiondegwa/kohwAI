from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, UUIDMixin, TimestampMixin

class CommunityReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "community_reports"
    submitter_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    report_type      = Column(String(50), nullable=False)
    entity_id        = Column(UUID(as_uuid=True), nullable=True)
    district         = Column(String(100), nullable=False, index=True)
    description      = Column(Text, nullable=True)
    photo_s3_key     = Column(String(512), nullable=True)
    lat              = Column(Float, nullable=True)
    lng              = Column(Float, nullable=True)
    ai_disease       = Column(String(300), nullable=True)
    ai_confidence    = Column(Float, nullable=True)
    status           = Column(String(20), default="pending")
    reviewed_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at      = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

class ValidatorAssignment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "validator_assignments"
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    district         = Column(String(100), nullable=False, index=True)
    assigned_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_active        = Column(Boolean, default=True)
    reports_reviewed = Column(Integer, default=0)
    last_active_at   = Column(DateTime(timezone=True), nullable=True)
