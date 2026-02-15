"""
API endpoints for dolls management.
"""
import json
from typing import Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.auth import User, get_current_user, require_permission, Permission
from app.db.session import get_db
from app.db.models import Doll, Event, LocationEnum, Photo
from app.schemas.dolls import DollCreate, DollUpdate, DollResponse, DollDetailResponse, DollListResponse
from app.schemas.events import EventResponse, EventListResponse
from app.services import photos_service

router = APIRouter(prefix="/dolls", tags=["dolls"])


def build_photo_url(path: str) -> str:
    """Build a photo URL from a relative path."""
    return f"/media/{path}"


def enrich_doll_with_photo(doll: Doll, db: Session) -> dict:
    """Enrich a doll object with primary_photo_url."""
    primary_photo = photos_service.get_primary_photo(db, doll.id)
    return {
        "id": doll.id,
        "name": doll.name,
        "location": doll.location,
        "bag_number": doll.bag_number,
        "created_at": doll.created_at,
        "updated_at": doll.updated_at,
        "primary_photo_url": build_photo_url(primary_photo.path) if primary_photo else None,
    }


def enrich_doll_with_photo_detail(doll: Doll, db: Session) -> dict:
    """Enrich a doll object with primary_photo_url and photos_count."""
    primary_photo = photos_service.get_primary_photo(db, doll.id)
    photos_count = photos_service.get_photos_count(db, doll.id)
    return {
        "id": doll.id,
        "name": doll.name,
        "location": doll.location,
        "bag_number": doll.bag_number,
        "created_at": doll.created_at,
        "updated_at": doll.updated_at,
        "primary_photo_url": build_photo_url(primary_photo.path) if primary_photo else None,
        "photos_count": photos_count,
    }


@router.get("", response_model=DollListResponse)
async def list_dolls(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.DOLL_READ))],
    q: Optional[str] = Query(None, description="Search query (case-insensitive substring)"),
    location: Optional[LocationEnum] = Query(None, description="Filter by location"),
    bag: Optional[int] = Query(None, ge=1, description="Filter by bag number"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """
    List dolls with optional filtering and pagination.

    Requires: doll:read permission
    """
    query = db.query(Doll)
    
    # Apply filters
    if q:
        query = query.filter(Doll.name.ilike(f"%{q}%"))
    if location:
        query = query.filter(Doll.location == location)
    if bag is not None:
        query = query.filter(Doll.bag_number == bag)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    dolls = query.order_by(Doll.created_at.desc()).offset(offset).limit(limit).all()

    # Enrich dolls with primary photo URLs
    enriched_dolls = [enrich_doll_with_photo(doll, db) for doll in dolls]

    return DollListResponse(
        items=enriched_dolls,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("", response_model=DollResponse, status_code=status.HTTP_201_CREATED)
async def create_doll(
    doll_data: DollCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.DOLL_CREATE))],
):
    """
    Create a new doll.

    Requires: doll:create permission
    """
    # Create doll
    doll = Doll(
        name=doll_data.name,
        location=doll_data.location,
        bag_number=doll_data.bag_number,
    )
    db.add(doll)
    db.flush()  # Flush to get the ID
    
    # Log event
    event = Event(
        doll_id=doll.id,
        event_type="DOLL_CREATED",
        payload=json.dumps({
            "name": doll_data.name,
            "location": doll_data.location.value,
            "bag_number": doll_data.bag_number,
        }),
        created_by=user.email,
    )
    db.add(event)
    db.commit()
    db.refresh(doll)

    return enrich_doll_with_photo(doll, db)


@router.get("/{doll_id}", response_model=DollDetailResponse)
async def get_doll(
    doll_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.DOLL_READ))],
):
    """
    Get a specific doll by ID.

    Requires: doll:read permission
    """
    doll = db.query(Doll).filter(Doll.id == doll_id).first()
    if not doll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doll with id {doll_id} not found"
        )
    return enrich_doll_with_photo_detail(doll, db)


@router.patch("/{doll_id}", response_model=DollResponse)
async def update_doll(
    doll_id: int,
    doll_data: DollUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """
    Update a doll.

    Access control:
    - doll:update_location permission required for location/bag changes
    - doll:rename permission required for name changes
    """
    # Get doll
    doll = db.query(Doll).filter(Doll.id == doll_id).first()
    if not doll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doll with id {doll_id} not found"
        )

    # Check permissions for name change
    if doll_data.name is not None and not user.has_permission(Permission.DOLL_RENAME):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {Permission.DOLL_RENAME}"
        )

    # Check permissions for location change
    if (doll_data.location is not None or doll_data.bag_number is not None) and not user.has_permission(Permission.DOLL_UPDATE_LOCATION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {Permission.DOLL_UPDATE_LOCATION}"
        )
    
    # Track changes for events
    events_to_create = []
    
    # Handle name change
    if doll_data.name is not None and doll_data.name != doll.name:
        events_to_create.append(Event(
            doll_id=doll.id,
            event_type="DOLL_RENAMED",
            payload=json.dumps({
                "old_name": doll.name,
                "new_name": doll_data.name,
            }),
            created_by=user.email,
        ))
        doll.name = doll_data.name

    # Handle location/bag change
    location_changed = doll_data.location is not None and doll_data.location != doll.location
    bag_changed = doll_data.bag_number is not None and doll_data.bag_number != doll.bag_number

    if location_changed or bag_changed:
        # Determine new location and bag
        new_location = doll_data.location if doll_data.location is not None else doll.location
        new_bag = doll_data.bag_number if doll_data.bag_number is not None else doll.bag_number

        # Validate location/bag combination
        if new_location == LocationEnum.HOME and new_bag is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bag_number must be null when location is HOME"
            )
        if new_location == LocationEnum.BAG and new_bag is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bag_number is required when location is BAG"
            )

        # Log move event
        events_to_create.append(Event(
            doll_id=doll.id,
            event_type="DOLL_MOVED",
            payload=json.dumps({
                "old_location": doll.location.value,
                "old_bag_number": doll.bag_number,
                "new_location": new_location.value,
                "new_bag_number": new_bag,
            }),
            created_by=user.email,
        ))

        # Update doll
        if doll_data.location is not None:
            doll.location = doll_data.location
        if doll_data.bag_number is not None:
            doll.bag_number = doll_data.bag_number
        elif doll_data.location == LocationEnum.HOME:
            # Clear bag_number when moving to HOME
            doll.bag_number = None

    # Update timestamp
    doll.updated_at = datetime.utcnow()

    # Save changes
    for event in events_to_create:
        db.add(event)
    db.commit()
    db.refresh(doll)

    return enrich_doll_with_photo(doll, db)


@router.get("/{doll_id}/events", response_model=EventListResponse)
async def get_doll_events(
    doll_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.EVENT_READ))],
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """
    Get events for a specific doll.

    Requires: event:read permission
    """
    # Check if doll exists
    doll = db.query(Doll).filter(Doll.id == doll_id).first()
    if not doll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doll with id {doll_id} not found"
        )

    # Get events
    query = db.query(Event).filter(Event.doll_id == doll_id)
    total = query.count()
    events = query.order_by(Event.created_at.desc()).offset(offset).limit(limit).all()

    return EventListResponse(
        items=events,
        total=total,
        limit=limit,
        offset=offset
    )

