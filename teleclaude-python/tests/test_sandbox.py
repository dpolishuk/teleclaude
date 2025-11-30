"""Test directory sandbox."""
import pytest
from pathlib import Path
from src.security.sandbox import Sandbox
from src.exceptions import SandboxError


@pytest.fixture
def sandbox(tmp_path):
    """Create sandbox with temp directory."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "subdir").mkdir()
    return Sandbox(allowed_paths=[str(allowed)])


def test_is_path_allowed_in_allowed_dir(sandbox, tmp_path):
    """Paths within allowed directories are allowed."""
    allowed = tmp_path / "allowed"
    assert sandbox.is_path_allowed(str(allowed)) is True
    assert sandbox.is_path_allowed(str(allowed / "subdir")) is True
    assert sandbox.is_path_allowed(str(allowed / "subdir" / "file.txt")) is True


def test_is_path_allowed_outside_not_allowed(sandbox, tmp_path):
    """Paths outside allowed directories are not allowed."""
    outside = tmp_path / "outside"
    assert sandbox.is_path_allowed(str(outside)) is False
    assert sandbox.is_path_allowed("/etc/passwd") is False


def test_is_path_allowed_traversal_blocked(sandbox, tmp_path):
    """Path traversal attempts are blocked."""
    allowed = tmp_path / "allowed"
    traversal = str(allowed / ".." / "outside")
    assert sandbox.is_path_allowed(traversal) is False


def test_validate_path_raises_on_invalid(sandbox):
    """validate_path raises SandboxError for invalid paths."""
    with pytest.raises(SandboxError):
        sandbox.validate_path("/etc/passwd")


def test_validate_path_returns_resolved(sandbox, tmp_path):
    """validate_path returns resolved path for valid paths."""
    allowed = tmp_path / "allowed"
    result = sandbox.validate_path(str(allowed / "subdir"))
    assert result == str((allowed / "subdir").resolve())


def test_empty_sandbox_allows_nothing():
    """Sandbox with no allowed paths allows nothing."""
    sandbox = Sandbox(allowed_paths=[])
    assert sandbox.is_path_allowed("/home/user") is False
