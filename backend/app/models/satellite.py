from sqlalchemy import Column, String, Float, Date, Integer
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base, UUIDMixin

# After alembic migration, run on TimescaleDB:
#   SELECT create_hypertable('satellite_readings', 'reading_date');

class SatelliteReading(Base, UUIDMixin):
    __tablename__ = "satellite_readings"
    district      = Column(String(100), nullable=False, index=True)
    reading_date  = Column(Date,        nullable=False, index=True)
    source        = Column(String(50),  nullable=False)
    rainfall_mm   = Column(Float, nullable=True)
    temp_max_c    = Column(Float, nullable=True)
    temp_min_c    = Column(Float, nullable=True)
    solar_kwh_m2  = Column(Float, nullable=True)
    ndvi          = Column(Float, nullable=True)
    drought_index = Column(Integer, nullable=True)
    raw_json      = Column(JSONB, nullable=True)
