from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB
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
