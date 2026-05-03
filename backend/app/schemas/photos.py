"""
Pydantic schemas for photos.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PhotoResponse(BaseModel):
    """Schema for a single photo."""
    id: int
    doll_id: Optional[int] = None
    container_id: Optional[int] = None
    url: str
    is_primary: bool
    created_at: datetime
    created_by: str
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    """Schema for list of photos for a doll."""
    doll_id: int
    primary_photo_id: Optional[int] = None
    photos: list[PhotoResponse]


class SetPrimaryResponse(BaseModel):
    """Schema for set primary photo response."""
    doll_id: int
    primary_photo_id: int
    photo_id: int


class ContainerPhotoResponse(BaseModel):
    """Schema for container photo response (wraps nullable photo)."""
    photo: Optional[PhotoResponse] = None
