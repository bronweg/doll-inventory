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
from app.db.models import Doll, Event, LocationEnum, Photo, Container
from app.schemas.dolls import DollCreate, DollUpdate, DollResponse, DollDetailResponse, DollListResponse
from app.schemas.events import EventResponse, EventListResponse
from app.schemas.suggestions import SuggestionItem, SuggestionsResponse
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
        "container_id": doll.container_id,
        "purchase_url": doll.purchase_url,
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
        "container_id": doll.container_id,
        "purchase_url": doll.purchase_url,
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
    container_id: Optional[int] = Query(None, description="Filter by container ID"),
    location: Optional[LocationEnum] = Query(None, description="Filter by location (deprecated)"),
    bag: Optional[int] = Query(None, ge=1, description="Filter by bag number (deprecated)"),
    include_deleted: bool = Query(False, description="Include deleted dolls (requires doll:delete permission)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """
    List dolls with optional filtering and pagination.

    Requires: doll:read permission
    """
    # Check permission for include_deleted
    if include_deleted and not user.has_permission(Permission.DOLL_DELETE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required to view deleted dolls: {Permission.DOLL_DELETE}"
        )

    query = db.query(Doll)

    # Filter out deleted dolls by default
    if not include_deleted:
        query = query.filter(Doll.deleted_at.is_(None))

    # Apply filters
    if q:
        query = query.filter(Doll.name.ilike(f"%{q}%"))

    # Preferred: filter by container_id
    if container_id is not None:
        query = query.filter(Doll.container_id == container_id)
    # Backward compatibility: map location/bag to container_id
    elif location or bag is not None:
        if location == LocationEnum.HOME:
            # Find Home container
            home_container = db.query(Container).filter(
                Container.name == "Home",
                Container.is_system == True
            ).first()
            if home_container:
                query = query.filter(Doll.container_id == home_container.id)
        elif location == LocationEnum.BAG and bag is not None:
            # Find Bag X container
            bag_name = f"Bag {bag}"
            bag_container = db.query(Container).filter(Container.name == bag_name).first()
            if bag_container:
                query = query.filter(Doll.container_id == bag_container.id)

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


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.DOLL_READ))],
    q: str = Query(..., description="Search query (case-insensitive substring)", min_length=1),
    container_id: Optional[int] = Query(None, description="Filter by container ID"),
    location: Optional[LocationEnum] = Query(None, description="Filter by location (deprecated)"),
    bag: Optional[int] = Query(None, ge=1, description="Filter by bag number (deprecated)"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions"),
):
    """
    Get search suggestions for doll names.

    Returns suggestions ordered by:
    1. Names starting with the query (case-insensitive)
    2. Names containing the query elsewhere
    3. Alphabetically within each group

    Requires: doll:read permission
    """
    query_obj = db.query(Doll)

    # Exclude deleted dolls
    query_obj = query_obj.filter(Doll.deleted_at.is_(None))

    # Apply container filters (preferred) or legacy location filters
    if container_id is not None:
        query_obj = query_obj.filter(Doll.container_id == container_id)
    elif location or bag is not None:
        if location == LocationEnum.HOME:
            home_container = db.query(Container).filter(
                Container.name == "Home",
                Container.is_system == True
            ).first()
            if home_container:
                query_obj = query_obj.filter(Doll.container_id == home_container.id)
        elif location == LocationEnum.BAG and bag is not None:
            bag_name = f"Bag {bag}"
            bag_container = db.query(Container).filter(Container.name == bag_name).first()
            if bag_container:
                query_obj = query_obj.filter(Doll.container_id == bag_container.id)

    # Apply name filter (case-insensitive substring match)
    query_obj = query_obj.filter(Doll.name.ilike(f"%{q}%"))

    # Fetch up to 50 matches for ranking
    dolls = query_obj.limit(50).all()

    # Rank results: starts-with first, then others, alphabetically within each group
    q_lower = q.lower()
    starts_with = []
    contains = []

    for doll in dolls:
        name_lower = doll.name.lower()
        if name_lower.startswith(q_lower):
            starts_with.append(doll)
        else:
            contains.append(doll)

    # Sort each group alphabetically
    starts_with.sort(key=lambda d: d.name.lower())
    contains.sort(key=lambda d: d.name.lower())

    # Combine and limit
    ranked_dolls = (starts_with + contains)[:limit]

    # Build suggestions with photo URLs
    suggestions = []
    for doll in ranked_dolls:
        primary_photo = photos_service.get_primary_photo(db, doll.id)
        suggestions.append(SuggestionItem(
            id=doll.id,
            name=doll.name,
            primary_photo_url=build_photo_url(primary_photo.path) if primary_photo else None,
            location=doll.location.value,
            bag_number=doll.bag_number
        ))

    return SuggestionsResponse(
        q=q,
        suggestions=suggestions
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
    # Determine container_id (prefer container_id, fallback to location/bag mapping)
    container_id = doll_data.container_id

    if container_id is None and doll_data.location:
        # Map legacy location/bag to container_id
        if doll_data.location == LocationEnum.HOME:
            home_container = db.query(Container).filter(
                Container.name == "Home",
                Container.is_system == True
            ).first()
            if home_container:
                container_id = home_container.id
        elif doll_data.location == LocationEnum.BAG and doll_data.bag_number:
            bag_name = f"Bag {doll_data.bag_number}"
            bag_container = db.query(Container).filter(Container.name == bag_name).first()
            if bag_container:
                container_id = bag_container.id

    if container_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine container for doll"
        )

    # Validate container exists
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Container with id {container_id} not found"
        )

    # Create doll
    doll = Doll(
        name=doll_data.name,
        container_id=container_id,
        purchase_url=doll_data.purchase_url,
        # Keep legacy fields for backward compatibility
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
            "container_id": container_id,
            "container_name": container.name,
            "purchase_url": doll_data.purchase_url,
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
    doll = db.query(Doll).filter(Doll.id == doll_id, Doll.deleted_at.is_(None)).first()
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

    # Check permissions for container/location change
    if (doll_data.container_id is not None or doll_data.location is not None or doll_data.bag_number is not None) and not user.has_permission(Permission.DOLL_UPDATE_LOCATION):
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

    # Handle purchase_url change
    if doll_data.purchase_url is not None and doll_data.purchase_url != doll.purchase_url:
        doll.purchase_url = doll_data.purchase_url

    # Handle container change (preferred) or legacy location/bag change
    container_changed = False
    new_container_id = None

    if doll_data.container_id is not None:
        # Direct container_id update
        new_container_id = doll_data.container_id
        container_changed = new_container_id != doll.container_id
    elif doll_data.location is not None or doll_data.bag_number is not None:
        # Legacy location/bag update - map to container_id
        new_location = doll_data.location if doll_data.location is not None else doll.location

        if new_location == LocationEnum.HOME:
            home_container = db.query(Container).filter(
                Container.name == "Home",
                Container.is_system == True
            ).first()
            if home_container:
                new_container_id = home_container.id
                container_changed = new_container_id != doll.container_id
        elif new_location == LocationEnum.BAG:
            new_bag = doll_data.bag_number if doll_data.bag_number is not None else doll.bag_number
            if new_bag is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="bag_number is required when location is BAG"
                )
            bag_name = f"Bag {new_bag}"
            bag_container = db.query(Container).filter(Container.name == bag_name).first()
            if bag_container:
                new_container_id = bag_container.id
                container_changed = new_container_id != doll.container_id

    if container_changed and new_container_id is not None:
        # Validate new container exists
        new_container = db.query(Container).filter(Container.id == new_container_id).first()
        if not new_container:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Container with id {new_container_id} not found"
            )

        # Get old container name for event
        old_container_name = None
        if doll.container_id:
            old_container = db.query(Container).filter(Container.id == doll.container_id).first()
            if old_container:
                old_container_name = old_container.name

        # Log move event
        events_to_create.append(Event(
            doll_id=doll.id,
            event_type="DOLL_MOVED",
            payload=json.dumps({
                "from_container_id": doll.container_id,
                "from_container_name": old_container_name,
                "to_container_id": new_container_id,
                "to_container_name": new_container.name,
            }),
            created_by=user.email,
        ))

        # Update doll container
        doll.container_id = new_container_id

        # Update legacy fields for backward compatibility
        if new_container.name == "Home":
            doll.location = LocationEnum.HOME
            doll.bag_number = None
        elif new_container.name.startswith("Bag "):
            doll.location = LocationEnum.BAG
            try:
                doll.bag_number = int(new_container.name.split(" ")[1])
            except (IndexError, ValueError):
                pass

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


@router.delete("/{doll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doll(
    doll_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.DOLL_DELETE))],
):
    """
    Soft delete a doll.

    This hides the doll from normal lists and searches but preserves all data
    (photos, events) in the database for audit/history purposes.

    Requires: doll:delete permission
    """
    # Get doll (only if not already deleted)
    doll = db.query(Doll).filter(Doll.id == doll_id, Doll.deleted_at.is_(None)).first()
    if not doll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doll with id {doll_id} not found"
        )

    # Soft delete
    doll.deleted_at = datetime.utcnow()
    doll.deleted_by = user.email

    # Log event
    event = Event(
        doll_id=doll.id,
        event_type="DOLL_DELETED",
        payload=json.dumps({"name": doll.name}),
        created_by=user.email,
    )
    db.add(event)
    db.commit()

