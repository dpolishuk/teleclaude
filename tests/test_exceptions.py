"""Test custom exceptions."""
import pytest
from src.exceptions import (
    TeleClaudeError,
    AuthenticationError,
    SessionError,
    SandboxError,
    ClaudeError,
)


def test_base_exception():
    """TeleClaudeError is base for all custom exceptions."""
    with pytest.raises(TeleClaudeError):
        raise TeleClaudeError("test")


def test_authentication_error_inherits():
    """AuthenticationError inherits from TeleClaudeError."""
    err = AuthenticationError("unauthorized")
    assert isinstance(err, TeleClaudeError)
    assert str(err) == "unauthorized"


def test_session_error_inherits():
    """SessionError inherits from TeleClaudeError."""
    err = SessionError("session not found")
    assert isinstance(err, TeleClaudeError)


def test_sandbox_error_inherits():
    """SandboxError inherits from TeleClaudeError."""
    err = SandboxError("path not allowed")
    assert isinstance(err, TeleClaudeError)


def test_claude_error_inherits():
    """ClaudeError inherits from TeleClaudeError."""
    err = ClaudeError("SDK error")
    assert isinstance(err, TeleClaudeError)
