"""SQLAlchemy declarative base and portable column types."""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

JSONType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    """Base class for all persistence models."""
