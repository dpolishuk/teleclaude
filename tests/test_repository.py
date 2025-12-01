"""Test database repository."""
import pytest
from src.storage.database import init_database, get_session
from src.storage.repository import SessionRepository, UsageRepository, AuditRepository
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


@pytest.mark.asyncio
async def test_record_usage(tmp_path):
    """UsageRepository records usage entry."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = UsageRepository(db)
        usage = await repo.record_usage(
            telegram_user_id=12345678,
            session_id="test-session-123",
            input_tokens=100,
            output_tokens=200,
            cost_usd=0.05,
        )

        assert usage.id is not None
        assert usage.telegram_user_id == 12345678
        assert usage.session_id == "test-session-123"
        assert usage.input_tokens == 100
        assert usage.output_tokens == 200
        assert usage.cost_usd == 0.05
        assert usage.timestamp is not None


@pytest.mark.asyncio
async def test_record_usage_without_session(tmp_path):
    """UsageRepository records usage entry without session."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = UsageRepository(db)
        usage = await repo.record_usage(
            telegram_user_id=12345678,
            session_id=None,
            input_tokens=50,
            output_tokens=75,
            cost_usd=0.03,
        )

        assert usage.id is not None
        assert usage.telegram_user_id == 12345678
        assert usage.session_id is None
        assert usage.input_tokens == 50
        assert usage.output_tokens == 75
        assert usage.cost_usd == 0.03


@pytest.mark.asyncio
async def test_get_total_cost(tmp_path):
    """UsageRepository calculates total cost for user."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = UsageRepository(db)

        # Record multiple usage entries
        await repo.record_usage(
            telegram_user_id=12345678,
            session_id="session-1",
            input_tokens=100,
            output_tokens=200,
            cost_usd=0.05,
        )
        await repo.record_usage(
            telegram_user_id=12345678,
            session_id="session-2",
            input_tokens=150,
            output_tokens=250,
            cost_usd=0.07,
        )
        await repo.record_usage(
            telegram_user_id=99999999,
            session_id="other-session",
            input_tokens=50,
            output_tokens=100,
            cost_usd=0.02,
        )

        total = await repo.get_total_cost(12345678)

        assert abs(total - 0.12) < 0.001


@pytest.mark.asyncio
async def test_get_total_cost_no_usage(tmp_path):
    """UsageRepository returns zero for user with no usage."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = UsageRepository(db)
        total = await repo.get_total_cost(12345678)

        assert total == 0.0


@pytest.mark.asyncio
async def test_audit_log(tmp_path):
    """AuditRepository creates audit log entry."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = AuditRepository(db)
        entry = await repo.log(
            telegram_user_id=12345678,
            action="session_created",
            session_id="test-session-123",
            details="Created new session for project: myapp",
        )

        assert entry.id is not None
        assert entry.telegram_user_id == 12345678
        assert entry.action == "session_created"
        assert entry.session_id == "test-session-123"
        assert entry.details == "Created new session for project: myapp"
        assert entry.timestamp is not None


@pytest.mark.asyncio
async def test_audit_log_minimal(tmp_path):
    """AuditRepository creates audit log with minimal data."""
    db_path = tmp_path / "test.db"
    await init_database(str(db_path))

    async with get_session() as db:
        repo = AuditRepository(db)
        entry = await repo.log(
            telegram_user_id=12345678,
            action="user_login",
        )

        assert entry.id is not None
        assert entry.telegram_user_id == 12345678
        assert entry.action == "user_login"
        assert entry.session_id is None
        assert entry.details is None
        assert entry.timestamp is not None
