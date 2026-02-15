"""
API endpoint for current user information.
"""
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import User, get_current_user

router = APIRouter(tags=["meta"])


class MeResponse(BaseModel):
    """Response model for /api/me endpoint."""
    id: str
    email: str
    display_name: str
    groups: list[str]
    permissions: list[str]


@router.get("/me", response_model=MeResponse)
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    """
    Get current user information including permissions.
    
    Returns:
        User identity and permissions
    """
    return MeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        groups=user.groups,
        permissions=sorted(list(user.permissions))
    )

