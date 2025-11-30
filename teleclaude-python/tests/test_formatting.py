"""Test formatting utilities."""
import pytest
from src.utils.formatting import (
    escape_markdown,
    format_tool_use,
    chunk_text,
    truncate_text,
)


def test_escape_markdown_special_chars():
    """escape_markdown escapes Telegram special characters."""
    text = "Hello *world* with _underscores_ and `code`"
    escaped = escape_markdown(text)

    assert "\\*" in escaped
    assert "\\_" in escaped
    assert "\\`" in escaped


def test_escape_markdown_brackets():
    """escape_markdown escapes brackets."""
    text = "Function(arg) and [link]"
    escaped = escape_markdown(text)

    assert "\\(" in escaped
    assert "\\)" in escaped
    assert "\\[" in escaped
    assert "\\]" in escaped


def test_format_tool_use_read():
    """format_tool_use formats Read tool."""
    result = format_tool_use("Read", {"file_path": "/home/user/file.txt"})
    assert "📁" in result
    assert "file.txt" in result


def test_format_tool_use_bash():
    """format_tool_use formats Bash tool."""
    result = format_tool_use("Bash", {"command": "ls -la"})
    assert "⚡" in result
    assert "ls -la" in result


def test_format_tool_use_bash_truncates():
    """format_tool_use truncates long commands."""
    long_cmd = "echo " + "a" * 100
    result = format_tool_use("Bash", {"command": long_cmd})
    assert len(result) < 100
    assert "..." in result


def test_format_tool_use_write():
    """format_tool_use formats Write tool."""
    result = format_tool_use("Write", {"file_path": "/home/user/new.py"})
    assert "📝" in result
    assert "new.py" in result


def test_format_tool_use_grep():
    """format_tool_use formats Grep tool."""
    result = format_tool_use("Grep", {"pattern": "TODO"})
    assert "🔍" in result
    assert "TODO" in result


def test_chunk_text_short():
    """chunk_text returns single chunk for short text."""
    text = "Short text"
    chunks = chunk_text(text, max_size=100)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_long():
    """chunk_text splits long text."""
    text = "a" * 1000
    chunks = chunk_text(text, max_size=300)

    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_chunk_text_preserves_content():
    """chunk_text preserves all content."""
    text = "Hello world! " * 100
    chunks = chunk_text(text, max_size=200)

    rejoined = "".join(chunks)
    assert rejoined == text


def test_truncate_text_short():
    """truncate_text returns short text unchanged."""
    text = "Short"
    result = truncate_text(text, max_len=100)
    assert result == text


def test_truncate_text_long():
    """truncate_text adds ellipsis to long text."""
    text = "a" * 100
    result = truncate_text(text, max_len=50)

    assert len(result) == 50
    assert result.endswith("...")
