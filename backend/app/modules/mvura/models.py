# SQLAlchemy ORM models for Mvura — Water Security
from sqlalchemy import Column, String, Boolean, Integer, Float, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin

# TODO: Define ORM models
