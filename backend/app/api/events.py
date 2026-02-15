"""
API endpoints for events.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import User, require_permission, Permission
from app.db.session import get_db
from app.db.models import Event
from app.schemas.events import EventResponse, EventListResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.EVENT_READ))],
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """
    List all events with pagination.

    Requires: event:read permission
    """
    query = db.query(Event)
    total = query.count()
    events = query.order_by(Event.created_at.desc()).offset(offset).limit(limit).all()
    
    return EventListResponse(
        items=events,
        total=total,
        limit=limit,
        offset=offset
    )

