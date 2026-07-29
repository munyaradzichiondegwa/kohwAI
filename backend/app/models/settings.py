from sqlalchemy import Column, String, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base, UUIDMixin, TimestampMixin


class PlatformSetting(Base, UUIDMixin, TimestampMixin):
    """Simple key/value feature-flag + OTA config store for the admin panel.
    e.g. key='maintenance_mode', value={'enabled': false}
         key='min_app_version',  value={'ios': '1.0.0', 'android': '1.0.0'}
         key='feature_flags',    value={'musika_insurance': false, ...}
    """
    __tablename__ = "platform_settings"
    key         = Column(String(100), unique=True, nullable=False, index=True)
    value       = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    updated_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
