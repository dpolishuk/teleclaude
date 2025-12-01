"""Test Claude commands module."""
import pytest
from pathlib import Path
from src.commands.models import ClaudeCommand
from src.commands.discovery import parse_command_file, scan_commands


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


def test_scan_commands_empty_dirs(tmp_path, monkeypatch):
    """Returns empty list when no command dirs exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    commands = scan_commands(project_path=str(tmp_path / "nonexistent"))

    assert commands == []


def test_scan_commands_personal_only(tmp_path, monkeypatch):
    """Scans personal commands from ~/.claude/commands/."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    cmd_dir = home / ".claude" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "review.md").write_text("Review code.")
    (cmd_dir / "test.md").write_text("Run tests.")

    commands = scan_commands(project_path=None)

    assert len(commands) == 2
    names = {c.name for c in commands}
    assert names == {"review", "test"}
    assert all(c.source == "personal" for c in commands)


def test_scan_commands_project_overrides_personal(tmp_path, monkeypatch):
    """Project commands override personal commands with same name."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    # Personal command
    personal_dir = home / ".claude" / "commands"
    personal_dir.mkdir(parents=True)
    (personal_dir / "review.md").write_text("Personal review.")

    # Project command with same name
    project = tmp_path / "myproject"
    project_dir = project / ".claude" / "commands"
    project_dir.mkdir(parents=True)
    (project_dir / "review.md").write_text("Project review.")

    commands = scan_commands(project_path=str(project))

    assert len(commands) == 1
    assert commands[0].name == "review"
    assert commands[0].prompt == "Project review."
    assert commands[0].source == "project"


def test_scan_commands_merges_both(tmp_path, monkeypatch):
    """Merges personal and project commands."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    # Personal commands
    personal_dir = home / ".claude" / "commands"
    personal_dir.mkdir(parents=True)
    (personal_dir / "personal-cmd.md").write_text("Personal only.")

    # Project commands
    project = tmp_path / "myproject"
    project_dir = project / ".claude" / "commands"
    project_dir.mkdir(parents=True)
    (project_dir / "project-cmd.md").write_text("Project only.")

    commands = scan_commands(project_path=str(project))

    assert len(commands) == 2
    names = {c.name for c in commands}
    assert names == {"personal-cmd", "project-cmd"}


# Task 4: CommandRegistry tests
from src.commands.registry import CommandRegistry


def test_registry_get_command():
    """Registry returns command by name."""
    registry = CommandRegistry()
    cmd = ClaudeCommand(name="test", description="Test", prompt="Test prompt")
    registry._commands = {"test": cmd}

    result = registry.get("test")

    assert result == cmd


def test_registry_get_unknown_returns_none():
    """Registry returns None for unknown command."""
    registry = CommandRegistry()

    result = registry.get("unknown")

    assert result is None


def test_registry_substitute_args_simple():
    """Substitutes $ARGUMENTS in prompt."""
    registry = CommandRegistry()
    cmd = ClaudeCommand(
        name="fix",
        description="Fix bug",
        prompt="Fix this bug: $ARGUMENTS",
        needs_args=True,
    )

    result = registry.substitute_args(cmd, "login is broken")

    assert result == "Fix this bug: login is broken"


def test_registry_substitute_args_positional():
    """Substitutes $1, $2 in prompt."""
    registry = CommandRegistry()
    cmd = ClaudeCommand(
        name="rename",
        description="Rename",
        prompt="Rename $1 to $2",
        needs_args=True,
    )

    result = registry.substitute_args(cmd, "old_name new_name")

    assert result == "Rename old_name to new_name"


def test_registry_builtin_commands():
    """Registry provides list of built-in command names."""
    registry = CommandRegistry()

    builtins = registry.builtin_names

    assert "new" in builtins
    assert "help" in builtins
    assert "cancel" in builtins
