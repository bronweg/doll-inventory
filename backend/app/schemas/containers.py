"""
Pydantic schemas for containers.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ContainerResponse(BaseModel):
    """Schema for container response."""
    id: int
    name: str
    sort_order: int
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ContainerCreate(BaseModel):
    """Schema for creating a container."""
    name: str = Field(..., min_length=1, max_length=255, description="Container name")


class ContainerUpdate(BaseModel):
    """Schema for updating a container."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Container name")
    sort_order: Optional[int] = Field(None, description="Sort order")
    is_active: Optional[bool] = Field(None, description="Active status")


class ContainerListResponse(BaseModel):
    """Schema for list of containers."""
    items: list[ContainerResponse]
    total: int

