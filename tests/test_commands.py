"""Test Claude commands module."""
import pytest
from pathlib import Path
from src.commands.models import ClaudeCommand
from src.commands.discovery import parse_command_file


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


def test_parse_command_file_simple(tmp_path):
    """Parse command file without frontmatter."""
    cmd_file = tmp_path / "review.md"
    cmd_file.write_text("Review this code for bugs and improvements.")

    cmd = parse_command_file(cmd_file)

    assert cmd.name == "review"
    assert cmd.prompt == "Review this code for bugs and improvements."
    assert cmd.description == "Review this code for bugs and improvements."
    assert cmd.needs_args is False


def test_parse_command_file_with_frontmatter(tmp_path):
    """Parse command file with YAML frontmatter."""
    cmd_file = tmp_path / "fix-bug.md"
    cmd_file.write_text("""---
description: Fix a specific bug
allowed-tools: Bash(git:*), Read
---
Fix this bug: $ARGUMENTS
""")

    cmd = parse_command_file(cmd_file)

    assert cmd.name == "fix-bug"
    assert cmd.description == "Fix a specific bug"
    assert cmd.prompt == "Fix this bug: $ARGUMENTS"
    assert cmd.needs_args is True


def test_parse_command_file_with_positional_args(tmp_path):
    """Parse command file with $1, $2 placeholders."""
    cmd_file = tmp_path / "rename.md"
    cmd_file.write_text("Rename $1 to $2 in all files.")

    cmd = parse_command_file(cmd_file)

    assert cmd.needs_args is True


def test_parse_command_file_truncates_long_description(tmp_path):
    """Long descriptions are truncated to 256 chars."""
    cmd_file = tmp_path / "long.md"
    long_desc = "A" * 300
    cmd_file.write_text(f"""---
description: {long_desc}
---
Do something.
""")

    cmd = parse_command_file(cmd_file)

    assert len(cmd.description) <= 256
    assert cmd.description.endswith("...")
