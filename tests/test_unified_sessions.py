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
