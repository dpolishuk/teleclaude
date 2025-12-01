"""Directory sandboxing for security."""
from pathlib import Path

from src.exceptions import SandboxError


class Sandbox:
    """Directory sandbox to restrict file access."""

    def __init__(self, allowed_paths: list[str]):
        """Initialize with list of allowed base paths."""
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]

    def is_path_allowed(self, path: str) -> bool:
        """Check if path is within allowed directories."""
        if not self.allowed_paths:
            return False

        try:
            resolved = Path(path).resolve()
            return any(
                self._is_subpath(resolved, allowed) for allowed in self.allowed_paths
            )
        except (OSError, ValueError):
            return False

    def validate_path(self, path: str) -> str:
        """Validate path and return resolved path or raise SandboxError."""
        if not self.is_path_allowed(path):
            raise SandboxError(f"Path not allowed: {path}")
        return str(Path(path).resolve())

    def _is_subpath(self, path: Path, parent: Path) -> bool:
        """Check if path is equal to or a subpath of parent."""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False
