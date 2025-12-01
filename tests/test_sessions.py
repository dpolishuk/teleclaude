"""Test Claude Code session scanner module."""
import pytest
import json
from pathlib import Path
from datetime import datetime
from src.claude.sessions import (
    Project,
    SessionInfo,
    scan_projects,
    scan_sessions,
    parse_session_preview,
)


@pytest.fixture
def mock_claude_dir(tmp_path):
    """Create a mock ~/.claude/projects directory structure."""
    # tmp_path will act as the home directory
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Create project 1: teleclaude
    project1 = projects_dir / "-root-work-teleclaude"
    project1.mkdir()

    # Create session files with different mtimes
    session1 = project1 / "session1.jsonl"
    session1.write_text(
        '{"type":"user","message":{"role":"user","content":"fix permission buttons"}}\n'
        '{"type":"assistant","message":{"role":"assistant","content":"I\'ll help fix that"}}\n'
    )

    session2 = project1 / "session2.jsonl"
    session2.write_text(
        '{"type":"user","message":{"role":"user","content":"implement MCP support for the bot"}}\n'
    )

    session3 = project1 / "session3.jsonl"
    session3.write_text(
        '{"type":"user","message":{"role":"user","content":"add session storage with SQLite"}}\n'
    )

    # Create project 2: another project
    project2 = projects_dir / "-home-user-myapp"
    project2.mkdir()

    session4 = project2 / "session4.jsonl"
    session4.write_text(
        '{"type":"user","message":{"role":"user","content":"initial setup"}}\n'
    )

    # Create empty project (no sessions)
    project3 = projects_dir / "-tmp-test"
    project3.mkdir()

    # Return tmp_path, which acts as the home directory
    return tmp_path


def test_project_dataclass():
    """Project dataclass has correct fields."""
    project = Project(
        name="-root-work-teleclaude",
        display_name="/root/work/teleclaude",
        path=Path("/home/user/.claude/projects/-root-work-teleclaude")
    )

    assert project.name == "-root-work-teleclaude"
    assert project.display_name == "/root/work/teleclaude"
    assert isinstance(project.path, Path)


def test_session_info_dataclass():
    """SessionInfo dataclass has correct fields."""
    now = datetime.now()
    session = SessionInfo(
        session_id="session1",
        path=Path("/home/user/.claude/projects/proj/session1.jsonl"),
        mtime=now,
        preview="fix permission buttons"
    )

    assert session.session_id == "session1"
    assert isinstance(session.path, Path)
    assert session.mtime == now
    assert session.preview == "fix permission buttons"


def test_scan_projects_finds_all_projects(mock_claude_dir, monkeypatch):
    """scan_projects returns all projects in ~/.claude/projects/."""
    import src.claude.sessions
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: mock_claude_dir)

    projects = scan_projects()

    assert len(projects) == 3
    project_names = [p.name for p in projects]
    assert "-root-work-teleclaude" in project_names
    assert "-home-user-myapp" in project_names
    assert "-tmp-test" in project_names


def test_scan_projects_decodes_project_names(mock_claude_dir, monkeypatch):
    """scan_projects decodes project names to display names."""
    import src.claude.sessions
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: mock_claude_dir)

    projects = scan_projects()
    project_dict = {p.name: p.display_name for p in projects}

    assert project_dict["-root-work-teleclaude"] == "/root/work/teleclaude"
    assert project_dict["-home-user-myapp"] == "/home/user/myapp"
    assert project_dict["-tmp-test"] == "/tmp/test"


def test_scan_projects_returns_empty_when_no_projects(tmp_path, monkeypatch):
    """scan_projects returns empty list when no projects exist."""
    import src.claude.sessions
    empty_dir = tmp_path / ".claude" / "projects"
    empty_dir.mkdir(parents=True)
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: tmp_path)

    projects = scan_projects()

    assert projects == []


def test_scan_projects_handles_missing_directory(tmp_path, monkeypatch):
    """scan_projects returns empty list when directory doesn't exist."""
    import src.claude.sessions
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: tmp_path)

    projects = scan_projects()

    assert projects == []


def test_scan_sessions_returns_sessions_for_project(mock_claude_dir, monkeypatch):
    """scan_sessions returns all sessions for a given project."""
    import src.claude.sessions
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: mock_claude_dir)

    sessions = scan_sessions("-root-work-teleclaude")

    assert len(sessions) == 3
    session_ids = [s.session_id for s in sessions]
    assert "session1" in session_ids
    assert "session2" in session_ids
    assert "session3" in session_ids


def test_scan_sessions_sorted_by_mtime_desc(mock_claude_dir, monkeypatch):
    """scan_sessions returns sessions sorted by modification time, newest first."""
    import src.claude.sessions
    import time
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: mock_claude_dir)

    # Touch files in specific order to set mtimes
    project_path = mock_claude_dir / ".claude" / "projects" / "-root-work-teleclaude"

    (project_path / "session1.jsonl").touch()
    time.sleep(0.01)
    (project_path / "session2.jsonl").touch()
    time.sleep(0.01)
    (project_path / "session3.jsonl").touch()

    sessions = scan_sessions("-root-work-teleclaude")

    # Should be sorted newest first
    assert sessions[0].session_id == "session3"
    assert sessions[1].session_id == "session2"
    assert sessions[2].session_id == "session1"

    # Verify mtimes are descending
    assert sessions[0].mtime >= sessions[1].mtime >= sessions[2].mtime


def test_scan_sessions_limits_to_5_most_recent(mock_claude_dir, monkeypatch):
    """scan_sessions returns only 5 most recent sessions."""
    import src.claude.sessions
    import time
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: mock_claude_dir)

    # Fixture already creates session1, session2, session3
    # Create 4 more sessions to have 7 total
    project_path = mock_claude_dir / ".claude" / "projects" / "-root-work-teleclaude"

    for i in range(4, 8):
        session = project_path / f"session{i}.jsonl"
        session.write_text(
            f'{{"type":"user","message":{{"role":"user","content":"test {i}"}}}}\n'
        )
        time.sleep(0.01)

    sessions = scan_sessions("-root-work-teleclaude")

    # Should return only 5 most recent (by mtime)
    assert len(sessions) == 5
    session_ids = [s.session_id for s in sessions]

    # The 4 newly created ones should definitely be in the list
    assert "session7" in session_ids
    assert "session6" in session_ids
    assert "session5" in session_ids
    assert "session4" in session_ids

    # And at least one from the fixture should NOT be in the list
    # since we're limiting to 5 out of 7 total
    all_old_sessions_present = all(s in session_ids for s in ["session1", "session2", "session3"])
    assert not all_old_sessions_present


def test_scan_sessions_returns_empty_for_nonexistent_project(mock_claude_dir, monkeypatch):
    """scan_sessions returns empty list for nonexistent project."""
    import src.claude.sessions
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: mock_claude_dir)

    sessions = scan_sessions("-nonexistent-project")

    assert sessions == []


def test_scan_sessions_returns_empty_for_project_with_no_sessions(mock_claude_dir, monkeypatch):
    """scan_sessions returns empty list for project with no sessions."""
    import src.claude.sessions
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: mock_claude_dir)

    sessions = scan_sessions("-tmp-test")

    assert sessions == []


def test_parse_session_preview_extracts_first_user_message(tmp_path):
    """parse_session_preview extracts the first user message content."""
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(
        '{"type":"user","message":{"role":"user","content":"This is the first message"}}\n'
        '{"type":"assistant","message":{"role":"assistant","content":"Response"}}\n'
        '{"type":"user","message":{"role":"user","content":"Second message"}}\n'
    )

    preview = parse_session_preview(session_file)

    assert preview == "This is the first message"


def test_parse_session_preview_skips_non_user_messages(tmp_path):
    """parse_session_preview skips non-user message types."""
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(
        '{"type":"system","message":{"role":"system","content":"System message"}}\n'
        '{"type":"assistant","message":{"role":"assistant","content":"Assistant first"}}\n'
        '{"type":"user","message":{"role":"user","content":"User message here"}}\n'
    )

    preview = parse_session_preview(session_file)

    assert preview == "User message here"


def test_parse_session_preview_truncates_long_messages(tmp_path):
    """parse_session_preview truncates messages longer than 100 chars."""
    long_message = "A" * 150
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(
        f'{{"type":"user","message":{{"role":"user","content":"{long_message}"}}}}\n'
    )

    preview = parse_session_preview(session_file)

    assert len(preview) == 103  # 100 chars + "..."
    assert preview.endswith("...")
    assert preview.startswith("A" * 100)


def test_parse_session_preview_handles_empty_file(tmp_path):
    """parse_session_preview returns empty string for empty file."""
    session_file = tmp_path / "session.jsonl"
    session_file.write_text("")

    preview = parse_session_preview(session_file)

    assert preview == ""


def test_parse_session_preview_handles_malformed_json(tmp_path):
    """parse_session_preview handles malformed JSON gracefully."""
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(
        'not valid json\n'
        '{"type":"user","message":{"role":"user","content":"Valid message"}}\n'
    )

    preview = parse_session_preview(session_file)

    # Should skip malformed line and find the valid message
    assert preview == "Valid message"


def test_parse_session_preview_handles_missing_fields(tmp_path):
    """parse_session_preview handles missing fields in JSON."""
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(
        '{"type":"user"}\n'  # Missing message field
        '{"type":"user","message":{"role":"user"}}\n'  # Missing content
        '{"type":"user","message":{"role":"user","content":"Good message"}}\n'
    )

    preview = parse_session_preview(session_file)

    assert preview == "Good message"


def test_scan_sessions_includes_previews(mock_claude_dir, monkeypatch):
    """scan_sessions includes preview text for each session."""
    import src.claude.sessions
    monkeypatch.setattr(src.claude.sessions.Path, "home", lambda: mock_claude_dir)

    sessions = scan_sessions("-root-work-teleclaude")

    previews = [s.preview for s in sessions]
    assert "fix permission buttons" in previews
    assert "implement MCP support for the bot" in previews
    assert "add session storage with SQLite" in previews
