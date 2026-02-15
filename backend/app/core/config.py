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

        # Data directory
        self.DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))

        # Database path
        self.DB_PATH = Path(os.getenv("DB_PATH", "/data/db/app.sqlite"))

        # Photos directory
        self.PHOTOS_DIR = Path(os.getenv("PHOTOS_DIR", "/data/photos"))

    def __repr__(self):
        return (
            f"Settings(AUTH_MODE={self.AUTH_MODE}, "
            f"DATA_DIR={self.DATA_DIR}, "
            f"DB_PATH={self.DB_PATH}, "
            f"PHOTOS_DIR={self.PHOTOS_DIR})"
        )


# Global settings instance
settings = Settings()

