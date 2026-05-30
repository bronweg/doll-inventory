"""
Application configuration settings.
"""
import json
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

        # Role-to-group mapping. ROLE_GROUPS is a JSON list of objects:
        # [{"role":"admin","groups":["admins"]}, ...]
        self.ROLE_GROUPS_ERROR = None
        try:
            self.ROLE_GROUPS = self._load_role_groups()
        except ValueError as exc:
            self.ROLE_GROUPS_ERROR = str(exc)
            self.ROLE_GROUPS = self._default_role_groups()

    def validate(self):
        """Validate settings that should fail application startup."""
        if self.ROLE_GROUPS_ERROR:
            raise RuntimeError(self.ROLE_GROUPS_ERROR)

    def _load_role_groups(self) -> dict[str, set[str]]:
        raw_value = os.getenv("ROLE_GROUPS")
        if raw_value:
            try:
                entries = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"ROLE_GROUPS must be valid JSON: {exc}") from exc

            role_groups: dict[str, set[str]] = {
                "admin": set(),
                "editor": set(),
                "member": set(),
                "viewer": set(),
            }
            if not isinstance(entries, list):
                raise ValueError("ROLE_GROUPS must be a JSON list")

            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError("Each ROLE_GROUPS entry must be an object")

                role = entry.get("role")
                groups = entry.get("groups")
                if role not in role_groups:
                    raise ValueError(f"Unsupported ROLE_GROUPS role: {role!r}")
                if not isinstance(groups, list) or not all(isinstance(group, str) for group in groups):
                    raise ValueError(f"ROLE_GROUPS entry for {role!r} must contain a string groups list")

                role_groups[role].update(group.strip() for group in groups if group.strip())

            return role_groups

        return self._default_role_groups()

    def _default_role_groups(self) -> dict[str, set[str]]:
        return {
            "admin": {"dolls_admin"},
            "editor": {"dolls_editor"},
            "member": {"dolls_member"},
            "viewer": {"dolls_viewer"},
        }

    def __repr__(self):
        return (
            f"Settings(AUTH_MODE={self.AUTH_MODE}, "
            f"DATA_DIR={self.DATA_DIR}, "
            f"DB_PATH={self.DB_PATH}, "
            f"PHOTOS_DIR={self.PHOTOS_DIR})"
        )


# Global settings instance
settings = Settings()
