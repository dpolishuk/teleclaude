"""Data models for Claude commands."""
from dataclasses import dataclass, field


@dataclass
class ClaudeCommand:
    """Represents a Claude slash command from .claude/commands/*.md."""

    name: str
    description: str
    prompt: str
    needs_args: bool = False
    source: str = "personal"
