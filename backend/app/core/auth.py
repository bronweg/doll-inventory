"""
Authentication adapter supporting multiple auth modes.
"""
from typing import Annotated
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings


# Permission constants
class Permission:
    """Permission constants for the application."""
    DOLL_READ = "doll:read"
    DOLL_CREATE = "doll:create"
    DOLL_UPDATE_LOCATION = "doll:update_location"
    DOLL_RENAME = "doll:rename"
    DOLL_DELETE = "doll:delete"
    PHOTO_ADD = "photo:add"
    PHOTO_SET_PRIMARY = "photo:set_primary"
    EVENT_READ = "event:read"

    @classmethod
    def all_permissions(cls) -> set[str]:
        """Return all available permissions."""
        return {
            cls.DOLL_READ,
            cls.DOLL_CREATE,
            cls.DOLL_UPDATE_LOCATION,
            cls.DOLL_RENAME,
            cls.DOLL_DELETE,
            cls.PHOTO_ADD,
            cls.PHOTO_SET_PRIMARY,
            cls.EVENT_READ,
        }


class User:
    """User model for authentication."""

    def __init__(
        self,
        id: str,
        email: str,
        display_name: str,
        groups: list[str] = None,
        permissions: set[str] = None
    ):
        self.id = id
        self.email = email
        self.display_name = display_name
        self.groups = groups or []
        self.permissions = permissions or set()

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def __repr__(self):
        return f"User(id={self.id}, email={self.email}, permissions={self.permissions})"


def _compute_permissions(groups: list[str]) -> set[str]:
    """
    Compute permissions based on user groups.

    Rules:
    - Admin group: ALL permissions
    - Editor group: create, rename, move, photos, events, read
    - Kid group (or default): read, move, photo add, set primary, event read
    """
    groups_set = set(groups)

    # Admin gets all permissions
    if settings.ADMIN_GROUP in groups_set:
        return Permission.all_permissions()

    # Editor gets most permissions (all except nothing - they get everything for now)
    if settings.EDITOR_GROUP in groups_set:
        return {
            Permission.DOLL_READ,
            Permission.DOLL_CREATE,
            Permission.DOLL_UPDATE_LOCATION,
            Permission.DOLL_RENAME,
            Permission.PHOTO_ADD,
            Permission.PHOTO_SET_PRIMARY,
            Permission.EVENT_READ,
        }

    # Default (kid) permissions
    return {
        Permission.DOLL_READ,
        Permission.DOLL_UPDATE_LOCATION,
        Permission.PHOTO_ADD,
        Permission.PHOTO_SET_PRIMARY,
        Permission.EVENT_READ,
    }


async def get_current_user(request: Request) -> User:
    """
    Get current user based on AUTH_MODE.

    AUTH_MODE=none: Returns local admin user with ALL permissions (requires ALLOW_INSECURE_LOCAL=true)
    AUTH_MODE=forwardauth: Reads user from forwarded headers and computes permissions from groups

    Raises:
        HTTPException: 401 if authentication fails
    """
    if settings.AUTH_MODE == "none":
        # Enforce ALLOW_INSECURE_LOCAL for safety
        if not settings.ALLOW_INSECURE_LOCAL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AUTH_MODE=none requires ALLOW_INSECURE_LOCAL=true"
            )

        # Return local admin user with ALL permissions
        return User(
            id="local",
            email="local@localhost",
            display_name="Local Admin",
            groups=["local"],
            permissions=Permission.all_permissions()
        )

    elif settings.AUTH_MODE == "forwardauth":
        # Read headers set by reverse proxy
        user_id = request.headers.get(settings.AUTH_HEADER_USER)
        email = request.headers.get(settings.AUTH_HEADER_EMAIL)
        groups_str = request.headers.get(settings.AUTH_HEADER_GROUPS, "")

        # Validate required headers
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing required auth headers: {settings.AUTH_HEADER_USER}, {settings.AUTH_HEADER_EMAIL}"
            )

        # Parse groups (support comma, semicolon, and space delimiters)
        # Replace semicolons and spaces with commas, then split
        groups_normalized = groups_str.replace(";", ",").replace(" ", ",")
        groups = [g.strip() for g in groups_normalized.split(",") if g.strip()]

        # Compute permissions from groups
        permissions = _compute_permissions(groups)

        return User(
            id=user_id,
            email=email,
            display_name=user_id,  # Use user_id as display name if not provided
            groups=groups,
            permissions=permissions
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid AUTH_MODE: {settings.AUTH_MODE}"
        )


def require_permission(permission: str):
    """
    Dependency factory that requires a specific permission.

    Usage:
        @router.get("/endpoint")
        async def endpoint(user: Annotated[User, Depends(require_permission(Permission.DOLL_READ))]):
            ...

    Raises:
        HTTPException: 403 if user doesn't have the required permission
    """
    async def _check_permission(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return user

    return _check_permission


# Legacy dependencies (kept for backward compatibility, but prefer require_permission)
async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Dependency that requires admin-level permissions (all permissions).

    Raises:
        HTTPException: 403 if user doesn't have all permissions
    """
    if user.permissions != Permission.all_permissions():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    return user


async def require_user_or_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Dependency that requires authenticated user.

    This is essentially the same as get_current_user but makes intent clearer.
    """
    return user

