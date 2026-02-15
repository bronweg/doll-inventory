"""
API endpoints for photo management.
"""
from typing import Annotated, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import User, require_permission, Permission
from app.core.config import settings
from app.db.session import get_db
from app.db.models import Doll, Photo
from app.schemas.photos import PhotoResponse, PhotoListResponse, SetPrimaryResponse
from app.services import photos_service
from app.utils.media import is_valid_image, is_safe_path

router = APIRouter(tags=["photos"])


def build_photo_url(path: str) -> str:
    """Build a photo URL from a relative path."""
    return f"/media/{path}"


def photo_to_response(photo: Photo) -> PhotoResponse:
    """Convert a Photo model to PhotoResponse."""
    return PhotoResponse(
        id=photo.id,
        doll_id=photo.doll_id,
        url=build_photo_url(photo.path),
        is_primary=photo.is_primary,
        created_at=photo.created_at,
        created_by=photo.created_by
    )


@router.post("/dolls/{doll_id}/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    doll_id: int,
    file: Annotated[UploadFile, File(...)],
    make_primary: Annotated[Optional[bool], Form()] = False,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_ADD))] = None,
):
    """
    Upload a photo for a doll.

    Requires: photo:add permission
    """
    # Check if doll exists
    doll = db.query(Doll).filter(Doll.id == doll_id).first()
    if not doll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doll with id {doll_id} not found"
        )

    # Validate file is an image
    if not is_valid_image(file.filename, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (jpg, jpeg, png, webp, gif)"
        )

    # Save file to disk
    relative_path = await photos_service.save_photo_file(doll_id, file)

    # Check if this is the first photo for the doll
    existing_photos_count = photos_service.get_photos_count(db, doll_id)
    is_first_photo = existing_photos_count == 0

    # Determine if this should be primary
    should_be_primary = is_first_photo or make_primary

    # If making this primary, unset current primary
    if should_be_primary and not is_first_photo:
        photos_service.unset_primary_photo(db, doll_id)

    # Create photo record
    photo = photos_service.create_photo_record(
        db=db,
        doll_id=doll_id,
        path=relative_path,
        is_primary=should_be_primary,
        created_by=user.email
    )

    # Log PHOTO_ADDED event
    photos_service.log_photo_event(
        db=db,
        doll_id=doll_id,
        event_type="PHOTO_ADDED",
        photo_id=photo.id,
        created_by=user.email,
        path=relative_path
    )

    # Log PHOTO_SET_PRIMARY event if applicable
    if should_be_primary:
        photos_service.log_photo_event(
            db=db,
            doll_id=doll_id,
            event_type="PHOTO_SET_PRIMARY",
            photo_id=photo.id,
            created_by=user.email
        )

    db.commit()
    db.refresh(photo)

    return photo_to_response(photo)


@router.get("/dolls/{doll_id}/photos", response_model=PhotoListResponse)
async def list_photos(
    doll_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.DOLL_READ))],
):
    """
    List all photos for a doll.

    Requires: doll:read permission
    """
    # Check if doll exists
    doll = db.query(Doll).filter(Doll.id == doll_id).first()
    if not doll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doll with id {doll_id} not found"
        )

    # Get photos ordered by newest first
    photos = db.query(Photo).filter(Photo.doll_id == doll_id).order_by(Photo.created_at.desc()).all()

    # Find primary photo ID
    primary_photo_id = None
    for photo in photos:
        if photo.is_primary:
            primary_photo_id = photo.id
            break

    return PhotoListResponse(
        doll_id=doll_id,
        primary_photo_id=primary_photo_id,
        photos=[photo_to_response(p) for p in photos]
    )





@router.post("/photos/{photo_id}/set-primary", response_model=SetPrimaryResponse)
async def set_primary_photo(
    photo_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_SET_PRIMARY))],
):
    """
    Set a photo as the primary photo for its doll.

    Requires: photo:set_primary permission
    """
    # Find photo
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Photo with id {photo_id} not found"
        )

    # Set as primary
    photos_service.set_photo_as_primary(db, photo)

    # Log event
    photos_service.log_photo_event(
        db=db,
        doll_id=photo.doll_id,
        event_type="PHOTO_SET_PRIMARY",
        photo_id=photo.id,
        created_by=user.email
    )

    db.commit()

    return SetPrimaryResponse(
        doll_id=photo.doll_id,
        primary_photo_id=photo.id,
        photo_id=photo.id
    )


@router.get("/media/{relative_path:path}")
async def serve_media(relative_path: str):
    """
    Serve media files.

    No authentication required (assumes app is behind LAN/SSO).
    Includes path traversal protection.
    """
    # Check path safety
    if not is_safe_path(settings.PHOTOS_DIR, relative_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Construct full path
    full_path = settings.PHOTOS_DIR / relative_path

    # Check if file exists
    if not full_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Return file
    return FileResponse(full_path)

