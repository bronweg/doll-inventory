"""
Pydantic schemas for events.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EventResponse(BaseModel):
    """Schema for event response."""
    id: int
    doll_id: int
    event_type: str
    payload: Optional[str]  # JSON string
    created_at: datetime
    created_by: str
    
    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Schema for list of events."""
    items: list[EventResponse]
    total: int
    limit: int
    offset: int

