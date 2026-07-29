from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    phone          = Column(String(20),  unique=True, nullable=False, index=True)
    language       = Column(String(5),   default="en", nullable=False)
    district       = Column(String(100), nullable=True)
    roles          = Column(ARRAY(String), default=["farmer"], nullable=False)
    is_active      = Column(Boolean, default=True)
    totp_secret    = Column(String(64),  nullable=True)
    fcm_token      = Column(String(512), nullable=True)
    ussd_language  = Column(String(5),   default="en")
    data_export_requested_at = Column(DateTime(timezone=True), nullable=True)
    diagnoses = relationship("DiagnosisReport", back_populates="user")
    livestock  = relationship("LivestockProfile",  back_populates="owner")
    listings   = relationship("MarketListing",     back_populates="seller")

class OTPLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "otp_logs"
    phone      = Column(String(20), nullable=False, index=True)
    otp_hash   = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used       = Column(Boolean, default=False)
    attempts   = Column(Integer, default=0)
    ip_address = Column(String(45), nullable=True)

class AuditLog(Base, UUIDMixin):
    """Immutable. No UPDATE or DELETE ever issued against this table."""
    __tablename__ = "audit_logs"
    from sqlalchemy import DateTime as DT, func as fn
    timestamp   = Column(DT(timezone=True), server_default="now()", nullable=False, index=True)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action      = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False)
    entity_id   = Column(String(200), nullable=True)
    before      = Column(Text, nullable=True)
    after       = Column(Text, nullable=True)
    ip_address  = Column(String(45), nullable=True)
