"""Claude integration module."""
from .client import TeleClaudeClient, ClaudeOptions
from .hooks import (
    is_dangerous_command,
    check_dangerous_command,
    create_approval_hooks,
    DANGEROUS_PATTERNS,
)

__all__ = [
    "TeleClaudeClient",
    "ClaudeOptions",
    "is_dangerous_command",
    "check_dangerous_command",
    "create_approval_hooks",
    "DANGEROUS_PATTERNS",
]
