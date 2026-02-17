"""
Pydantic schemas for dolls.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, HttpUrl
from enum import Enum


class LocationEnum(str, Enum):
    """Doll location enum."""
    HOME = "HOME"
    BAG = "BAG"


class DollCreate(BaseModel):
    """Schema for creating a doll."""
    name: str = Field(..., min_length=1, max_length=255, description="Doll name")

    # Preferred: container-based storage
    container_id: Optional[int] = Field(None, description="Container ID (preferred)")
    purchase_url: Optional[str] = Field(None, description="Purchase URL (for wishlist items)")

    # Deprecated: legacy location-based storage (for backward compatibility)
    location: Optional[LocationEnum] = Field(None, description="Storage location (deprecated)")
    bag_number: Optional[int] = Field(None, ge=1, description="Bag number (deprecated)")

    @field_validator('bag_number')
    @classmethod
    def validate_bag_number(cls, v, info):
        """Validate bag_number based on location."""
        location = info.data.get('location')
        if location == LocationEnum.HOME and v is not None:
            raise ValueError("bag_number must be null when location is HOME")
        if location == LocationEnum.BAG and v is None:
            raise ValueError("bag_number is required when location is BAG")
        return v

    @field_validator('container_id')
    @classmethod
    def validate_container_or_location(cls, v, info):
        """Validate that either container_id or location is provided."""
        location = info.data.get('location')
        if v is None and location is None:
            raise ValueError("Either container_id or location must be provided")
        return v


class DollUpdate(BaseModel):
    """Schema for updating a doll."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Doll name (admin only)")

    # Preferred: container-based storage
    container_id: Optional[int] = Field(None, description="Container ID")
    purchase_url: Optional[str] = Field(None, description="Purchase URL (for wishlist items)")

    # Deprecated: legacy location-based storage (for backward compatibility)
    location: Optional[LocationEnum] = Field(None, description="Storage location (deprecated)")
    bag_number: Optional[int] = Field(None, ge=1, description="Bag number (deprecated)")

    @field_validator('bag_number')
    @classmethod
    def validate_bag_number(cls, v, info):
        """Validate bag_number based on location."""
        location = info.data.get('location')
        # Only validate if location is being updated
        if location == LocationEnum.HOME and v is not None:
            raise ValueError("bag_number must be null when location is HOME")
        return v


class DollResponse(BaseModel):
    """Schema for doll response."""
    id: int
    name: str

    # Container-based storage (preferred)
    container_id: Optional[int]
    purchase_url: Optional[str] = Field(default=None)

    # Legacy location fields (for backward compatibility)
    location: Optional[LocationEnum]
    bag_number: Optional[int]

    created_at: datetime
    updated_at: datetime
    primary_photo_url: Optional[str] = Field(default=None)

    class Config:
        from_attributes = True


class DollDetailResponse(BaseModel):
    """Schema for detailed doll response."""
    id: int
    name: str

    # Container-based storage (preferred)
    container_id: Optional[int]
    purchase_url: Optional[str] = Field(default=None)

    # Legacy location fields (for backward compatibility)
    location: Optional[LocationEnum]
    bag_number: Optional[int]

    created_at: datetime
    updated_at: datetime
    primary_photo_url: Optional[str] = Field(default=None)
    photos_count: int = Field(default=0)

    class Config:
        from_attributes = True


class DollListResponse(BaseModel):
    """Schema for list of dolls."""
    items: list[DollResponse]
    total: int
    limit: int
    offset: int

