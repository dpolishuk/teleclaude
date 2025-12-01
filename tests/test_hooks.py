"""Test Claude SDK hooks."""
import pytest
from src.claude.hooks import (
    is_dangerous_command,
    check_dangerous_command,
    create_approval_hooks,
    create_dangerous_command_hook,
    DANGEROUS_PATTERNS,
)


def test_dangerous_patterns_exist():
    """DANGEROUS_PATTERNS contains expected patterns."""
    assert "rm -rf" in DANGEROUS_PATTERNS
    assert "sudo" in DANGEROUS_PATTERNS
    assert "git push --force" in DANGEROUS_PATTERNS


def test_is_dangerous_command_matches():
    """is_dangerous_command detects dangerous patterns."""
    assert is_dangerous_command("rm -rf /") is True
    assert is_dangerous_command("sudo rm file") is True
    assert is_dangerous_command("git push --force origin main") is True


def test_is_dangerous_command_safe():
    """is_dangerous_command allows safe commands."""
    assert is_dangerous_command("ls -la") is False
    assert is_dangerous_command("echo hello") is False
    assert is_dangerous_command("git status") is False


def test_is_dangerous_command_case_insensitive():
    """is_dangerous_command is case insensitive."""
    assert is_dangerous_command("RM -RF /") is True
    assert is_dangerous_command("SUDO rm file") is True
    assert is_dangerous_command("Git Push --Force main") is True


def test_is_dangerous_command_custom_patterns():
    """is_dangerous_command works with custom patterns."""
    custom = ["drop table", "truncate"]
    assert is_dangerous_command("DROP TABLE users", custom) is True
    assert is_dangerous_command("truncate logs", custom) is True
    assert is_dangerous_command("select * from users", custom) is False


@pytest.mark.asyncio
async def test_check_dangerous_command_allows_safe():
    """check_dangerous_command allows safe commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
    }

    result = await check_dangerous_command(input_data, "tool123", {})

    assert result == {}


@pytest.mark.asyncio
async def test_check_dangerous_command_blocks_dangerous():
    """check_dangerous_command blocks dangerous commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /"},
    }

    result = await check_dangerous_command(input_data, "tool123", {})

    assert "hookSpecificOutput" in result
    assert result["hookSpecificOutput"]["permissionDecision"] == "ask"


@pytest.mark.asyncio
async def test_check_dangerous_command_ignores_non_bash():
    """check_dangerous_command ignores non-Bash tools."""
    input_data = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/etc/passwd"},
    }

    result = await check_dangerous_command(input_data, "tool123", {})

    assert result == {}


def test_create_approval_hooks_default():
    """create_approval_hooks returns correct structure with defaults."""
    hooks = create_approval_hooks()

    assert "PreToolUse" in hooks
    assert "Bash" in hooks["PreToolUse"]
    assert len(hooks["PreToolUse"]["Bash"]) == 1
    assert hooks["PreToolUse"]["Bash"][0] == check_dangerous_command


def test_create_approval_hooks_custom_patterns():
    """create_approval_hooks combines custom patterns with defaults."""
    custom = ["my-dangerous-cmd"]
    hooks = create_approval_hooks(custom)

    assert "PreToolUse" in hooks
    assert "Bash" in hooks["PreToolUse"]
    # Should have a custom hook, not the default
    assert hooks["PreToolUse"]["Bash"][0] != check_dangerous_command


@pytest.mark.asyncio
async def test_create_approval_hooks_custom_detects_custom_pattern():
    """Custom patterns are detected by the created hook."""
    custom = ["my-secret-cmd"]
    hooks = create_approval_hooks(custom)
    hook = hooks["PreToolUse"]["Bash"][0]

    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "my-secret-cmd --flag"},
    }

    result = await hook(input_data, "tool123", {})

    assert "hookSpecificOutput" in result
    assert result["hookSpecificOutput"]["permissionDecision"] == "ask"


@pytest.mark.asyncio
async def test_create_approval_hooks_custom_still_checks_defaults():
    """Custom hooks still check default dangerous patterns."""
    custom = ["my-secret-cmd"]
    hooks = create_approval_hooks(custom)
    hook = hooks["PreToolUse"]["Bash"][0]

    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "sudo rm -rf /"},
    }

    result = await hook(input_data, "tool123", {})

    assert "hookSpecificOutput" in result
    assert result["hookSpecificOutput"]["permissionDecision"] == "ask"


@pytest.mark.asyncio
async def test_create_dangerous_command_hook():
    """create_dangerous_command_hook creates working hook."""
    patterns = ["secret-op"]
    hook = create_dangerous_command_hook(patterns)

    # Should detect custom pattern
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "secret-op --run"},
    }
    result = await hook(input_data, "tool123", {})
    assert result["hookSpecificOutput"]["permissionDecision"] == "ask"

    # Should allow non-matching command
    input_data["tool_input"]["command"] = "ls -la"
    result = await hook(input_data, "tool123", {})
    assert result == {}
