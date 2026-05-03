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
from app.db.models import Doll, Photo, Container
from app.schemas.photos import PhotoResponse, PhotoListResponse, SetPrimaryResponse, ContainerPhotoResponse
from app.services import photos_service
from app.utils.media import is_valid_image, is_safe_path

router = APIRouter(tags=["photos"])
media_router = APIRouter(tags=["media"])


def build_photo_url(path: str) -> str:
    """Build a photo URL from a relative path."""
    return f"/media/{path}"


def photo_to_response(photo: Photo) -> PhotoResponse:
    """Convert a Photo model to PhotoResponse."""
    return PhotoResponse(
        id=photo.id,
        doll_id=photo.doll_id,
        container_id=photo.container_id,
        url=build_photo_url(photo.path),
        is_primary=photo.is_primary,
        created_at=photo.created_at,
        created_by=photo.created_by,
        deleted_at=photo.deleted_at,
        deleted_by=photo.deleted_by,
    )


@router.post("/dolls/{doll_id}/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    doll_id: int,
    file: Annotated[UploadFile, File(...)],
    make_primary: Annotated[Optional[bool], Form()] = True,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_ADD))] = None,
):
    """
    Upload a photo for a doll.

    NEW BEHAVIOR: All newly uploaded photos automatically become the primary photo.
    The make_primary parameter is kept for backwards compatibility but is ignored.

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

    # ALWAYS make new uploads primary - unset current primary first
    photos_service.unset_primary_photo(db, doll_id)

    # Create photo record as primary
    photo = photos_service.create_photo_record(
        db=db,
        doll_id=doll_id,
        path=relative_path,
        is_primary=True,
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

    # ALWAYS log PHOTO_SET_PRIMARY event for every upload
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
    include_deleted: bool = False,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.DOLL_READ))] = None,
):
    """List photos for a doll. include_deleted=true requires photo:restore permission."""
    doll = db.query(Doll).filter(Doll.id == doll_id).first()
    if not doll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Doll with id {doll_id} not found")

    if include_deleted and not user.has_permission(Permission.PHOTO_RESTORE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission required: {Permission.PHOTO_RESTORE}")

    query = db.query(Photo).filter(Photo.doll_id == doll_id)
    if not include_deleted:
        query = query.filter(Photo.deleted_at.is_(None))
    photos = query.order_by(Photo.created_at.desc()).all()

    primary_photo_id = next((p.id for p in photos if p.is_primary and p.deleted_at is None), None)

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


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_DELETE))] = None,
):
    """
    Soft-delete a photo. Refuses if photo is primary and other live photos exist.
    Requires: photo:delete permission (admin only).
    """
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted_at.is_(None)).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="photo not found")

    if photo.doll_id and photo.is_primary:
        other_live = db.query(Photo).filter(
            Photo.doll_id == photo.doll_id,
            Photo.id != photo_id,
            Photo.deleted_at.is_(None)
        ).count()
        if other_live > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="cannot delete primary photo — set another primary first"
            )

    photos_service.soft_delete_photo(db, photo, user.email)
    photos_service.log_photo_event(
        db=db,
        doll_id=photo.doll_id,
        event_type="PHOTO_DELETED",
        photo_id=photo.id,
        created_by=user.email,
    )
    db.commit()
    return None


@router.post("/photos/{photo_id}/restore", response_model=PhotoResponse)
async def restore_photo(
    photo_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_RESTORE))] = None,
):
    """
    Restore a soft-deleted photo.
    If restoring a doll photo and doll has no live primary, promote restored photo.
    Requires: photo:restore permission (admin only).
    """
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted_at.isnot(None)).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="photo not found")

    if photo.container_id:
        existing = db.query(Photo).filter(
            Photo.container_id == photo.container_id,
            Photo.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="container already has a photo")

    photos_service.restore_photo(db, photo)

    if photo.doll_id:
        live_primary = photos_service.get_live_primary_for_doll(db, photo.doll_id)
        if not live_primary:
            photo.is_primary = True

    photos_service.log_photo_event(
        db=db,
        doll_id=photo.doll_id,
        event_type="PHOTO_RESTORED",
        photo_id=photo.id,
        created_by=user.email,
    )
    db.commit()
    db.refresh(photo)
    return photo_to_response(photo)


@router.post("/containers/{container_id}/photo", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_container_photo(
    container_id: int,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_ADD))] = None,
):
    """
    Upload (or replace) a photo for a user-created container.
    Admin only; system containers are refused.
    Requires: photo:add permission + admin role check.
    """
    if not user.has_permission(Permission.PHOTO_DELETE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission required: {Permission.PHOTO_DELETE}")

    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="container not found")
    if container.is_system:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="system containers cannot have photos")

    if not is_valid_image(file.filename, file.content_type):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image (jpg, jpeg, png, webp, gif)")

    replaced = False
    existing = photos_service.get_live_photo_for_container(db, container_id)
    if existing:
        photos_service.soft_delete_photo(db, existing, user.email)
        replaced = True

    relative_path = await photos_service.save_container_photo_file(container_id, file)
    try:
        photo = photos_service.create_container_photo_record(db, container_id, relative_path, user.email)
        photos_service.log_container_photo_event(db, container_id, "CONTAINER_PHOTO_ADDED", photo.id, user.email)
        if replaced:
            photos_service.log_container_photo_event(db, container_id, "CONTAINER_PHOTO_REPLACED", photo.id, user.email)
        db.commit()
    except Exception:
        (settings.PHOTOS_DIR / relative_path).unlink(missing_ok=True)
        raise
    db.refresh(photo)
    return photo_to_response(photo)


@router.delete("/containers/{container_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_container_photo(
    container_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.PHOTO_DELETE))] = None,
):
    """
    Soft-delete a container's photo.
    Requires: photo:delete permission (admin only).
    """
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="container not found")
    if container.is_system:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="system containers cannot have photos")

    photo = photos_service.get_live_photo_for_container(db, container_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="container has no photo")

    photos_service.soft_delete_photo(db, photo, user.email)
    photos_service.log_container_photo_event(db, container_id, "CONTAINER_PHOTO_DELETED", photo.id, user.email)
    db.commit()
    return None


@router.get("/containers/{container_id}/photo", response_model=ContainerPhotoResponse)
async def get_container_photo(
    container_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[User, Depends(require_permission(Permission.CONTAINER_READ))] = None,
):
    """Return the live photo for a container, or null."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="container not found")
    if container.is_system:
        return ContainerPhotoResponse(photo=None)

    photo = photos_service.get_live_photo_for_container(db, container_id)
    return ContainerPhotoResponse(photo=photo_to_response(photo) if photo else None)


@media_router.get("/media/{relative_path:path}")
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

