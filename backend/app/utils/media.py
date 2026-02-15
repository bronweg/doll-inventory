"""
Media utilities for file handling and path safety.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def is_valid_image(filename: str, content_type: Optional[str] = None) -> bool:
    """
    Check if a file is a valid image based on extension or content type.
    
    Args:
        filename: The filename to check
        content_type: Optional content type header
        
    Returns:
        True if the file is a valid image, False otherwise
    """
    # Check content type if provided
    if content_type and content_type.startswith("image/"):
        return True
    
    # Check file extension
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename: str, content_type: Optional[str] = None) -> str:
    """
    Get the file extension from filename or content type.
    
    Args:
        filename: The original filename
        content_type: Optional content type header
        
    Returns:
        File extension (e.g., '.jpg')
    """
    # Try to get extension from filename
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_EXTENSIONS:
        return ext
    
    # Fallback to content type
    if content_type:
        type_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        return type_to_ext.get(content_type, ".jpg")
    
    return ".jpg"


def generate_photo_path(doll_id: int, filename: str, content_type: Optional[str] = None) -> str:
    """
    Generate a unique photo path for storage.
    
    Format: <doll_id>/<timestamp>_<uuid>.<ext>
    Example: 123/20260215T142355Z_a1b2c3d4.jpg
    
    Args:
        doll_id: The doll ID
        filename: Original filename
        content_type: Optional content type
        
    Returns:
        Relative path for the photo
    """
    # Generate timestamp in UTC compact form
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    
    # Generate random UUID suffix
    uuid_suffix = str(uuid.uuid4()).split('-')[0]
    
    # Get file extension
    ext = get_file_extension(filename, content_type)
    
    # Construct path
    return f"{doll_id}/{timestamp}_{uuid_suffix}{ext}"


def is_safe_path(base_dir: Path, requested_path: str) -> bool:
    """
    Check if a requested path is safe (prevents path traversal attacks).
    
    Args:
        base_dir: The base directory (absolute path)
        requested_path: The requested relative path
        
    Returns:
        True if the path is safe, False otherwise
    """
    try:
        # Resolve to absolute path
        base_dir = base_dir.resolve()
        full_path = (base_dir / requested_path).resolve()
        
        # Check if the resolved path starts with the base directory
        return str(full_path).startswith(str(base_dir))
    except (ValueError, OSError):
        return False


def ensure_directory_exists(directory: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: The directory path
    """
    directory.mkdir(parents=True, exist_ok=True)

