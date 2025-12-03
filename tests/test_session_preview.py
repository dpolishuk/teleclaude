"""Test session preview functionality."""
import pytest
import json
from pathlib import Path


def test_get_session_last_message(tmp_path):
    """get_session_last_message returns last user message."""
    from src.claude.sessions import get_session_last_message

    # Create mock session file
    session_dir = tmp_path / ".claude" / "projects" / "test-project" / "sessions"
    session_dir.mkdir(parents=True)

    session_file = session_dir / "abc123.jsonl"
    messages = [
        {"type": "human", "message": {"content": "First message"}},
        {"type": "assistant", "message": {"content": "Response"}},
        {"type": "human", "message": {"content": "Last user message here"}},
    ]
    session_file.write_text("\n".join(json.dumps(m) for m in messages))

    result = get_session_last_message(str(session_file))

    assert result == "Last user message here"


def test_get_session_last_message_truncates(tmp_path):
    """Long messages are truncated."""
    from src.claude.sessions import get_session_last_message

    session_dir = tmp_path / ".claude" / "projects" / "test-project" / "sessions"
    session_dir.mkdir(parents=True)

    session_file = session_dir / "abc123.jsonl"
    long_message = "x" * 200
    messages = [{"type": "human", "message": {"content": long_message}}]
    session_file.write_text(json.dumps(messages[0]))

    result = get_session_last_message(str(session_file), max_length=50)

    assert len(result) <= 53  # 50 + "..."
    assert result.endswith("...")


def test_get_session_last_message_missing_file():
    """Missing file returns None."""
    from src.claude.sessions import get_session_last_message

    result = get_session_last_message("/nonexistent/path.jsonl")

    assert result is None
