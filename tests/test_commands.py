"""Test Claude commands module."""
import pytest
from src.commands.models import ClaudeCommand


def test_claude_command_creation():
    """ClaudeCommand can be created with all fields."""
    cmd = ClaudeCommand(
        name="fix-bug",
        description="Fix a bug in the code",
        prompt="Fix this bug: $ARGUMENTS",
        needs_args=True,
        source="project",
    )
    assert cmd.name == "fix-bug"
    assert cmd.description == "Fix a bug in the code"
    assert cmd.prompt == "Fix this bug: $ARGUMENTS"
    assert cmd.needs_args is True
    assert cmd.source == "project"


def test_claude_command_defaults():
    """ClaudeCommand has sensible defaults."""
    cmd = ClaudeCommand(
        name="review",
        description="Review code",
        prompt="Review this code",
    )
    assert cmd.needs_args is False
    assert cmd.source == "personal"
