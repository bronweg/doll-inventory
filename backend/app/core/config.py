"""
Application configuration settings.
"""
import os
from pathlib import Path


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Authentication mode: 'none' or 'forwardauth'
        self.AUTH_MODE = os.getenv("AUTH_MODE", "none")

        # Allow insecure local mode (required for AUTH_MODE=none)
        self.ALLOW_INSECURE_LOCAL = os.getenv("ALLOW_INSECURE_LOCAL", "false").lower() == "true"

        # Data directory
        self.DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))

        # Database path
        self.DB_PATH = Path(os.getenv("DB_PATH", "/data/db/app.sqlite"))

        # Photos directory
        self.PHOTOS_DIR = Path(os.getenv("PHOTOS_DIR", "/data/photos"))

        # Forward auth header names (for AUTH_MODE=forwardauth)
        self.AUTH_HEADER_USER = os.getenv("AUTH_HEADER_USER", "X-Forwarded-User")
        self.AUTH_HEADER_EMAIL = os.getenv("AUTH_HEADER_EMAIL", "X-Forwarded-Email")
        self.AUTH_HEADER_GROUPS = os.getenv("AUTH_HEADER_GROUPS", "X-Forwarded-Groups")

        # Group names for permission assignment
        self.ADMIN_GROUP = os.getenv("ADMIN_GROUP", "dolls_admin")
        self.EDITOR_GROUP = os.getenv("EDITOR_GROUP", "dolls_editor")
        self.KID_GROUP = os.getenv("KID_GROUP", "dolls_kid")

    def __repr__(self):
        return (
            f"Settings(AUTH_MODE={self.AUTH_MODE}, "
            f"DATA_DIR={self.DATA_DIR}, "
            f"DB_PATH={self.DB_PATH}, "
            f"PHOTOS_DIR={self.PHOTOS_DIR})"
        )


# Global settings instance
settings = Settings()

