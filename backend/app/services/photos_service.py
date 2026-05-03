"""
Photo service for business logic.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Photo, Doll, Container, Event
from app.utils.media import generate_photo_path, ensure_directory_exists, get_file_extension


async def save_photo_file(doll_id: int, file: UploadFile) -> str:
    """
    Save an uploaded photo file to disk.
    
    Args:
        doll_id: The doll ID
        file: The uploaded file
        
    Returns:
        Relative path where the file was saved
    """
    # Generate unique path
    relative_path = generate_photo_path(doll_id, file.filename, file.content_type)
    
    # Construct full path
    full_path = settings.PHOTOS_DIR / relative_path
    
    # Ensure directory exists
    ensure_directory_exists(full_path.parent)
    
    # Save file
    with open(full_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    return relative_path


def create_photo_record(
    db: Session,
    doll_id: int,
    path: str,
    is_primary: bool,
    created_by: str
) -> Photo:
    """
    Create a photo record in the database.
    
    Args:
        db: Database session
        doll_id: The doll ID
        path: Relative path to the photo
        is_primary: Whether this is the primary photo
        created_by: User who created the photo
        
    Returns:
        The created Photo object
    """
    photo = Photo(
        doll_id=doll_id,
        path=path,
        is_primary=is_primary,
        created_by=created_by
    )
    db.add(photo)
    db.flush()
    return photo


def unset_primary_photo(db: Session, doll_id: int) -> None:
    """
    Unset the current primary photo for a doll.
    
    Args:
        db: Database session
        doll_id: The doll ID
    """
    db.query(Photo).filter(
        Photo.doll_id == doll_id,
        Photo.is_primary == True
    ).update({"is_primary": False})


def set_photo_as_primary(db: Session, photo: Photo) -> None:
    """
    Set a photo as the primary photo for its doll.
    
    Args:
        db: Database session
        photo: The photo to set as primary
    """
    # Unset current primary
    unset_primary_photo(db, photo.doll_id)
    
    # Set this photo as primary
    photo.is_primary = True


def log_photo_event(
    db: Session,
    doll_id: Optional[int],
    event_type: str,
    photo_id: int,
    created_by: str,
    path: Optional[str] = None
) -> None:
    """
    Log a photo-related event.
    
    Args:
        db: Database session
        doll_id: The doll ID
        event_type: Event type (PHOTO_ADDED, PHOTO_SET_PRIMARY)
        photo_id: The photo ID
        created_by: User who triggered the event
        path: Optional photo path (for PHOTO_ADDED)
    """
    payload = {"photo_id": photo_id}
    if path:
        payload["path"] = path
    
    event = Event(
        doll_id=doll_id,
        event_type=event_type,
        payload=json.dumps(payload),
        created_by=created_by
    )
    db.add(event)


def get_primary_photo(db: Session, doll_id: int) -> Optional[Photo]:
    """
    Get the primary photo for a doll.
    
    Args:
        db: Database session
        doll_id: The doll ID
        
    Returns:
        The primary Photo object or None
    """
    return db.query(Photo).filter(
        Photo.doll_id == doll_id,
        Photo.is_primary == True
    ).first()


def get_photos_count(db: Session, doll_id: int) -> int:
    """
    Get the count of photos for a doll.

    Args:
        db: Database session
        doll_id: The doll ID

    Returns:
        Number of photos
    """
    return db.query(Photo).filter(Photo.doll_id == doll_id).count()


def soft_delete_photo(db: Session, photo: Photo, deleted_by: str) -> None:
    """Mark a photo as soft-deleted."""
    photo.deleted_at = datetime.utcnow()
    photo.deleted_by = deleted_by


def restore_photo(db: Session, photo: Photo) -> None:
    """Clear soft-delete flags on a photo."""
    photo.deleted_at = None
    photo.deleted_by = None


def get_live_photos_for_doll(db: Session, doll_id: int) -> list[Photo]:
    """Return non-deleted photos for a doll, newest first."""
    return (
        db.query(Photo)
        .filter(Photo.doll_id == doll_id, Photo.deleted_at.is_(None))
        .order_by(Photo.created_at.desc())
        .all()
    )


def get_live_primary_for_doll(db: Session, doll_id: int) -> Optional[Photo]:
    """Return the live primary photo for a doll, or None."""
    return db.query(Photo).filter(
        Photo.doll_id == doll_id,
        Photo.is_primary == True,
        Photo.deleted_at.is_(None)
    ).first()


def get_live_photo_for_container(db: Session, container_id: int) -> Optional[Photo]:
    """Return the live photo for a container, or None."""
    return db.query(Photo).filter(
        Photo.container_id == container_id,
        Photo.deleted_at.is_(None)
    ).first()


def create_container_photo_record(
    db: Session,
    container_id: int,
    path: str,
    created_by: str
) -> Photo:
    """Create a primary photo record for a container."""
    photo = Photo(
        container_id=container_id,
        path=path,
        is_primary=True,
        created_by=created_by
    )
    db.add(photo)
    db.flush()
    return photo


async def save_container_photo_file(container_id: int, file) -> str:
    """Save an uploaded container photo file to disk."""
    ext = get_file_extension(file.filename, file.content_type)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    uuid_suffix = str(uuid.uuid4()).split('-')[0]
    relative_path = f"containers/{container_id}/{timestamp}_{uuid_suffix}{ext}"
    full_path = settings.PHOTOS_DIR / relative_path
    ensure_directory_exists(full_path.parent)
    with open(full_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return relative_path


def log_container_photo_event(
    db: Session,
    container_id: int,
    event_type: str,
    photo_id: int,
    created_by: str
) -> None:
    """Log a container-photo event (doll_id = NULL)."""
    payload = {"photo_id": photo_id, "container_id": container_id}
    event = Event(
        doll_id=None,
        event_type=event_type,
        payload=json.dumps(payload),
        created_by=created_by
    )
    db.add(event)

