"""
API endpoints for containers management.
"""
from typing import Annotated
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.auth import User, require_permission, Permission
from app.db.session import get_db
from app.db.models import Container, Doll
from app.schemas.containers import ContainerCreate, ContainerUpdate, ContainerResponse, ContainerListResponse

router = APIRouter(prefix="/containers", tags=["containers"])


@router.get("", response_model=ContainerListResponse)
async def list_containers(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.CONTAINER_READ))],
):
    """
    List all active containers ordered by sort_order.

    Requires: container:read permission
    """
    query = db.query(Container).filter(Container.is_active == True)
    
    # Get total count
    total = query.count()
    
    # Get containers ordered by sort_order
    containers = query.order_by(Container.sort_order.asc()).all()
    
    return ContainerListResponse(
        items=containers,
        total=total
    )


@router.post("", response_model=ContainerResponse, status_code=status.HTTP_201_CREATED)
async def create_container(
    container_data: ContainerCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.CONTAINER_MANAGE))],
):
    """
    Create a new container (bag).

    Requires: container:manage permission (admin only)
    """
    # Validate name is unique among active containers (case-insensitive)
    existing = db.query(Container).filter(
        func.lower(Container.name) == func.lower(container_data.name),
        Container.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Container with name '{container_data.name}' already exists"
        )
    
    # Calculate sort_order (max + 10)
    max_sort_order = db.query(func.max(Container.sort_order)).scalar() or 0
    sort_order = max_sort_order + 10
    
    # Create container
    container = Container(
        name=container_data.name,
        sort_order=sort_order,
        is_active=True,
        is_system=False,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    
    return container


@router.patch("/{container_id}", response_model=ContainerResponse)
async def update_container(
    container_id: int,
    container_data: ContainerUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.CONTAINER_MANAGE))],
):
    """
    Update a container (rename, change sort_order, or activate/deactivate).

    Requires: container:manage permission (admin only)
    """
    # Get container
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Container with id {container_id} not found"
        )
    
    # Update name if provided
    if container_data.name is not None:
        # Validate name is unique among active containers (case-insensitive)
        existing = db.query(Container).filter(
            func.lower(Container.name) == func.lower(container_data.name),
            Container.is_active == True,
            Container.id != container_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Container with name '{container_data.name}' already exists"
            )
        
        container.name = container_data.name
    
    # Update sort_order if provided
    if container_data.sort_order is not None:
        container.sort_order = container_data.sort_order
    
    # Update is_active if provided
    if container_data.is_active is not None:
        # Prevent deactivating system containers
        if container.is_system and not container_data.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate system containers"
            )
        container.is_active = container_data.is_active
    
    # Update timestamp
    container.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(container)
    
    return container


@router.delete("/{container_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_container(
    container_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission(Permission.CONTAINER_MANAGE))],
):
    """
    Soft delete a container (set is_active=false).
    
    Only allowed if:
    - Container is not a system container
    - Container has no dolls assigned

    Requires: container:manage permission (admin only)
    """
    # Get container
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Container with id {container_id} not found"
        )
    
    # Check if system container
    if container.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system containers"
        )
    
    # Check if container has dolls
    doll_count = db.query(Doll).filter(
        Doll.container_id == container_id,
        Doll.deleted_at.is_(None)
    ).count()
    
    if doll_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Container not empty. It contains {doll_count} doll(s)."
        )
    
    # Soft delete (set is_active=false)
    container.is_active = False
    container.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None

