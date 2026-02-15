"""
Authentication adapter supporting multiple auth modes.
"""
from typing import Annotated
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings


class User:
    """User model for authentication."""
    
    def __init__(self, id: str, email: str, display_name: str, roles: set[str]):
        self.id = id
        self.email = email
        self.display_name = display_name
        self.roles = roles
    
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles
    
    def __repr__(self):
        return f"User(id={self.id}, email={self.email}, roles={self.roles})"


async def get_current_user(request: Request) -> User:
    """
    Get current user based on AUTH_MODE.
    
    AUTH_MODE=none: Returns local admin user (requires ALLOW_INSECURE_LOCAL=true)
    AUTH_MODE=forwardauth: Reads user from forwarded headers
    
    Raises:
        HTTPException: 401 if authentication fails
    """
    if settings.AUTH_MODE == "none":
        # Return local admin user
        return User(
            id="local",
            email="local@localhost",
            display_name="Local Admin",
            roles={"admin"}
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
        
        # Parse groups (comma-separated)
        groups = {g.strip() for g in groups_str.split(",") if g.strip()}
        
        # Determine roles
        roles = set()
        if settings.ADMIN_GROUP in groups:
            roles.add("admin")
        else:
            roles.add("user")
        
        return User(
            id=user_id,
            email=email,
            display_name=user_id,  # Use user_id as display name if not provided
            roles=roles
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid AUTH_MODE: {settings.AUTH_MODE}"
        )


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Dependency that requires admin role.
    
    Raises:
        HTTPException: 403 if user is not admin
    """
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return user


async def require_user_or_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Dependency that requires user or admin role.
    
    This is essentially the same as get_current_user but makes intent clearer.
    """
    return user

