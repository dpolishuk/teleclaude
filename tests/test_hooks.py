"""Test Claude hooks."""
import pytest
from src.claude.hooks import (
    is_dangerous_command,
    check_dangerous_command,
    create_approval_hooks,
    DANGEROUS_PATTERNS,
)


def test_is_dangerous_command_matches_rm_rf():
    """Detects rm -rf as dangerous."""
    assert is_dangerous_command("rm -rf /tmp/test") is True


def test_is_dangerous_command_safe():
    """Allows safe commands."""
    assert is_dangerous_command("ls -la") is False


def test_is_dangerous_command_case_insensitive():
    """Pattern matching is case insensitive."""
    assert is_dangerous_command("SUDO apt install") is True


def test_is_dangerous_command_custom_patterns():
    """Custom patterns override defaults."""
    assert is_dangerous_command("rm test.txt", patterns=["rm"]) is True
    assert is_dangerous_command("ls", patterns=["rm"]) is False


@pytest.mark.asyncio
async def test_check_dangerous_command_blocks_dangerous():
    """Hook returns ask decision for dangerous commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /important"},
    }

    result = await check_dangerous_command(input_data, "tool123", {})

    assert result["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert "rm -rf" in result["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.asyncio
async def test_check_dangerous_command_allows_safe():
    """Hook returns empty dict for safe commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
    }

    result = await check_dangerous_command(input_data, "tool123", {})

    assert result == {}


@pytest.mark.asyncio
async def test_check_dangerous_command_ignores_non_bash():
    """Hook ignores non-Bash tools."""
    input_data = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/etc/passwd"},
    }

    result = await check_dangerous_command(input_data, "tool123", {})

    assert result == {}


def test_create_approval_hooks_returns_hookmatcher_format():
    """create_approval_hooks returns SDK-compatible format."""
    hooks = create_approval_hooks()

    assert "PreToolUse" in hooks
    # Should be a list of HookMatcher objects
    assert isinstance(hooks["PreToolUse"], list)
