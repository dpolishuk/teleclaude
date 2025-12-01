"""Claude integration module."""
from .client import TeleClaudeClient, create_claude_options
from .hooks import (
    is_dangerous_command,
    check_dangerous_command,
    create_approval_hooks,
    create_dangerous_command_hook,
    DANGEROUS_PATTERNS,
)

__all__ = [
    "TeleClaudeClient",
    "create_claude_options",
    "is_dangerous_command",
    "check_dangerous_command",
    "create_approval_hooks",
    "create_dangerous_command_hook",
    "DANGEROUS_PATTERNS",
]
