"""
SQLAlchemy database models.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, Boolean
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class LocationEnum(str, enum.Enum):
    """Doll location enum."""
    HOME = "HOME"
    BAG = "BAG"


class Doll(Base):
    """Doll model."""
    __tablename__ = "dolls"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    location = Column(SQLEnum(LocationEnum), nullable=False, index=True)
    bag_number = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    events = relationship("Event", back_populates="doll", cascade="all, delete-orphan")
    photos = relationship("Photo", back_populates="doll", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Doll(id={self.id}, name={self.name}, location={self.location})>"


class Event(Base):
    """Event model for tracking doll changes."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doll_id = Column(Integer, ForeignKey("dolls.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_by = Column(String(255), nullable=False)  # email or user id

    # Relationship to doll
    doll = relationship("Doll", back_populates="events")

    def __repr__(self):
        return f"<Event(id={self.id}, doll_id={self.doll_id}, event_type={self.event_type})>"



class Photo(Base):
    """Photo model for doll images."""
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doll_id = Column(Integer, ForeignKey("dolls.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(500), nullable=False)  # Relative path under PHOTOS_DIR
    is_primary = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)  # email or user id

    # Relationship to doll
    doll = relationship("Doll", back_populates="photos")

    def __repr__(self):
        return f"<Photo(id={self.id}, doll_id={self.doll_id}, is_primary={self.is_primary})>"

