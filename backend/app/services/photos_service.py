"""
Photo service for business logic.
"""
import json
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Photo, Doll, Event
from app.utils.media import generate_photo_path, ensure_directory_exists


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
    doll_id: int,
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

