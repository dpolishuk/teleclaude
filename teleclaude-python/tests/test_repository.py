"""Test database repository."""
import pytest
from src.storage.database import init_database, get_session
from src.storage.repository import SessionRepository
from src.storage.models import SessionStatus


@pytest.fixture
async def db_session(tmp_path):
    """Create a test database session."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))
    async with get_session() as session:
        yield session


@pytest.fixture
def repo(db_session):
    """Create a repository with test session."""
    return SessionRepository(db_session)


@pytest.mark.asyncio
async def test_create_session(tmp_path):
    """Repository creates session."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = SessionRepository(db)
        session = await repo.create_session(
            telegram_user_id=12345678,
            project_path="/home/user/myapp",
            project_name="myapp",
        )

        assert session.id is not None
        assert session.telegram_user_id == 12345678
        assert session.project_path == "/home/user/myapp"
        assert session.status == SessionStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_session_by_id(tmp_path):
    """Repository retrieves session by ID."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = SessionRepository(db)
        created = await repo.create_session(
            telegram_user_id=12345678,
            project_path="/home/user/myapp",
        )

        retrieved = await repo.get_session(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id


@pytest.mark.asyncio
async def test_get_active_session(tmp_path):
    """Repository retrieves active session for user."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = SessionRepository(db)
        await repo.create_session(
            telegram_user_id=12345678,
            project_path="/home/user/myapp",
        )

        active = await repo.get_active_session(12345678)

        assert active is not None
        assert active.telegram_user_id == 12345678
        assert active.status == SessionStatus.ACTIVE


@pytest.mark.asyncio
async def test_list_sessions_by_user(tmp_path):
    """Repository lists all sessions for user."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = SessionRepository(db)
        await repo.create_session(telegram_user_id=12345678, project_path="/path1")
        await repo.create_session(telegram_user_id=12345678, project_path="/path2")
        await repo.create_session(telegram_user_id=99999999, project_path="/other")

        sessions = await repo.list_sessions(12345678)

        assert len(sessions) == 2


@pytest.mark.asyncio
async def test_update_session_cost(tmp_path):
    """Repository updates session cost."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = SessionRepository(db)
        session = await repo.create_session(
            telegram_user_id=12345678,
            project_path="/home/user/myapp",
        )

        await repo.add_cost(session.id, 0.05)
        updated = await repo.get_session(session.id)

        assert updated.total_cost_usd == 0.05
