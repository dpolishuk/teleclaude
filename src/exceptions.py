"""Custom exceptions for TeleClaude."""


class TeleClaudeError(Exception):
    """Base exception for TeleClaude."""

    pass


class AuthenticationError(TeleClaudeError):
    """User not authorized."""

    pass


class SessionError(TeleClaudeError):
    """Session-related error."""

    pass


class SandboxError(TeleClaudeError):
    """Sandbox violation or error."""

    pass


class ClaudeError(TeleClaudeError):
    """Claude SDK error."""

    pass
