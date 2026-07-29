from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, Integer, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin

class MarketListing(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "market_listings"
    seller_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    type         = Column(String(30), nullable=False)
    title        = Column(String(300), nullable=False)
    description  = Column(Text, nullable=True)
    quantity     = Column(Float, nullable=False)
    unit         = Column(String(30), nullable=False)
    price_usd    = Column(Numeric(10, 2), nullable=False)
    district     = Column(String(100), nullable=False, index=True)
    is_active    = Column(Boolean, default=True)
    expires_at   = Column(DateTime(timezone=True), nullable=True)
    ai_verified_healthy  = Column(Boolean, nullable=True)
    livestock_profile_id = Column(UUID(as_uuid=True), nullable=True)
    seller = relationship("User", back_populates="listings")

class InsuranceEnrollment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "insurance_enrollments"
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    district          = Column(String(100), nullable=False)
    season            = Column(String(20), nullable=False)
    payout_amount_usd = Column(Numeric(10, 2), default=15.00)
    is_active         = Column(Boolean, default=True)
    ecocash_number    = Column(String(20), nullable=True)

class PayoutRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payout_records"
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("insurance_enrollments.id"), nullable=False)
    district      = Column(String(100), nullable=False)
    drought_index = Column(Integer, nullable=False)
    amount_usd    = Column(Numeric(10, 2), nullable=False)
    ecocash_ref   = Column(String(200), nullable=True)
    status        = Column(String(30), default="pending")
    sent_at       = Column(DateTime(timezone=True), nullable=True)
