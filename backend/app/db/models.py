"""
SQLAlchemy database models.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, Boolean
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class LocationEnum(str, enum.Enum):
    """Doll location enum (deprecated - use containers instead)."""
    HOME = "HOME"
    BAG = "BAG"


class Container(Base):
    """Container model for storage locations (bags, home, wishlist)."""
    __tablename__ = "containers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dolls = relationship("Doll", back_populates="container")

    def __repr__(self):
        return f"<Container(id={self.id}, name={self.name}, sort_order={self.sort_order})>"


class Doll(Base):
    """Doll model."""
    __tablename__ = "dolls"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)

    # New container-based storage (preferred)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True, index=True)
    purchase_url = Column(Text, nullable=True)

    # Legacy location fields (kept for backward compatibility during transition)
    location = Column(SQLEnum(LocationEnum), nullable=True, index=True)
    bag_number = Column(Integer, nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(255), nullable=True)

    # Relationships
    container = relationship("Container", back_populates="dolls")
    events = relationship("Event", back_populates="doll", cascade="all, delete-orphan")
    photos = relationship("Photo", back_populates="doll", cascade="all, delete-orphan")

    @property
    def is_deleted(self) -> bool:
        """Check if doll is soft-deleted."""
        return self.deleted_at is not None

    def __repr__(self):
        return f"<Doll(id={self.id}, name={self.name}, container_id={self.container_id})>"


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

