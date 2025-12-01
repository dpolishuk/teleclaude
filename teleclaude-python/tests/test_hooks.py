"""Test Claude SDK hooks."""
import pytest
from src.claude.hooks import (
    is_dangerous_command,
    check_dangerous_command,
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
