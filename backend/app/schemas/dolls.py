"""
Pydantic schemas for dolls.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class LocationEnum(str, Enum):
    """Doll location enum."""
    HOME = "HOME"
    BAG = "BAG"


class DollCreate(BaseModel):
    """Schema for creating a doll."""
    name: str = Field(..., min_length=1, max_length=255, description="Doll name")
    location: LocationEnum = Field(..., description="Storage location")
    bag_number: Optional[int] = Field(None, ge=1, description="Bag number (required if location=BAG)")
    
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


class DollUpdate(BaseModel):
    """Schema for updating a doll."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Doll name (admin only)")
    location: Optional[LocationEnum] = Field(None, description="Storage location")
    bag_number: Optional[int] = Field(None, ge=1, description="Bag number")
    
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
    location: LocationEnum
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
    location: LocationEnum
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

