"""
Pydantic schemas for photos.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PhotoResponse(BaseModel):
    """Schema for photo response."""
    id: int
    doll_id: int
    url: str
    is_primary: bool
    created_at: datetime
    created_by: str
    
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

