from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.models.base import Base, UUIDMixin, TimestampMixin

class Alert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts"
    pillar          = Column(String(30),  nullable=False, index=True)
    type            = Column(String(50),  nullable=False)
    severity        = Column(String(20),  nullable=False)
    title           = Column(String(300), nullable=False)
    body            = Column(Text, nullable=False)
    district        = Column(String(100), nullable=False, index=True)
    source          = Column(String(100), nullable=True)
    source_ref      = Column(String(200), nullable=True)
    extra_data      = Column(JSONB, nullable=True)
    is_active       = Column(Boolean, default=True)
    expires_at      = Column(DateTime(timezone=True), nullable=True)
    sms_sent        = Column(Boolean, default=False)
    push_sent       = Column(Boolean, default=False)
    ws_broadcast    = Column(Boolean, default=False)
    recipient_count = Column(Integer, default=0)
    dispatched_at   = Column(DateTime(timezone=True), nullable=True, index=True)   # SMS phase finished (everyone sent/skipped/gave up)


class AlertDelivery(Base, UUIDMixin, TimestampMixin):
    """One row per (alert, farmer, channel): makes dispatch idempotent and gives an honest delivery record."""
    __tablename__ = "alert_deliveries"
    __table_args__ = (UniqueConstraint("alert_id", "user_id", "channel", name="uq_delivery_alert_user_channel"),)
    alert_id        = Column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    channel         = Column(String(10), nullable=False, default="sms")
    status          = Column(String(20), nullable=False)       # sent | failed | skipped_cap
    attempts        = Column(Integer, nullable=False, default=0)
    provider_status = Column(String(100), nullable=True)       # e.g. Africa's Talking status text/code
    error           = Column(Text, nullable=True)
    sent_at         = Column(DateTime(timezone=True), nullable=True)
