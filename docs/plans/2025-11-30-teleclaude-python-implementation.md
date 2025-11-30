# TeleClaude Python Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite TeleClaude in Python using the Claude Agent SDK, creating a successor to RichardAtCT/claude-code-telegram.

**Architecture:** Python 3.10+ application using claude-agent-sdk for Claude integration, python-telegram-bot for Telegram, SQLAlchemy + SQLite for storage, Poetry for packaging.

**Tech Stack:** Python 3.10+, claude-agent-sdk, python-telegram-bot v21+, SQLAlchemy 2.0, aiosqlite, PyYAML, python-dotenv

---

## Task 1: Project Scaffolding

**Files:**
- Create: `teleclaude-python/pyproject.toml`
- Create: `teleclaude-python/src/__init__.py`
- Create: `teleclaude-python/src/main.py`
- Create: `teleclaude-python/config.example.yaml`
- Create: `teleclaude-python/.env.example`

**Step 1: Create project directory**

Run:
```bash
mkdir -p teleclaude-python/src teleclaude-python/tests
cd teleclaude-python
```

**Step 2: Create pyproject.toml**

Create `teleclaude-python/pyproject.toml`:

```toml
[tool.poetry]
name = "teleclaude"
version = "0.1.0"
description = "Telegram bot for Claude Code access"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "src"}]

[tool.poetry.dependencies]
python = "^3.10"
claude-agent-sdk = "^0.1"
python-telegram-bot = {extras = ["job-queue"], version = "^21.0"}
sqlalchemy = "^2.0"
aiosqlite = "^0.19"
pyyaml = "^6.0"
python-dotenv = "^1.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
ruff = "^0.4"
mypy = "^1.10"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py310"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**Step 3: Create minimal main.py**

Create `teleclaude-python/src/__init__.py`:

```python
"""TeleClaude - Telegram bot for Claude Code access."""
```

Create `teleclaude-python/src/main.py`:

```python
"""TeleClaude entry point."""
import asyncio
import logging
import os

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable required")
        return

    logger.info("TeleClaude starting...")
    logger.info("Token found, bot ready to initialize")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Create example config files**

Create `teleclaude-python/config.example.yaml`:

```yaml
# TeleClaude Configuration
# Copy to ~/.teleclaude/config.yaml and customize

# Authentication - Telegram user IDs allowed
allowed_users:
  - 12345678  # Replace with your Telegram user ID

# Registered projects
projects:
  # myapp: /home/user/projects/myapp

# Directory sandbox - allowed base paths
sandbox:
  allowed_paths:
    - /home/user/projects

# Claude settings
claude:
  max_turns: 50
  permission_mode: "acceptEdits"
  max_budget_usd: 10.0

# Approval rules
approval:
  dangerous_commands:
    - "rm -rf"
    - "git push --force"
    - "sudo"
  require_approval_for:
    - "Bash"

# Streaming behavior
streaming:
  edit_throttle_ms: 1000
  chunk_size: 3800

# Database
database:
  path: ~/.teleclaude/teleclaude.db
```

Create `teleclaude-python/.env.example`:

```bash
# TeleClaude Environment Variables
TELEGRAM_BOT_TOKEN=your_bot_token_here
# Optional: override Claude CLI path
# CLAUDE_CLI_PATH=/usr/local/bin/claude
```

**Step 5: Install dependencies**

Run:
```bash
cd teleclaude-python
poetry install
```

**Step 6: Verify**

Run:
```bash
poetry run python -c "import src.main; print('OK')"
```

Expected: `OK`

**Step 7: Commit**

```bash
git add teleclaude-python/
git commit -m "feat(python): project scaffolding with Poetry"
```

---

## Task 2: Exceptions Module

**Files:**
- Create: `teleclaude-python/src/exceptions.py`
- Create: `teleclaude-python/tests/test_exceptions.py`

**Step 1: Write test**

Create `teleclaude-python/tests/__init__.py`:

```python
"""TeleClaude tests."""
```

Create `teleclaude-python/tests/test_exceptions.py`:

```python
"""Test custom exceptions."""
import pytest
from src.exceptions import (
    TeleClaudeError,
    AuthenticationError,
    SessionError,
    SandboxError,
    ClaudeError,
)


def test_base_exception():
    """TeleClaudeError is base for all custom exceptions."""
    with pytest.raises(TeleClaudeError):
        raise TeleClaudeError("test")


def test_authentication_error_inherits():
    """AuthenticationError inherits from TeleClaudeError."""
    err = AuthenticationError("unauthorized")
    assert isinstance(err, TeleClaudeError)
    assert str(err) == "unauthorized"


def test_session_error_inherits():
    """SessionError inherits from TeleClaudeError."""
    err = SessionError("session not found")
    assert isinstance(err, TeleClaudeError)


def test_sandbox_error_inherits():
    """SandboxError inherits from TeleClaudeError."""
    err = SandboxError("path not allowed")
    assert isinstance(err, TeleClaudeError)


def test_claude_error_inherits():
    """ClaudeError inherits from TeleClaudeError."""
    err = ClaudeError("SDK error")
    assert isinstance(err, TeleClaudeError)
```

**Step 2: Run test (should fail)**

```bash
cd teleclaude-python
poetry run pytest tests/test_exceptions.py -v
```

Expected: FAIL - module not found

**Step 3: Implement exceptions**

Create `teleclaude-python/src/exceptions.py`:

```python
"""Custom exceptions for TeleClaude."""


class TeleClaudeError(Exception):
    """Base exception for TeleClaude."""

    pass


class AuthenticationError(TeleClaudeError):
    """User not authorized."""

    pass


class SessionError(TeleClaudeError):
    """Session-related error."""

    pass


class SandboxError(TeleClaudeError):
    """Directory access violation."""

    pass


class ClaudeError(TeleClaudeError):
    """Claude SDK error."""

    pass
```

**Step 4: Run test (should pass)**

```bash
poetry run pytest tests/test_exceptions.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add teleclaude-python/src/exceptions.py teleclaude-python/tests/
git commit -m "feat(python): add custom exceptions"
```

---

## Task 3: Configuration Module

**Files:**
- Create: `teleclaude-python/src/config/__init__.py`
- Create: `teleclaude-python/src/config/settings.py`
- Create: `teleclaude-python/tests/test_config.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_config.py`:

```python
"""Test configuration loading."""
import os
import pytest
from pathlib import Path
from src.config.settings import Config, load_config


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config file."""
    config_content = """
allowed_users:
  - 12345678
  - 87654321

projects:
  myapp: /home/user/myapp

sandbox:
  allowed_paths:
    - /home/user

claude:
  max_turns: 25
  permission_mode: "acceptEdits"
  max_budget_usd: 5.0

approval:
  dangerous_commands:
    - "rm -rf"
  require_approval_for:
    - "Bash"

streaming:
  edit_throttle_ms: 500
  chunk_size: 4000

database:
  path: /tmp/test.db
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    return config_path


def test_load_config(config_file):
    """Config loads from YAML file."""
    config = load_config(config_file)

    assert len(config.allowed_users) == 2
    assert 12345678 in config.allowed_users
    assert config.projects["myapp"] == "/home/user/myapp"
    assert config.claude.max_turns == 25
    assert config.claude.max_budget_usd == 5.0
    assert config.streaming.chunk_size == 4000


def test_load_config_defaults(tmp_path):
    """Config applies defaults for missing values."""
    config_content = """
allowed_users:
  - 12345678
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)

    config = load_config(config_path)

    assert config.claude.max_turns == 50
    assert config.claude.permission_mode == "acceptEdits"
    assert config.streaming.edit_throttle_ms == 1000
    assert config.streaming.chunk_size == 3800


def test_is_user_allowed():
    """is_user_allowed checks whitelist."""
    config = Config(allowed_users=[12345678, 87654321])

    assert config.is_user_allowed(12345678) is True
    assert config.is_user_allowed(99999999) is False


def test_config_expands_home_path(tmp_path):
    """Database path expands ~ to home directory."""
    config_content = """
allowed_users:
  - 12345678

database:
  path: ~/.teleclaude/test.db
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)

    config = load_config(config_path)

    assert "~" not in config.database.path
    assert config.database.path.startswith(str(Path.home()))
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_config.py -v
```

Expected: FAIL - module not found

**Step 3: Implement config module**

Create `teleclaude-python/src/config/__init__.py`:

```python
"""Configuration module."""
from .settings import Config, load_config

__all__ = ["Config", "load_config"]
```

Create `teleclaude-python/src/config/settings.py`:

```python
"""Configuration settings."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ClaudeConfig:
    """Claude SDK settings."""

    max_turns: int = 50
    permission_mode: str = "acceptEdits"
    max_budget_usd: float = 10.0


@dataclass
class ApprovalConfig:
    """Approval workflow settings."""

    dangerous_commands: list[str] = field(default_factory=lambda: ["rm -rf", "sudo"])
    require_approval_for: list[str] = field(default_factory=lambda: ["Bash"])


@dataclass
class StreamingConfig:
    """Streaming behavior settings."""

    edit_throttle_ms: int = 1000
    chunk_size: int = 3800


@dataclass
class SandboxConfig:
    """Directory sandbox settings."""

    allowed_paths: list[str] = field(default_factory=list)


@dataclass
class DatabaseConfig:
    """Database settings."""

    path: str = "~/.teleclaude/teleclaude.db"


@dataclass
class Config:
    """Main configuration."""

    allowed_users: list[int] = field(default_factory=list)
    projects: dict[str, str] = field(default_factory=dict)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    approval: ApprovalConfig = field(default_factory=ApprovalConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    telegram_token: str = ""

    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is in whitelist."""
        return user_id in self.allowed_users


def load_config(path: Path | str | None = None) -> Config:
    """Load configuration from YAML file."""
    if path is None:
        path = Path.home() / ".teleclaude" / "config.yaml"
    else:
        path = Path(path)

    if not path.exists():
        return Config()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return _parse_config(data)


def _parse_config(data: dict[str, Any]) -> Config:
    """Parse config dictionary into Config object."""
    config = Config(
        allowed_users=data.get("allowed_users", []),
        projects=data.get("projects", {}),
    )

    # Parse nested configs
    if "sandbox" in data:
        config.sandbox = SandboxConfig(
            allowed_paths=data["sandbox"].get("allowed_paths", [])
        )

    if "claude" in data:
        config.claude = ClaudeConfig(
            max_turns=data["claude"].get("max_turns", 50),
            permission_mode=data["claude"].get("permission_mode", "acceptEdits"),
            max_budget_usd=data["claude"].get("max_budget_usd", 10.0),
        )

    if "approval" in data:
        config.approval = ApprovalConfig(
            dangerous_commands=data["approval"].get("dangerous_commands", []),
            require_approval_for=data["approval"].get("require_approval_for", []),
        )

    if "streaming" in data:
        config.streaming = StreamingConfig(
            edit_throttle_ms=data["streaming"].get("edit_throttle_ms", 1000),
            chunk_size=data["streaming"].get("chunk_size", 3800),
        )

    if "database" in data:
        db_path = data["database"].get("path", "~/.teleclaude/teleclaude.db")
        config.database = DatabaseConfig(path=str(Path(db_path).expanduser()))
    else:
        config.database = DatabaseConfig(
            path=str(Path("~/.teleclaude/teleclaude.db").expanduser())
        )

    return config
```

**Step 4: Run test (should pass)**

```bash
poetry run pytest tests/test_config.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add teleclaude-python/src/config/
git commit -m "feat(python): add configuration module with YAML loading"
```

---

## Task 4: Database Models

**Files:**
- Create: `teleclaude-python/src/storage/__init__.py`
- Create: `teleclaude-python/src/storage/models.py`
- Create: `teleclaude-python/tests/test_models.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_models.py`:

```python
"""Test database models."""
import pytest
from datetime import datetime
from src.storage.models import Session, Usage, AuditLog, SessionStatus


def test_session_creation():
    """Session can be created with required fields."""
    session = Session(
        id="test123",
        telegram_user_id=12345678,
        project_path="/home/user/myapp",
    )

    assert session.id == "test123"
    assert session.telegram_user_id == 12345678
    assert session.project_path == "/home/user/myapp"
    assert session.status == SessionStatus.ACTIVE


def test_session_defaults():
    """Session has sensible defaults."""
    session = Session(
        id="test123",
        telegram_user_id=12345678,
        project_path="/home/user/myapp",
    )

    assert session.claude_session_id is None
    assert session.project_name is None
    assert session.current_directory is None
    assert session.total_cost_usd == 0.0
    assert session.created_at is not None


def test_session_status_enum():
    """SessionStatus enum has expected values."""
    assert SessionStatus.ACTIVE.value == "active"
    assert SessionStatus.IDLE.value == "idle"
    assert SessionStatus.ARCHIVED.value == "archived"


def test_usage_creation():
    """Usage record can be created."""
    usage = Usage(
        session_id="test123",
        telegram_user_id=12345678,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
    )

    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.cost_usd == 0.001


def test_audit_log_creation():
    """AuditLog record can be created."""
    log = AuditLog(
        telegram_user_id=12345678,
        action="session_created",
        details="Created new session",
    )

    assert log.action == "session_created"
    assert log.details == "Created new session"
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_models.py -v
```

Expected: FAIL - module not found

**Step 3: Implement models**

Create `teleclaude-python/src/storage/__init__.py`:

```python
"""Storage module."""
from .models import Session, Usage, AuditLog, SessionStatus

__all__ = ["Session", "Usage", "AuditLog", "SessionStatus"]
```

Create `teleclaude-python/src/storage/models.py`:

```python
"""Database models."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class SessionStatus(str, Enum):
    """Session status enum."""

    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVED = "archived"


class Session(Base):
    """Session model."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    claude_session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_path: Mapped[str] = mapped_column(Text, nullable=False)
    project_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_directory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus), default=SessionStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_active: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class Usage(Base):
    """Usage tracking model."""

    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[str]] = mapped_column(
        String(32), ForeignKey("sessions.id"), nullable=True
    )
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class AuditLog(Base):
    """Audit log model."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

**Step 4: Run test (should pass)**

```bash
poetry run pytest tests/test_models.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add teleclaude-python/src/storage/
git commit -m "feat(python): add SQLAlchemy database models"
```

---

## Task 5: Database Repository

**Files:**
- Create: `teleclaude-python/src/storage/database.py`
- Create: `teleclaude-python/src/storage/repository.py`
- Create: `teleclaude-python/tests/test_repository.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_repository.py`:

```python
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
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_repository.py -v
```

Expected: FAIL - module not found

**Step 3: Implement database and repository**

Create `teleclaude-python/src/storage/database.py`:

```python
"""Database initialization and session management."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base

_engine = None
_session_factory = None


async def init_database(db_path: str) -> None:
    """Initialize database and create tables."""
    global _engine, _session_factory

    # Ensure directory exists
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Create `teleclaude-python/src/storage/repository.py`:

```python
"""Data access repository."""
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Session, Usage, AuditLog, SessionStatus


class SessionRepository:
    """Repository for session operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create_session(
        self,
        telegram_user_id: int,
        project_path: str,
        project_name: Optional[str] = None,
    ) -> Session:
        """Create a new session."""
        # Mark existing active sessions as idle
        await self._mark_existing_idle(telegram_user_id)

        session = Session(
            id=secrets.token_hex(16),
            telegram_user_id=telegram_user_id,
            project_path=project_path,
            project_name=project_name,
            current_directory=project_path,
            status=SessionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
        )

        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_active_session(self, telegram_user_id: int) -> Optional[Session]:
        """Get active session for user."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .where(Session.status == SessionStatus.ACTIVE)
            .order_by(Session.last_active.desc())
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self, telegram_user_id: int, limit: int = 10
    ) -> list[Session]:
        """List sessions for user."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .order_by(Session.last_active.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_session(self, session: Session) -> None:
        """Update session."""
        session.last_active = datetime.utcnow()
        await self.db.flush()

    async def add_cost(self, session_id: str, cost: float) -> None:
        """Add cost to session."""
        session = await self.get_session(session_id)
        if session:
            session.total_cost_usd += cost
            session.last_active = datetime.utcnow()
            await self.db.flush()

    async def set_claude_session_id(
        self, session_id: str, claude_session_id: str
    ) -> None:
        """Set Claude session ID."""
        session = await self.get_session(session_id)
        if session:
            session.claude_session_id = claude_session_id
            await self.db.flush()

    async def mark_idle(self, session_id: str) -> None:
        """Mark session as idle."""
        session = await self.get_session(session_id)
        if session:
            session.status = SessionStatus.IDLE
            session.last_active = datetime.utcnow()
            await self.db.flush()

    async def mark_active(self, session_id: str) -> None:
        """Mark session as active."""
        session = await self.get_session(session_id)
        if session:
            # Mark other active sessions as idle first
            await self._mark_existing_idle(session.telegram_user_id)
            session.status = SessionStatus.ACTIVE
            session.last_active = datetime.utcnow()
            await self.db.flush()

    async def _mark_existing_idle(self, telegram_user_id: int) -> None:
        """Mark existing active sessions as idle."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .where(Session.status == SessionStatus.ACTIVE)
        )
        for session in result.scalars():
            session.status = SessionStatus.IDLE


class UsageRepository:
    """Repository for usage tracking."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def record_usage(
        self,
        telegram_user_id: int,
        session_id: Optional[str],
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> Usage:
        """Record usage entry."""
        usage = Usage(
            telegram_user_id=telegram_user_id,
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            timestamp=datetime.utcnow(),
        )

        self.db.add(usage)
        await self.db.flush()
        return usage

    async def get_total_cost(self, telegram_user_id: int) -> float:
        """Get total cost for user."""
        result = await self.db.execute(
            select(Usage.cost_usd).where(Usage.telegram_user_id == telegram_user_id)
        )
        return sum(row[0] for row in result.all())


class AuditRepository:
    """Repository for audit logging."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def log(
        self,
        telegram_user_id: int,
        action: str,
        session_id: Optional[str] = None,
        details: Optional[str] = None,
    ) -> AuditLog:
        """Create audit log entry."""
        entry = AuditLog(
            telegram_user_id=telegram_user_id,
            session_id=session_id,
            action=action,
            details=details,
            timestamp=datetime.utcnow(),
        )

        self.db.add(entry)
        await self.db.flush()
        return entry
```

**Step 4: Update storage __init__.py**

Update `teleclaude-python/src/storage/__init__.py`:

```python
"""Storage module."""
from .models import Session, Usage, AuditLog, SessionStatus
from .database import init_database, get_session
from .repository import SessionRepository, UsageRepository, AuditRepository

__all__ = [
    "Session",
    "Usage",
    "AuditLog",
    "SessionStatus",
    "init_database",
    "get_session",
    "SessionRepository",
    "UsageRepository",
    "AuditRepository",
]
```

**Step 5: Run test (should pass)**

```bash
poetry run pytest tests/test_repository.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add teleclaude-python/src/storage/
git commit -m "feat(python): add database repository with async SQLAlchemy"
```

---

## Task 6: Security Module - Sandbox

**Files:**
- Create: `teleclaude-python/src/security/__init__.py`
- Create: `teleclaude-python/src/security/sandbox.py`
- Create: `teleclaude-python/tests/test_sandbox.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_sandbox.py`:

```python
"""Test directory sandbox."""
import pytest
from pathlib import Path
from src.security.sandbox import Sandbox
from src.exceptions import SandboxError


@pytest.fixture
def sandbox(tmp_path):
    """Create sandbox with temp directory."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "subdir").mkdir()
    return Sandbox(allowed_paths=[str(allowed)])


def test_is_path_allowed_in_allowed_dir(sandbox, tmp_path):
    """Paths within allowed directories are allowed."""
    allowed = tmp_path / "allowed"
    assert sandbox.is_path_allowed(str(allowed)) is True
    assert sandbox.is_path_allowed(str(allowed / "subdir")) is True
    assert sandbox.is_path_allowed(str(allowed / "subdir" / "file.txt")) is True


def test_is_path_allowed_outside_not_allowed(sandbox, tmp_path):
    """Paths outside allowed directories are not allowed."""
    outside = tmp_path / "outside"
    assert sandbox.is_path_allowed(str(outside)) is False
    assert sandbox.is_path_allowed("/etc/passwd") is False


def test_is_path_allowed_traversal_blocked(sandbox, tmp_path):
    """Path traversal attempts are blocked."""
    allowed = tmp_path / "allowed"
    traversal = str(allowed / ".." / "outside")
    assert sandbox.is_path_allowed(traversal) is False


def test_validate_path_raises_on_invalid(sandbox):
    """validate_path raises SandboxError for invalid paths."""
    with pytest.raises(SandboxError):
        sandbox.validate_path("/etc/passwd")


def test_validate_path_returns_resolved(sandbox, tmp_path):
    """validate_path returns resolved path for valid paths."""
    allowed = tmp_path / "allowed"
    result = sandbox.validate_path(str(allowed / "subdir"))
    assert result == str((allowed / "subdir").resolve())


def test_empty_sandbox_allows_nothing():
    """Sandbox with no allowed paths allows nothing."""
    sandbox = Sandbox(allowed_paths=[])
    assert sandbox.is_path_allowed("/home/user") is False
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_sandbox.py -v
```

Expected: FAIL - module not found

**Step 3: Implement sandbox**

Create `teleclaude-python/src/security/__init__.py`:

```python
"""Security module."""
from .sandbox import Sandbox

__all__ = ["Sandbox"]
```

Create `teleclaude-python/src/security/sandbox.py`:

```python
"""Directory sandboxing for security."""
from pathlib import Path

from src.exceptions import SandboxError


class Sandbox:
    """Directory sandbox to restrict file access."""

    def __init__(self, allowed_paths: list[str]):
        """Initialize with list of allowed base paths."""
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]

    def is_path_allowed(self, path: str) -> bool:
        """Check if path is within allowed directories."""
        if not self.allowed_paths:
            return False

        try:
            resolved = Path(path).resolve()
            return any(
                self._is_subpath(resolved, allowed) for allowed in self.allowed_paths
            )
        except (OSError, ValueError):
            return False

    def validate_path(self, path: str) -> str:
        """Validate path and return resolved path or raise SandboxError."""
        if not self.is_path_allowed(path):
            raise SandboxError(f"Path not allowed: {path}")
        return str(Path(path).resolve())

    def _is_subpath(self, path: Path, parent: Path) -> bool:
        """Check if path is equal to or a subpath of parent."""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False
```

**Step 4: Run test (should pass)**

```bash
poetry run pytest tests/test_sandbox.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add teleclaude-python/src/security/
git commit -m "feat(python): add directory sandbox for security"
```

---

## Task 7: Utils - Formatting

**Files:**
- Create: `teleclaude-python/src/utils/__init__.py`
- Create: `teleclaude-python/src/utils/formatting.py`
- Create: `teleclaude-python/tests/test_formatting.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_formatting.py`:

```python
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
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_formatting.py -v
```

Expected: FAIL - module not found

**Step 3: Implement formatting**

Create `teleclaude-python/src/utils/__init__.py`:

```python
"""Utilities module."""
from .formatting import escape_markdown, format_tool_use, chunk_text, truncate_text

__all__ = ["escape_markdown", "format_tool_use", "chunk_text", "truncate_text"]
```

Create `teleclaude-python/src/utils/formatting.py`:

```python
"""Telegram formatting utilities."""
import re
from pathlib import Path

# Characters that need escaping in Telegram MarkdownV2
MARKDOWN_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!"


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    return re.sub(f"([{re.escape(MARKDOWN_SPECIAL_CHARS)}])", r"\\\1", text)


def format_tool_use(tool_name: str, tool_input: dict) -> str:
    """Format tool use as inline annotation."""
    icons = {
        "Read": "📁",
        "Write": "📝",
        "Edit": "✏️",
        "Bash": "⚡",
        "Grep": "🔍",
        "Glob": "🔎",
    }
    icon = icons.get(tool_name, "🔧")

    # Extract relevant info based on tool type
    if tool_name in ("Read", "Write", "Edit"):
        path = tool_input.get("file_path", "")
        name = Path(path).name if path else "file"
        return f"[{icon} {name}]"

    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        cmd_short = truncate_text(cmd, max_len=40)
        return f"[{icon} {cmd_short}]"

    elif tool_name in ("Grep", "Glob"):
        pattern = tool_input.get("pattern", "")
        return f"[{icon} {pattern}]"

    else:
        return f"[{icon} {tool_name}]"


def chunk_text(text: str, max_size: int = 3800) -> list[str]:
    """Split text into chunks respecting max size."""
    if len(text) <= max_size:
        return [text]

    chunks = []
    current = ""

    for char in text:
        if len(current) >= max_size:
            chunks.append(current)
            current = ""
        current += char

    if current:
        chunks.append(current)

    return chunks


def truncate_text(text: str, max_len: int = 4096) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
```

**Step 4: Run test (should pass)**

```bash
poetry run pytest tests/test_formatting.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add teleclaude-python/src/utils/
git commit -m "feat(python): add Telegram formatting utilities"
```

---

## Task 8: Utils - Keyboards

**Files:**
- Create: `teleclaude-python/src/utils/keyboards.py`
- Create: `teleclaude-python/tests/test_keyboards.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_keyboards.py`:

```python
"""Test keyboard builders."""
import pytest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.utils.keyboards import (
    project_keyboard,
    session_keyboard,
    approval_keyboard,
    cancel_keyboard,
)


def test_project_keyboard_with_projects():
    """project_keyboard creates buttons for projects."""
    projects = {"myapp": "/home/user/myapp", "api": "/home/user/api"}
    keyboard = project_keyboard(projects)

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 3  # 2 projects + other button
    assert keyboard.inline_keyboard[0][0].text == "myapp"


def test_project_keyboard_empty():
    """project_keyboard with no projects shows only Other."""
    keyboard = project_keyboard({})

    assert len(keyboard.inline_keyboard) == 1
    assert "other" in keyboard.inline_keyboard[0][0].callback_data.lower()


def test_session_keyboard_with_sessions():
    """session_keyboard creates buttons for sessions."""
    sessions = [
        type("Session", (), {"id": "abc123", "project_name": "myapp", "status": "active"}),
        type("Session", (), {"id": "def456", "project_name": "api", "status": "idle"}),
    ]
    keyboard = session_keyboard(sessions)

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 2


def test_approval_keyboard():
    """approval_keyboard creates approve/deny buttons."""
    keyboard = approval_keyboard("req123")

    assert isinstance(keyboard, InlineKeyboardMarkup)
    buttons = keyboard.inline_keyboard[0]
    assert len(buttons) == 2

    texts = [b.text for b in buttons]
    assert any("approve" in t.lower() or "✅" in t for t in texts)
    assert any("deny" in t.lower() or "❌" in t for t in texts)


def test_cancel_keyboard():
    """cancel_keyboard creates cancel button."""
    keyboard = cancel_keyboard()

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 1
    assert "cancel" in keyboard.inline_keyboard[0][0].callback_data.lower()
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_keyboards.py -v
```

Expected: FAIL - module not found

**Step 3: Implement keyboards**

Create `teleclaude-python/src/utils/keyboards.py`:

```python
"""Telegram inline keyboard builders."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def project_keyboard(projects: dict[str, str]) -> InlineKeyboardMarkup:
    """Create project selection keyboard."""
    buttons = []

    for name, path in projects.items():
        buttons.append(
            [InlineKeyboardButton(name, callback_data=f"project:{name}")]
        )

    # Always add "Other" option for custom path
    buttons.append(
        [InlineKeyboardButton("📁 Other...", callback_data="project:other")]
    )

    return InlineKeyboardMarkup(buttons)


def session_keyboard(sessions: list) -> InlineKeyboardMarkup:
    """Create session selection keyboard."""
    buttons = []

    for session in sessions:
        status_icon = "🟢" if session.status == "active" else "⚪"
        name = session.project_name or session.id[:8]
        text = f"{status_icon} {name}"
        buttons.append(
            [InlineKeyboardButton(text, callback_data=f"session:{session.id}")]
        )

    return InlineKeyboardMarkup(buttons)


def approval_keyboard(request_id: str) -> InlineKeyboardMarkup:
    """Create approval buttons for dangerous operations."""
    buttons = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{request_id}"),
            InlineKeyboardButton("❌ Deny", callback_data=f"deny:{request_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Create cancel button."""
    buttons = [
        [InlineKeyboardButton("🛑 Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Create confirmation keyboard for destructive actions."""
    buttons = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{action}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)
```

**Step 4: Update utils __init__.py**

Update `teleclaude-python/src/utils/__init__.py`:

```python
"""Utilities module."""
from .formatting import escape_markdown, format_tool_use, chunk_text, truncate_text
from .keyboards import (
    project_keyboard,
    session_keyboard,
    approval_keyboard,
    cancel_keyboard,
    confirm_keyboard,
)

__all__ = [
    "escape_markdown",
    "format_tool_use",
    "chunk_text",
    "truncate_text",
    "project_keyboard",
    "session_keyboard",
    "approval_keyboard",
    "cancel_keyboard",
    "confirm_keyboard",
]
```

**Step 5: Run test (should pass)**

```bash
poetry run pytest tests/test_keyboards.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add teleclaude-python/src/utils/
git commit -m "feat(python): add Telegram inline keyboard builders"
```

---

## Task 9: Claude Client Wrapper

**Files:**
- Create: `teleclaude-python/src/claude/__init__.py`
- Create: `teleclaude-python/src/claude/client.py`
- Create: `teleclaude-python/tests/test_claude_client.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_claude_client.py`:

```python
"""Test Claude client wrapper."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.claude.client import TeleClaudeClient
from src.config.settings import Config, ClaudeConfig


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return Config(
        allowed_users=[12345678],
        claude=ClaudeConfig(
            max_turns=10,
            permission_mode="acceptEdits",
            max_budget_usd=5.0,
        ),
    )


@pytest.fixture
def mock_session():
    """Create mock session."""
    return MagicMock(
        id="test123",
        claude_session_id=None,
        current_directory="/home/user/myapp",
    )


def test_client_init(mock_config, mock_session):
    """Client initializes with config and session."""
    client = TeleClaudeClient(mock_config, mock_session)

    assert client.config == mock_config
    assert client.session == mock_session
    assert client._client is None


def test_client_builds_options(mock_config, mock_session):
    """Client builds correct options."""
    client = TeleClaudeClient(mock_config, mock_session)
    options = client._build_options()

    assert options.max_turns == 10
    assert options.permission_mode == "acceptEdits"
    assert options.cwd == "/home/user/myapp"


def test_client_builds_options_with_resume(mock_config, mock_session):
    """Client includes resume when session has claude_session_id."""
    mock_session.claude_session_id = "claude_abc123"
    client = TeleClaudeClient(mock_config, mock_session)
    options = client._build_options()

    assert options.resume == "claude_abc123"
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_claude_client.py -v
```

Expected: FAIL - module not found

**Step 3: Implement Claude client**

Create `teleclaude-python/src/claude/__init__.py`:

```python
"""Claude integration module."""
from .client import TeleClaudeClient

__all__ = ["TeleClaudeClient"]
```

Create `teleclaude-python/src/claude/client.py`:

```python
"""Claude SDK client wrapper."""
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from src.config.settings import Config
from src.storage.models import Session


@dataclass
class ClaudeOptions:
    """Options for Claude SDK (placeholder until SDK available)."""

    max_turns: int = 50
    permission_mode: str = "acceptEdits"
    max_budget_usd: float = 10.0
    cwd: Optional[str] = None
    resume: Optional[str] = None
    allowed_tools: list[str] = None
    hooks: dict = None

    def __post_init__(self):
        if self.allowed_tools is None:
            self.allowed_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        if self.hooks is None:
            self.hooks = {}


class TeleClaudeClient:
    """Wrapper for Claude SDK client."""

    def __init__(self, config: Config, session: Session):
        """Initialize with configuration and session."""
        self.config = config
        self.session = session
        self._client = None

    def _build_options(self) -> ClaudeOptions:
        """Build Claude SDK options."""
        options = ClaudeOptions(
            max_turns=self.config.claude.max_turns,
            permission_mode=self.config.claude.permission_mode,
            max_budget_usd=self.config.claude.max_budget_usd,
            cwd=self.session.current_directory,
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        )

        if self.session.claude_session_id:
            options.resume = self.session.claude_session_id

        return options

    async def __aenter__(self) -> "TeleClaudeClient":
        """Enter async context - connect to Claude."""
        # TODO: Replace with actual SDK when available
        # from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
        #
        # options = ClaudeAgentOptions(
        #     **self._build_options().__dict__
        # )
        # self._client = ClaudeSDKClient(options=options)
        # await self._client.connect()
        return self

    async def __aexit__(self, *args) -> None:
        """Exit async context - disconnect."""
        if self._client:
            # await self._client.disconnect()
            pass

    async def query(self, prompt: str) -> AsyncIterator:
        """Send prompt and yield messages."""
        # TODO: Replace with actual SDK implementation
        # await self._client.query(prompt)
        # async for message in self._client.receive_messages():
        #     yield message

        # Placeholder implementation for testing
        yield {
            "type": "assistant",
            "content": [{"type": "text", "text": f"Response to: {prompt}"}],
        }

    def get_session_id(self) -> Optional[str]:
        """Get Claude session ID if available."""
        return self.session.claude_session_id
```

**Step 4: Run test (should pass)**

```bash
poetry run pytest tests/test_claude_client.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add teleclaude-python/src/claude/
git commit -m "feat(python): add Claude SDK client wrapper"
```

---

## Task 10: Claude Hooks

**Files:**
- Create: `teleclaude-python/src/claude/hooks.py`
- Create: `teleclaude-python/tests/test_hooks.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_hooks.py`:

```python
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
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_hooks.py -v
```

Expected: FAIL - module not found

**Step 3: Implement hooks**

Create `teleclaude-python/src/claude/hooks.py`:

```python
"""Claude SDK hooks for approval workflow."""
from typing import Any

# Patterns that require user approval
DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -r /",
    "sudo rm",
    "sudo",
    "git push --force",
    "git push -f",
    "chmod 777",
    "chmod -R 777",
    "> /dev/sd",
    "mkfs.",
    "dd if=",
    ":(){:|:&};:",  # Fork bomb
    "wget | sh",
    "curl | sh",
]


def is_dangerous_command(command: str) -> bool:
    """Check if command matches dangerous patterns."""
    command_lower = command.lower()
    return any(pattern in command_lower for pattern in DANGEROUS_PATTERNS)


async def check_dangerous_command(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    """PreToolUse hook to intercept dangerous operations."""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Bash":
        return {}

    command = tool_input.get("command", "")

    if is_dangerous_command(command):
        # Find which pattern matched
        matched = next(
            (p for p in DANGEROUS_PATTERNS if p in command.lower()),
            "dangerous pattern",
        )

        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"Command contains: {matched}",
            }
        }

    return {}


def create_approval_hooks(dangerous_commands: list[str] | None = None) -> dict:
    """Create hooks dict for ClaudeAgentOptions."""
    # Note: This would use HookMatcher when SDK is available
    # from claude_agent_sdk import HookMatcher
    #
    # return {
    #     "PreToolUse": [
    #         HookMatcher(matcher="Bash", hooks=[check_dangerous_command]),
    #     ]
    # }

    return {
        "PreToolUse": {
            "Bash": [check_dangerous_command],
        }
    }
```

**Step 4: Update claude __init__.py**

Update `teleclaude-python/src/claude/__init__.py`:

```python
"""Claude integration module."""
from .client import TeleClaudeClient
from .hooks import (
    is_dangerous_command,
    check_dangerous_command,
    create_approval_hooks,
    DANGEROUS_PATTERNS,
)

__all__ = [
    "TeleClaudeClient",
    "is_dangerous_command",
    "check_dangerous_command",
    "create_approval_hooks",
    "DANGEROUS_PATTERNS",
]
```

**Step 5: Run test (should pass)**

```bash
poetry run pytest tests/test_hooks.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add teleclaude-python/src/claude/
git commit -m "feat(python): add Claude SDK hooks for approval workflow"
```

---

## Task 11: Bot Middleware

**Files:**
- Create: `teleclaude-python/src/bot/__init__.py`
- Create: `teleclaude-python/src/bot/middleware.py`
- Create: `teleclaude-python/tests/test_middleware.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_middleware.py`:

```python
"""Test bot middleware."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.bot.middleware import auth_middleware
from src.config.settings import Config


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock()
    update.effective_user.id = 12345678
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock context with config."""
    context = MagicMock()
    context.bot_data = {
        "config": Config(allowed_users=[12345678])
    }
    return context


@pytest.mark.asyncio
async def test_auth_middleware_allows_authorized(mock_update, mock_context):
    """auth_middleware allows authorized users."""
    handler = AsyncMock(return_value="success")
    wrapped = auth_middleware(handler)

    result = await wrapped(mock_update, mock_context)

    assert result == "success"
    handler.assert_called_once_with(mock_update, mock_context)


@pytest.mark.asyncio
async def test_auth_middleware_blocks_unauthorized(mock_update, mock_context):
    """auth_middleware blocks unauthorized users."""
    mock_update.effective_user.id = 99999999  # Not in whitelist
    handler = AsyncMock()
    wrapped = auth_middleware(handler)

    await wrapped(mock_update, mock_context)

    handler.assert_not_called()
    mock_update.message.reply_text.assert_called_once()
    assert "Unauthorized" in str(mock_update.message.reply_text.call_args)


@pytest.mark.asyncio
async def test_auth_middleware_preserves_function_name():
    """auth_middleware preserves wrapped function name."""
    async def my_handler(update, context):
        pass

    wrapped = auth_middleware(my_handler)

    assert wrapped.__name__ == "my_handler"
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_middleware.py -v
```

Expected: FAIL - module not found

**Step 3: Implement middleware**

Create `teleclaude-python/src/bot/__init__.py`:

```python
"""Bot module."""
from .middleware import auth_middleware

__all__ = ["auth_middleware"]
```

Create `teleclaude-python/src/bot/middleware.py`:

```python
"""Bot middleware for authentication and logging."""
from functools import wraps
from typing import Callable, TypeVar

from telegram import Update
from telegram.ext import ContextTypes

F = TypeVar("F", bound=Callable)


def auth_middleware(handler: F) -> F:
    """Decorator to check user authentication."""

    @wraps(handler)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        config = context.bot_data.get("config")

        if config is None:
            await update.message.reply_text("⚠️ Bot not configured")
            return

        user_id = update.effective_user.id

        if not config.is_user_allowed(user_id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        return await handler(update, context)

    return wrapper
```

**Step 4: Run test (should pass)**

```bash
poetry run pytest tests/test_middleware.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add teleclaude-python/src/bot/
git commit -m "feat(python): add bot authentication middleware"
```

---

## Task 12: Bot Command Handlers - Core

**Files:**
- Create: `teleclaude-python/src/bot/handlers.py`
- Create: `teleclaude-python/tests/test_handlers.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_handlers.py`:

```python
"""Test bot command handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.bot.handlers import start, help_cmd, pwd


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock()
    update.effective_user.id = 12345678
    update.effective_user.first_name = "Test"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = MagicMock()
    context.bot_data = {"config": MagicMock()}
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_start_handler(mock_update, mock_context):
    """start handler sends welcome message."""
    await start(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = str(mock_update.message.reply_text.call_args)
    assert "TeleClaude" in call_args or "Welcome" in call_args


@pytest.mark.asyncio
async def test_help_handler(mock_update, mock_context):
    """help handler lists commands."""
    await help_cmd(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = str(mock_update.message.reply_text.call_args)
    assert "/new" in call_args
    assert "/help" in call_args


@pytest.mark.asyncio
async def test_pwd_with_session(mock_update, mock_context):
    """pwd shows current directory when session exists."""
    mock_context.user_data["current_session"] = MagicMock(
        current_directory="/home/user/myapp"
    )

    await pwd(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = str(mock_update.message.reply_text.call_args)
    assert "/home/user/myapp" in call_args


@pytest.mark.asyncio
async def test_pwd_without_session(mock_update, mock_context):
    """pwd shows error when no session."""
    mock_context.user_data["current_session"] = None

    await pwd(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = str(mock_update.message.reply_text.call_args)
    assert "session" in call_args.lower()
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_handlers.py -v
```

Expected: FAIL - module not found

**Step 3: Implement handlers**

Create `teleclaude-python/src/bot/handlers.py`:

```python
"""Telegram bot command handlers."""
from telegram import Update
from telegram.ext import ContextTypes

from src.utils.keyboards import project_keyboard, cancel_keyboard


HELP_TEXT = """
📱 *TeleClaude Commands*

*Session Management*
/new \\[project\\] \\- Start new session
/continue \\- Resume last session
/sessions \\- List all sessions
/switch <id> \\- Switch to session
/cancel \\- Stop current operation

*Navigation*
/cd <path> \\- Change directory
/ls \\[path\\] \\- List directory
/pwd \\- Show current directory

*Tools*
/git \\[cmd\\] \\- Git operations
/export \\[fmt\\] \\- Export session
/cost \\- Show usage costs

*Help*
/help \\- Show this message
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome to TeleClaude, {user.first_name}!\n\n"
        "I'm your mobile interface to Claude Code.\n\n"
        "Use /new to start a new session or /help for all commands."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")


async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new command."""
    config = context.bot_data.get("config")

    if context.args:
        # Project name provided
        project_name = context.args[0]
        if project_name in config.projects:
            project_path = config.projects[project_name]
            await _create_session(update, context, project_path, project_name)
        else:
            await update.message.reply_text(
                f"❌ Project '{project_name}' not found.\n"
                "Use /new without arguments to see available projects."
            )
    else:
        # Show project selection keyboard
        keyboard = project_keyboard(config.projects)
        await update.message.reply_text(
            "📁 Select a project or choose Other to enter a path:",
            reply_markup=keyboard,
        )


async def continue_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /continue command."""
    session = context.user_data.get("current_session")

    if session:
        await update.message.reply_text(
            f"▶️ Continuing session in `{session.project_name or session.project_path}`\n\n"
            "Send a message to chat with Claude.",
            parse_mode="MarkdownV2",
        )
    else:
        await update.message.reply_text(
            "❌ No active session. Use /new to start one."
        )


async def list_sessions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /sessions command."""
    # TODO: Load sessions from database
    await update.message.reply_text(
        "📋 *Your Sessions*\n\nNo sessions found\\. Use /new to create one\\.",
        parse_mode="MarkdownV2",
    )


async def switch_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /switch command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /switch <session_id>\n\nUse /sessions to see available sessions."
        )
        return

    session_id = context.args[0]
    # TODO: Load session from database
    await update.message.reply_text(f"🔄 Switching to session {session_id}...")


async def show_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cost command."""
    session = context.user_data.get("current_session")

    if session:
        await update.message.reply_text(
            f"💰 *Session Cost*\n\n"
            f"Current session: ${session.total_cost_usd:.4f}",
            parse_mode="MarkdownV2",
        )
    else:
        await update.message.reply_text(
            "💰 *Usage Cost*\n\nNo active session\\.",
            parse_mode="MarkdownV2",
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command."""
    # TODO: Cancel running Claude operation
    await update.message.reply_text("🛑 Operation cancelled.")


async def cd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cd command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /cd <path>")
        return

    new_path = context.args[0]
    # TODO: Validate path with sandbox
    session.current_directory = new_path
    await update.message.reply_text(f"📂 Changed to: `{new_path}`", parse_mode="MarkdownV2")


async def ls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ls command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    path = context.args[0] if context.args else session.current_directory
    # TODO: List directory contents
    await update.message.reply_text(f"📁 Contents of `{path}`:\n\n(not implemented)", parse_mode="MarkdownV2")


async def pwd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pwd command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    await update.message.reply_text(
        f"📂 Current directory: `{session.current_directory}`",
        parse_mode="MarkdownV2",
    )


async def git(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /git command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /git <command>\n\n"
            "Examples:\n"
            "  /git status\n"
            "  /git log\n"
            "  /git diff"
        )
        return

    git_cmd = " ".join(context.args)
    # TODO: Execute git command
    await update.message.reply_text(f"🔀 Running: git {git_cmd}")


async def export_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /export command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    format_type = context.args[0] if context.args else "md"
    valid_formats = ["md", "html", "json"]

    if format_type not in valid_formats:
        await update.message.reply_text(
            f"❌ Invalid format. Use: {', '.join(valid_formats)}"
        )
        return

    # TODO: Export session
    await update.message.reply_text(f"📤 Exporting session as {format_type}...")


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle regular text messages (Claude interaction)."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text(
            "❌ No active session. Use /new to start one or /continue to resume."
        )
        return

    prompt = update.message.text

    # Send "thinking" message
    thinking_msg = await update.message.reply_text(
        "🤔 Thinking...",
        reply_markup=cancel_keyboard(),
    )

    # TODO: Send to Claude and stream response
    await thinking_msg.edit_text(
        f"Response to: {prompt}\n\n(Claude integration pending)"
    )


async def _create_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project_path: str,
    project_name: str | None = None,
) -> None:
    """Create a new session."""
    # TODO: Create session in database
    await update.message.reply_text(
        f"✅ Created new session for `{project_name or project_path}`\n\n"
        "Send a message to start chatting with Claude.",
        parse_mode="MarkdownV2",
    )
```

**Step 4: Update bot __init__.py**

Update `teleclaude-python/src/bot/__init__.py`:

```python
"""Bot module."""
from .middleware import auth_middleware
from .handlers import (
    start,
    help_cmd,
    new_session,
    continue_session,
    list_sessions,
    switch_session,
    show_cost,
    cancel,
    cd,
    ls,
    pwd,
    git,
    export_session,
    handle_message,
)

__all__ = [
    "auth_middleware",
    "start",
    "help_cmd",
    "new_session",
    "continue_session",
    "list_sessions",
    "switch_session",
    "show_cost",
    "cancel",
    "cd",
    "ls",
    "pwd",
    "git",
    "export_session",
    "handle_message",
]
```

**Step 5: Run test (should pass)**

```bash
poetry run pytest tests/test_handlers.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add teleclaude-python/src/bot/
git commit -m "feat(python): add bot command handlers"
```

---

## Task 13: Bot Callbacks

**Files:**
- Create: `teleclaude-python/src/bot/callbacks.py`
- Create: `teleclaude-python/tests/test_callbacks.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_callbacks.py`:

```python
"""Test callback handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.bot.callbacks import handle_callback, parse_callback_data


def test_parse_callback_data_simple():
    """parse_callback_data handles simple callbacks."""
    action, data = parse_callback_data("cancel")
    assert action == "cancel"
    assert data is None


def test_parse_callback_data_with_value():
    """parse_callback_data handles callbacks with values."""
    action, data = parse_callback_data("project:myapp")
    assert action == "project"
    assert data == "myapp"


def test_parse_callback_data_with_colon_in_value():
    """parse_callback_data handles colons in values."""
    action, data = parse_callback_data("approve:req:123:abc")
    assert action == "approve"
    assert data == "req:123:abc"


@pytest.fixture
def mock_callback_query():
    """Create mock callback query."""
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.message.reply_text = AsyncMock()
    return query


@pytest.fixture
def mock_update(mock_callback_query):
    """Create mock update with callback query."""
    update = MagicMock()
    update.callback_query = mock_callback_query
    update.effective_user.id = 12345678
    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = MagicMock()
    context.bot_data = {
        "config": MagicMock(
            projects={"myapp": "/home/user/myapp"}
        )
    }
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_handle_callback_cancel(mock_update, mock_context):
    """handle_callback processes cancel."""
    mock_update.callback_query.data = "cancel"

    await handle_callback(mock_update, mock_context)

    mock_update.callback_query.answer.assert_called()


@pytest.mark.asyncio
async def test_handle_callback_project_selection(mock_update, mock_context):
    """handle_callback processes project selection."""
    mock_update.callback_query.data = "project:myapp"

    await handle_callback(mock_update, mock_context)

    mock_update.callback_query.answer.assert_called()
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_callbacks.py -v
```

Expected: FAIL - module not found

**Step 3: Implement callbacks**

Create `teleclaude-python/src/bot/callbacks.py`:

```python
"""Telegram callback query handlers."""
from telegram import Update
from telegram.ext import ContextTypes


def parse_callback_data(data: str) -> tuple[str, str | None]:
    """Parse callback data into action and value."""
    if ":" in data:
        action, _, value = data.partition(":")
        return action, value
    return data, None


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()

    action, value = parse_callback_data(query.data)

    handlers = {
        "cancel": _handle_cancel,
        "project": _handle_project_select,
        "session": _handle_session_select,
        "approve": _handle_approve,
        "deny": _handle_deny,
        "confirm": _handle_confirm,
    }

    handler = handlers.get(action)
    if handler:
        await handler(update, context, value)
    else:
        await query.edit_message_text(f"❓ Unknown action: {action}")


async def _handle_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle cancel callback."""
    query = update.callback_query
    # TODO: Cancel any running operation
    await query.edit_message_text("🛑 Cancelled.")


async def _handle_project_select(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle project selection callback."""
    query = update.callback_query
    config = context.bot_data.get("config")

    if value == "other":
        await query.edit_message_text(
            "📁 Send me the path to your project directory."
        )
        context.user_data["awaiting_path"] = True
        return

    if value and value in config.projects:
        project_path = config.projects[value]
        # TODO: Create session
        await query.edit_message_text(
            f"✅ Starting session for `{value}`\n\n"
            f"Path: `{project_path}`\n\n"
            "Send a message to chat with Claude."
        )
    else:
        await query.edit_message_text(f"❌ Project not found: {value}")


async def _handle_session_select(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle session selection callback."""
    query = update.callback_query

    if value:
        # TODO: Load and switch to session
        await query.edit_message_text(f"🔄 Switched to session: {value[:8]}...")
    else:
        await query.edit_message_text("❌ Invalid session.")


async def _handle_approve(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle approval callback."""
    query = update.callback_query

    if value:
        # TODO: Approve the operation
        await query.edit_message_text(f"✅ Approved operation: {value[:8]}...")
    else:
        await query.edit_message_text("❌ Invalid approval request.")


async def _handle_deny(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle denial callback."""
    query = update.callback_query

    if value:
        # TODO: Deny the operation
        await query.edit_message_text(f"❌ Denied operation: {value[:8]}...")
    else:
        await query.edit_message_text("❌ Invalid denial request.")


async def _handle_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle confirmation callback."""
    query = update.callback_query

    if value:
        # TODO: Execute confirmed action
        await query.edit_message_text(f"✅ Confirmed: {value}")
    else:
        await query.edit_message_text("❌ Invalid confirmation.")
```

**Step 4: Update bot __init__.py**

Update `teleclaude-python/src/bot/__init__.py`:

```python
"""Bot module."""
from .middleware import auth_middleware
from .handlers import (
    start,
    help_cmd,
    new_session,
    continue_session,
    list_sessions,
    switch_session,
    show_cost,
    cancel,
    cd,
    ls,
    pwd,
    git,
    export_session,
    handle_message,
)
from .callbacks import handle_callback, parse_callback_data

__all__ = [
    "auth_middleware",
    "start",
    "help_cmd",
    "new_session",
    "continue_session",
    "list_sessions",
    "switch_session",
    "show_cost",
    "cancel",
    "cd",
    "ls",
    "pwd",
    "git",
    "export_session",
    "handle_message",
    "handle_callback",
    "parse_callback_data",
]
```

**Step 5: Run test (should pass)**

```bash
poetry run pytest tests/test_callbacks.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add teleclaude-python/src/bot/
git commit -m "feat(python): add callback query handlers"
```

---

## Task 14: Bot Application

**Files:**
- Create: `teleclaude-python/src/bot/application.py`
- Create: `teleclaude-python/tests/test_application.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_application.py`:

```python
"""Test bot application setup."""
import pytest
from unittest.mock import MagicMock, patch
from src.bot.application import create_application
from src.config.settings import Config


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return Config(
        allowed_users=[12345678],
        telegram_token="test_token",
    )


def test_create_application_returns_application(mock_config):
    """create_application returns Application instance."""
    with patch("src.bot.application.Application") as MockApp:
        mock_builder = MagicMock()
        MockApp.builder.return_value = mock_builder
        mock_builder.token.return_value = mock_builder
        mock_builder.build.return_value = MagicMock()

        app = create_application(mock_config)

        MockApp.builder.assert_called_once()
        mock_builder.token.assert_called_once_with("test_token")
        mock_builder.build.assert_called_once()


def test_create_application_stores_config(mock_config):
    """create_application stores config in bot_data."""
    with patch("src.bot.application.Application") as MockApp:
        mock_app = MagicMock()
        mock_app.bot_data = {}
        MockApp.builder.return_value.token.return_value.build.return_value = mock_app

        create_application(mock_config)

        assert mock_app.bot_data["config"] == mock_config
```

**Step 2: Run test (should fail)**

```bash
poetry run pytest tests/test_application.py -v
```

Expected: FAIL - module not found

**Step 3: Implement application**

Create `teleclaude-python/src/bot/application.py`:

```python
"""Telegram bot application setup."""
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from src.config.settings import Config
from .middleware import auth_middleware
from .handlers import (
    start,
    help_cmd,
    new_session,
    continue_session,
    list_sessions,
    switch_session,
    show_cost,
    cancel,
    cd,
    ls,
    pwd,
    git,
    export_session,
    handle_message,
)
from .callbacks import handle_callback


def create_application(config: Config) -> Application:
    """Create and configure Telegram Application."""
    app = Application.builder().token(config.telegram_token).build()

    # Store config in bot_data for handlers to access
    app.bot_data["config"] = config

    # Command handlers with auth middleware
    commands = [
        ("start", start),
        ("help", help_cmd),
        ("new", new_session),
        ("continue", continue_session),
        ("sessions", list_sessions),
        ("switch", switch_session),
        ("cost", show_cost),
        ("cancel", cancel),
        ("cd", cd),
        ("ls", ls),
        ("pwd", pwd),
        ("git", git),
        ("export", export_session),
    ]

    for command, handler in commands:
        app.add_handler(CommandHandler(command, auth_middleware(handler)))

    # Message handler for Claude interactions
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            auth_middleware(handle_message),
        )
    )

    # Callback handler for inline keyboards
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app
```

**Step 4: Update bot __init__.py**

Update `teleclaude-python/src/bot/__init__.py`:

```python
"""Bot module."""
from .middleware import auth_middleware
from .handlers import (
    start,
    help_cmd,
    new_session,
    continue_session,
    list_sessions,
    switch_session,
    show_cost,
    cancel,
    cd,
    ls,
    pwd,
    git,
    export_session,
    handle_message,
)
from .callbacks import handle_callback, parse_callback_data
from .application import create_application

__all__ = [
    "auth_middleware",
    "start",
    "help_cmd",
    "new_session",
    "continue_session",
    "list_sessions",
    "switch_session",
    "show_cost",
    "cancel",
    "cd",
    "ls",
    "pwd",
    "git",
    "export_session",
    "handle_message",
    "handle_callback",
    "parse_callback_data",
    "create_application",
]
```

**Step 5: Run test (should pass)**

```bash
poetry run pytest tests/test_application.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add teleclaude-python/src/bot/
git commit -m "feat(python): add bot application setup"
```

---

## Task 15: Main Entry Point

**Files:**
- Update: `teleclaude-python/src/main.py`
- Create: `teleclaude-python/tests/test_main.py`

**Step 1: Write test**

Create `teleclaude-python/tests/test_main.py`:

```python
"""Test main entry point."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os


def test_main_requires_token(tmp_path, monkeypatch):
    """main exits if TELEGRAM_BOT_TOKEN not set."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    # Import after clearing env
    from src.main import main
    import asyncio

    # Should not raise, just log error and return
    asyncio.run(main())


@pytest.mark.asyncio
async def test_main_loads_config(tmp_path, monkeypatch):
    """main loads configuration."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")

    config_content = """
allowed_users:
  - 12345678
"""
    config_dir = tmp_path / ".teleclaude"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(config_content)

    with patch("src.main.Path.home", return_value=tmp_path):
        with patch("src.main.create_application") as mock_create:
            mock_app = MagicMock()
            mock_app.run_polling = AsyncMock()
            mock_create.return_value = mock_app

            with patch("src.main.init_database", new_callable=AsyncMock):
                from src.main import main
                await main()

                mock_create.assert_called_once()
```

**Step 2: Update main.py**

Update `teleclaude-python/src/main.py`:

```python
"""TeleClaude entry point."""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from src.config.settings import load_config
from src.storage.database import init_database
from src.bot.application import create_application

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point."""
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable required")
        return

    # Load configuration
    config_path = Path.home() / ".teleclaude" / "config.yaml"
    config = load_config(config_path)
    config.telegram_token = token

    # Initialize database
    await init_database(config.database.path)

    # Create and run bot
    app = create_application(config)

    logger.info("TeleClaude starting...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 3: Run test (should pass)**

```bash
poetry run pytest tests/test_main.py -v
```

Expected: All tests PASS

**Step 4: Commit**

```bash
git add teleclaude-python/src/main.py teleclaude-python/tests/test_main.py
git commit -m "feat(python): implement main entry point with config and database"
```

---

## Task 16: README and Final Polish

**Files:**
- Create: `teleclaude-python/README.md`
- Create: `teleclaude-python/.gitignore`

**Step 1: Create README**

Create `teleclaude-python/README.md`:

```markdown
# TeleClaude Python

A Telegram bot for interacting with Claude Code from your mobile device.

Successor to [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) using the Claude Agent SDK.

## Features

- Real-time streaming of Claude responses
- Session management with resume support
- Category-based approval for dangerous operations
- Cost tracking per session
- Multi-project support
- Directory navigation commands
- Git integration

## Requirements

- Python 3.10+
- Claude Code CLI installed
- Telegram Bot Token

## Installation

```bash
# Clone the repository
git clone https://github.com/user/teleclaude-python.git
cd teleclaude-python

# Install with Poetry
poetry install

# Or with pip
pip install .
```

## Configuration

1. Create config directory:
```bash
mkdir -p ~/.teleclaude
```

2. Copy example config:
```bash
cp config.example.yaml ~/.teleclaude/config.yaml
```

3. Edit `~/.teleclaude/config.yaml`:
```yaml
allowed_users:
  - YOUR_TELEGRAM_USER_ID

projects:
  myapp: /path/to/your/project
```

4. Set environment variables:
```bash
export TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Usage

```bash
# Run with Poetry
poetry run python -m src.main

# Or directly
python -m src.main
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show all commands |
| `/new [project]` | Start new session |
| `/continue` | Resume last session |
| `/sessions` | List all sessions |
| `/switch <id>` | Switch to session |
| `/cost` | Show usage costs |
| `/cancel` | Stop operation |
| `/cd <path>` | Change directory |
| `/ls [path]` | List directory |
| `/pwd` | Show current directory |
| `/git [cmd]` | Git operations |
| `/export [fmt]` | Export session |

## Development

```bash
# Install dev dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Run linting
poetry run ruff check .

# Run type checking
poetry run mypy src/
```

## License

MIT
```

**Step 2: Create .gitignore**

Create `teleclaude-python/.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# Poetry
poetry.lock

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.mypy_cache/

# Environment
.env
.env.local

# Database
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db
```

**Step 3: Run all tests**

```bash
cd teleclaude-python
poetry run pytest -v
```

Expected: All tests PASS

**Step 4: Commit**

```bash
git add teleclaude-python/README.md teleclaude-python/.gitignore
git commit -m "docs(python): add README and gitignore"
```

---

## Summary

This plan implements TeleClaude Python in 16 tasks:

1. **Project Scaffolding** - Poetry, pyproject.toml, main.py
2. **Exceptions Module** - Custom exception hierarchy
3. **Configuration Module** - YAML loading with dataclasses
4. **Database Models** - SQLAlchemy ORM models
5. **Database Repository** - Async data access layer
6. **Security Sandbox** - Directory access validation
7. **Formatting Utils** - Telegram markdown, tool annotations
8. **Keyboard Utils** - Inline keyboard builders
9. **Claude Client** - SDK wrapper with options
10. **Claude Hooks** - PreToolUse approval hooks
11. **Bot Middleware** - Authentication decorator
12. **Bot Handlers** - Command handlers
13. **Bot Callbacks** - Inline keyboard callbacks
14. **Bot Application** - Application setup
15. **Main Entry Point** - Wiring everything together
16. **Documentation** - README and polish

Each task follows TDD: write failing test, implement, verify pass, commit.
