"""Test unified session model."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.storage.models import Session


def test_session_uses_uuid_primary_key():
    """Session model uses claude_session_id as primary key."""
    session = Session(
        id="550e8400-e29b-41d4-a716-446655440000",
        telegram_user_id=12345,
        project_path="/root/work/myproject",
    )
    # id should be the claude session UUID, not a hex token
    assert "-" in session.id  # UUIDs contain dashes
    assert len(session.id) == 36  # UUID length


def test_session_no_redundant_fields():
    """Session model removed redundant fields."""
    session = Session(
        id="550e8400-e29b-41d4-a716-446655440000",
        telegram_user_id=12345,
        project_path="/root/work/myproject",
    )
    # These fields should not exist
    assert not hasattr(session, "claude_session_id")
    assert not hasattr(session, "project_name")
    assert not hasattr(session, "current_directory")
    assert not hasattr(session, "status")


@pytest.mark.asyncio
async def test_repository_get_or_create_session():
    """Repository can get existing or create new session by claude_session_id."""
    from src.storage.repository import SessionRepository

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Simulate no existing session
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    repo = SessionRepository(mock_db)

    session = await repo.get_or_create_session(
        session_id="550e8400-e29b-41d4-a716-446655440000",
        telegram_user_id=12345,
        project_path="/root/work/myproject",
    )

    assert session.id == "550e8400-e29b-41d4-a716-446655440000"
    assert session.telegram_user_id == 12345
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_repository_list_sessions_for_project():
    """Repository lists sessions for a specific project path."""
    from src.storage.repository import SessionRepository

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    repo = SessionRepository(mock_db)

    # Method should exist and accept project_path
    assert hasattr(repo, "list_sessions_for_project")


@pytest.mark.asyncio
async def test_repository_get_session_ids_for_project():
    """Repository returns set of session IDs for a project."""
    from src.storage.repository import SessionRepository

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    # Simulate returning session IDs
    mock_result = MagicMock()
    mock_result.all.return_value = [("id1",), ("id2",), ("id3",)]
    mock_db.execute.return_value = mock_result

    repo = SessionRepository(mock_db)

    session_ids = await repo.get_session_ids_for_project(
        telegram_user_id=12345,
        project_path="/root/work/myproject",
    )

    assert session_ids == {"id1", "id2", "id3"}


@pytest.mark.asyncio
async def test_repository_get_active_session_for_user():
    """Repository renamed get_active_session to get_active_session_for_user."""
    from src.storage.repository import SessionRepository

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    repo = SessionRepository(mock_db)

    # Method should exist with new name
    assert hasattr(repo, "get_active_session_for_user")
    # Old method should not exist
    assert not hasattr(repo, "get_active_session")


@pytest.mark.asyncio
async def test_deprecated_methods_removed():
    """Repository removed deprecated methods."""
    from src.storage.repository import SessionRepository

    mock_db = MagicMock()
    repo = SessionRepository(mock_db)

    # These methods should not exist
    assert not hasattr(repo, "set_claude_session_id")
    assert not hasattr(repo, "_mark_existing_idle")
    assert not hasattr(repo, "mark_idle")
    assert not hasattr(repo, "mark_active")


def test_unified_session_info_has_origin():
    """UnifiedSessionInfo includes origin field."""
    from src.claude.sessions import UnifiedSessionInfo
    from datetime import datetime
    from pathlib import Path

    session = UnifiedSessionInfo(
        session_id="550e8400-e29b-41d4-a716-446655440000",
        path=Path("/tmp/session.jsonl"),
        mtime=datetime.now(),
        preview="test message",
        origin="telegram",
    )
    assert session.origin in ("telegram", "terminal")


def test_scan_unified_sessions_with_origin():
    """scan_unified_sessions marks sessions with correct origin."""
    from src.claude.sessions import scan_unified_sessions
    from pathlib import Path
    import tempfile
    import json
    import time

    # Create temporary project directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock ~/.claude/projects/
        projects_dir = Path(tmpdir) / ".claude" / "projects"
        project_dir = projects_dir / "-tmp-testproject"
        project_dir.mkdir(parents=True)

        # Create two session files
        session1_id = "telegram-session-123"
        session2_id = "terminal-session-456"

        session1_file = project_dir / f"{session1_id}.jsonl"
        session2_file = project_dir / f"{session2_id}.jsonl"

        # Write sample session data
        session_data = {
            "type": "user",
            "message": {"content": "Hello from test"}
        }

        with open(session1_file, "w") as f:
            json.dump(session_data, f)

        time.sleep(0.01)  # Ensure different mtime

        with open(session2_file, "w") as f:
            json.dump(session_data, f)

        # Mock Path.home() to use our temp directory
        original_home = Path.home
        Path.home = lambda: Path(tmpdir)

        try:
            # Scan with telegram session owned
            owned_ids = {session1_id}
            sessions = scan_unified_sessions(
                project_path="/tmp/testproject",
                owned_session_ids=owned_ids,
                limit=10
            )

            # Should return both sessions
            assert len(sessions) == 2

            # Find each session
            tg_session = next((s for s in sessions if s.session_id == session1_id), None)
            term_session = next((s for s in sessions if s.session_id == session2_id), None)

            assert tg_session is not None
            assert term_session is not None

            # Check origins
            assert tg_session.origin == "telegram"
            assert term_session.origin == "terminal"

            # Check they are sorted by mtime (newest first)
            assert sessions[0].session_id == session2_id  # Written last

        finally:
            # Restore original Path.home
            Path.home = original_home


def test_unified_sessions_keyboard_shows_origin_icons():
    """Unified sessions keyboard shows origin icons."""
    from datetime import datetime
    from pathlib import Path
    from src.claude.sessions import UnifiedSessionInfo
    from src.bot.keyboards import build_unified_sessions_keyboard

    sessions = [
        UnifiedSessionInfo(
            session_id="abc123",
            path=Path("/tmp/abc123.jsonl"),
            mtime=datetime.now(),
            preview="telegram session",
            origin="telegram",
        ),
        UnifiedSessionInfo(
            session_id="def456",
            path=Path("/tmp/def456.jsonl"),
            mtime=datetime.now(),
            preview="terminal session",
            origin="terminal",
        ),
    ]

    keyboard = build_unified_sessions_keyboard(sessions)
    buttons = keyboard.inline_keyboard

    # First button should have telegram icon
    assert "\U0001F4F1" in buttons[0][0].text  # 📱
    # Second button should have terminal icon
    assert "\U0001F4BB" in buttons[1][0].text  # 💻


@pytest.mark.asyncio
async def test_list_sessions_shows_unified_view():
    """list_sessions handler shows unified sessions from filesystem + SQLite."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.bot.handlers import list_sessions

    update = MagicMock()
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.effective_user.id = 12345

    # Mock current session
    mock_session = MagicMock()
    mock_session.project_path = "/root/work/myproject"

    context = MagicMock()
    context.user_data = {"current_session": mock_session}

    # Mock the unified session scanning
    with patch("src.bot.handlers.scan_unified_sessions") as mock_scan, \
         patch("src.bot.handlers.get_session") as mock_get_session, \
         patch("src.bot.handlers.SessionRepository") as MockRepo:

        mock_repo = MagicMock()
        mock_repo.get_session_ids_for_project = AsyncMock(return_value={"abc123"})
        MockRepo.return_value = mock_repo

        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_scan.return_value = []  # No sessions

        await list_sessions(update, context)

    # Should have been called with project path
    update.message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_select_session_creates_record_for_terminal():
    """Selecting terminal session creates SQLite record (claim ownership)."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.bot.callbacks import _handle_select_session

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.effective_user.id = 12345

    mock_session = MagicMock()
    mock_session.project_path = "/root/work/myproject"

    context = MagicMock()
    context.user_data = {"current_session": mock_session}

    mock_repo = MagicMock()
    mock_repo.get_or_create_session = AsyncMock()

    with patch("src.bot.callbacks.get_session") as mock_get_session, \
         patch("src.bot.callbacks.SessionRepository", return_value=mock_repo):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await _handle_select_session(update, context, "terminal-session-id")

    # Should create session record
    mock_repo.get_or_create_session.assert_called_once_with(
        session_id="terminal-session-id",
        telegram_user_id=12345,
        project_path="/root/work/myproject",
    )


@pytest.mark.asyncio
async def test_result_message_creates_session_lazily():
    """ResultMessage with session_id creates SQLite record lazily."""
    from unittest.mock import AsyncMock, MagicMock

    # This tests the handler portion that processes ResultMessage
    # The key change is using get_or_create_session instead of set_claude_session_id

    from src.storage.repository import SessionRepository

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Simulate no existing session
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    repo = SessionRepository(mock_db)

    # This should create a new session
    session = await repo.get_or_create_session(
        session_id="new-uuid-from-sdk",
        telegram_user_id=12345,
        project_path="/root/work/myproject",
    )

    # Verify session was added
    mock_db.add.assert_called_once()
    assert session.id == "new-uuid-from-sdk"
