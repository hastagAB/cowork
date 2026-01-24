"""Permission guard — enforces filesystem access control."""

from __future__ import annotations

import logging
from pathlib import Path

from cowork.models import PermissionConfig, PermissionTier

logger = logging.getLogger(__name__)

# Extensions that are never writable by the agent
BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".msi", ".dll", ".sys"}


class PermissionGuard:
    """Checks whether a file operation is allowed based on config."""

    def __init__(self, config: PermissionConfig):
        self.config = config
        self.allowed_paths = [
            Path(p).expanduser().resolve() for p in config.allowed_paths
        ]

    def check_path(self, path: str | Path) -> PermissionTier:
        """Determine the permission tier for a given path."""
        resolved = Path(path).expanduser().resolve()

        # Block system-critical extensions
        if resolved.suffix.lower() in BLOCKED_EXTENSIONS:
            logger.warning("Blocked access to executable: %s", resolved)
            return PermissionTier.BLOCKED

        # If no allowed_paths configured, everything is allowed (first-run experience)
        if not self.allowed_paths:
            return PermissionTier.AUTO

        # Check if the path is under an allowed directory
        for allowed in self.allowed_paths:
            try:
                resolved.relative_to(allowed)
                return PermissionTier.AUTO
            except ValueError:
                continue

        logger.warning("Path outside allowed directories: %s", resolved)
        return PermissionTier.BLOCKED

    def is_allowed(self, path: str | Path) -> bool:
        tier = self.check_path(path)
        return tier != PermissionTier.BLOCKED

    def requires_confirmation(self, operation: str) -> bool:
        """Check if a destructive operation needs user confirmation."""
        if not self.config.confirm_destructive:
            return False
        return operation.upper() in ("DELETE", "MOVE", "OVERWRITE")
