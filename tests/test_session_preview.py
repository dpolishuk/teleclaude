"""Test session preview functionality."""
import json


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


def test_get_session_file_path(tmp_path):
    """get_session_file_path finds session file by Claude session ID."""
    from pathlib import Path
    from src.claude.sessions import get_session_file_path, encode_project_path

    # Create mock Claude directory structure
    project_path = str(tmp_path / "myproject")
    encoded = encode_project_path(project_path)

    sessions_dir = Path.home() / ".claude" / "projects" / encoded / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Create session file
    session_file = sessions_dir / "abc-123-def.jsonl"
    session_file.write_text('{"type": "human", "message": {"content": "test"}}')

    result = get_session_file_path(project_path, "abc-123-def")

    assert result is not None
    assert result.endswith("abc-123-def.jsonl")


def test_get_session_file_path_not_found(tmp_path):
    """get_session_file_path returns None for missing session."""
    from src.claude.sessions import get_session_file_path

    result = get_session_file_path("/nonexistent", "no-such-session")

    assert result is None
