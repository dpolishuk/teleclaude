# Unified Sessions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify Claude Code sessions between TeleClaude and terminal so sessions are visible and resumable in both interfaces.

**Architecture:** SDK manages session `.jsonl` files in `~/.claude/projects/`. SQLite becomes a metadata layer storing `telegram_user_id` → `session_id` mappings, costs, and timestamps. The `claude_session_id` UUID becomes the primary key, eliminating the redundant TeleClaude ID.

**Tech Stack:** Python 3.10+, SQLAlchemy async, python-telegram-bot v21, Claude Agent SDK

---

## Task 1: Simplify Session Model

**Files:**
- Modify: `src/storage/models.py:24-48`
- Test: `tests/test_unified_sessions.py` (create)

**Step 1: Write the failing test**

Create `tests/test_unified_sessions.py`:

```python
"""Test unified session model."""
import pytest
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
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py -v`
Expected: FAIL (session still has old fields)

**Step 3: Update Session model**

Modify `src/storage/models.py` - replace the Session class:

```python
class Session(Base):
    """Session model - maps telegram users to Claude sessions."""

    __tablename__ = "sessions"

    # Primary key is now the Claude session UUID
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        insert_default=lambda: datetime.now(timezone.utc),
    )
    last_active: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        insert_default=lambda: datetime.now(timezone.utc),
    )
    total_cost_usd: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, insert_default=0.0
    )

    def __init__(self, **kwargs):
        """Initialize with defaults."""
        kwargs.setdefault("total_cost_usd", 0.0)
        kwargs.setdefault("created_at", datetime.now(timezone.utc))
        kwargs.setdefault("last_active", datetime.now(timezone.utc))
        super().__init__(**kwargs)
```

Also remove the `SessionStatus` enum import and class since it's no longer used.

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/storage/models.py tests/test_unified_sessions.py
git commit -m "refactor: simplify Session model for unified sessions"
```

---

## Task 2: Update SessionRepository

**Files:**
- Modify: `src/storage/repository.py:12-122`
- Test: `tests/test_unified_sessions.py`

**Step 1: Write the failing test**

Add to `tests/test_unified_sessions.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock


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
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_repository_get_or_create_session -v`
Expected: FAIL (method doesn't exist)

**Step 3: Update SessionRepository**

Modify `src/storage/repository.py`:

```python
"""Data access repository."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Session, Usage, AuditLog


class SessionRepository:
    """Repository for session operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_or_create_session(
        self,
        session_id: str,
        telegram_user_id: int,
        project_path: str,
    ) -> Session:
        """Get existing session or create new one.

        This is the primary method for unified sessions - called when
        SDK returns a session_id.
        """
        session = await self.get_session(session_id)
        if session:
            session.last_active = datetime.now(timezone.utc)
            await self.db.flush()
            return session

        # Create new session with the SDK's session_id as primary key
        session = Session(
            id=session_id,
            telegram_user_id=telegram_user_id,
            project_path=project_path,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID (claude_session_id)."""
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_active_session_for_user(
        self, telegram_user_id: int
    ) -> Optional[Session]:
        """Get most recent session for user."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .order_by(Session.last_active.desc())
            .limit(1)
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

    async def list_sessions_for_project(
        self, telegram_user_id: int, project_path: str, limit: int = 10
    ) -> list[Session]:
        """List sessions for a specific project."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .where(Session.project_path == project_path)
            .order_by(Session.last_active.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_session(self, session: Session) -> None:
        """Update session last_active timestamp."""
        session.last_active = datetime.now(timezone.utc)
        await self.db.flush()

    async def add_cost(self, session_id: str, cost: float) -> None:
        """Add cost to session."""
        session = await self.get_session(session_id)
        if session:
            session.total_cost_usd += cost
            session.last_active = datetime.now(timezone.utc)
            await self.db.flush()

    async def get_session_ids_for_project(
        self, telegram_user_id: int, project_path: str
    ) -> set[str]:
        """Get set of session IDs owned by user for a project.

        Used to determine origin (Telegram vs Terminal) in unified list.
        """
        result = await self.db.execute(
            select(Session.id)
            .where(Session.telegram_user_id == telegram_user_id)
            .where(Session.project_path == project_path)
        )
        return {row[0] for row in result.all()}
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/storage/repository.py tests/test_unified_sessions.py
git commit -m "refactor: update SessionRepository for unified sessions"
```

---

## Task 3: Add Unified Session Scanner

**Files:**
- Modify: `src/claude/sessions.py`
- Test: `tests/test_unified_sessions.py`

**Step 1: Write the failing test**

Add to `tests/test_unified_sessions.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_unified_session_info_has_origin -v`
Expected: FAIL (class doesn't exist)

**Step 3: Add UnifiedSessionInfo dataclass**

Add to `src/claude/sessions.py` after the existing `SessionInfo` class:

```python
@dataclass
class UnifiedSessionInfo:
    """Session info with origin tracking for unified display."""

    session_id: str
    path: Path
    mtime: datetime
    preview: str
    origin: str  # "telegram" or "terminal"


def scan_unified_sessions(
    project_path: str,
    owned_session_ids: set[str],
    limit: int = 10,
) -> list[UnifiedSessionInfo]:
    """Scan sessions with origin detection.

    Args:
        project_path: Project directory path (e.g., "/root/work/teleclaude")
        owned_session_ids: Set of session IDs owned by current telegram user
        limit: Maximum sessions to return

    Returns:
        List of UnifiedSessionInfo sorted by mtime, newest first.
    """
    encoded = encode_project_path(project_path)
    projects_dir = Path.home() / ".claude" / "projects"
    project_dir = projects_dir / encoded

    if not project_dir.exists():
        return []

    # Find all .jsonl session files
    session_files = list(project_dir.glob("*.jsonl"))

    if not session_files:
        return []

    # Sort by mtime (newest first) and limit
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    session_files = session_files[:limit]

    sessions = []
    for session_file in session_files:
        session_id = session_file.stem
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        preview = parse_session_preview(session_file)

        # Determine origin based on ownership
        origin = "telegram" if session_id in owned_session_ids else "terminal"

        sessions.append(
            UnifiedSessionInfo(
                session_id=session_id,
                path=session_file,
                mtime=mtime,
                preview=preview,
                origin=origin,
            )
        )

    return sessions
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_unified_session_info_has_origin -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude/sessions.py tests/test_unified_sessions.py
git commit -m "feat: add unified session scanner with origin detection"
```

---

## Task 4: Update Keyboard Builder for Origin Icons

**Files:**
- Modify: `src/bot/keyboards.py:99-134`
- Test: `tests/test_unified_sessions.py`

**Step 1: Write the failing test**

Add to `tests/test_unified_sessions.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_unified_sessions_keyboard_shows_origin_icons -v`
Expected: FAIL (function doesn't exist)

**Step 3: Add unified keyboard builder**

Add to `src/bot/keyboards.py`:

```python
from src.claude.sessions import UnifiedSessionInfo


def build_unified_sessions_keyboard(
    sessions: list[UnifiedSessionInfo],
) -> InlineKeyboardMarkup:
    """Build unified session list keyboard with origin icons.

    Args:
        sessions: List of UnifiedSessionInfo from scan_unified_sessions()

    Returns:
        InlineKeyboardMarkup with origin icons and previews.
        Callback data pattern: select_session:<session_id>
    """
    buttons = []

    for session in sessions:
        relative = _format_relative_time(session.mtime)
        preview = session.preview

        # Origin icon
        origin_icon = "\U0001F4F1" if session.origin == "telegram" else "\U0001F4BB"

        # Build display: "📱 2h ago: message..."
        if preview:
            max_preview = TELEGRAM_BUTTON_TEXT_LIMIT - len(relative) - 6  # icon + ": "
            if len(preview) > max_preview:
                preview = preview[: max_preview - 1] + "..."
            display_text = f"{origin_icon} {relative}: \"{preview}\""
        else:
            display_text = f"{origin_icon} {relative}: (empty)"

        if len(display_text) > TELEGRAM_BUTTON_TEXT_LIMIT:
            display_text = display_text[:61] + "..."

        button = InlineKeyboardButton(
            text=display_text,
            callback_data=f"select_session:{session.session_id}",
        )
        buttons.append([button])

    return InlineKeyboardMarkup(buttons)
```

Also add the import at the top of the file.

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_unified_sessions_keyboard_shows_origin_icons -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/keyboards.py tests/test_unified_sessions.py
git commit -m "feat: add unified sessions keyboard with origin icons"
```

---

## Task 5: Update /sessions Handler

**Files:**
- Modify: `src/bot/handlers.py:249-279`
- Test: `tests/test_unified_sessions.py`

**Step 1: Write the failing test**

Add to `tests/test_unified_sessions.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_list_sessions_shows_unified_view -v`
Expected: FAIL (handler uses old approach)

**Step 3: Update list_sessions handler**

Modify `src/bot/handlers.py` - update the `list_sessions` function:

```python
async def list_sessions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /sessions command - show unified Claude Code sessions."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text(
            "No active project. Use /new to start."
        )
        return

    project_path = session.project_path
    user_id = update.effective_user.id

    # Get session IDs owned by this user (for origin detection)
    async with get_session() as db:
        repo = SessionRepository(db)
        owned_ids = await repo.get_session_ids_for_project(user_id, project_path)

    # Scan unified sessions from filesystem
    sessions = scan_unified_sessions(project_path, owned_ids)

    if not sessions:
        await update.message.reply_text(
            f"No sessions found for {project_path}"
        )
        return

    # Build keyboard with origin icons
    keyboard = build_unified_sessions_keyboard(sessions)

    project_name = project_path.split("/")[-1]
    await update.message.reply_text(
        f"\U0001F4CB Sessions for {project_name}\n\n"
        "\U0001F4F1 = Telegram  \U0001F4BB = Terminal",
        reply_markup=keyboard,
    )
```

Also add the imports at the top:

```python
from src.claude.sessions import scan_unified_sessions
from src.bot.keyboards import build_unified_sessions_keyboard
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_list_sessions_shows_unified_view -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handlers.py tests/test_unified_sessions.py
git commit -m "feat: update /sessions to show unified view with origin icons"
```

---

## Task 6: Update Session Selection Callback

**Files:**
- Modify: `src/bot/callbacks.py:366-396`
- Test: `tests/test_unified_sessions.py`

**Step 1: Write the failing test**

Add to `tests/test_unified_sessions.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_select_session_creates_record_for_terminal -v`
Expected: FAIL (handler uses old approach)

**Step 3: Update session selection callback**

Modify `src/bot/callbacks.py` - update `_handle_select_session`:

```python
async def _handle_select_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle session selection - create record if terminal session, then resume."""
    query = update.callback_query

    if not value:
        await query.edit_message_text("\u274c Invalid session selection.")
        return

    current_session = context.user_data.get("current_session")
    if not current_session:
        await query.edit_message_text("\u274c No active project. Use /new first.")
        return

    user_id = update.effective_user.id
    project_path = current_session.project_path

    # Get or create session record (claims ownership for terminal sessions)
    async with get_session() as db:
        repo = SessionRepository(db)
        session = await repo.get_or_create_session(
            session_id=value,
            telegram_user_id=user_id,
            project_path=project_path,
        )

    # Update current session in user_data
    context.user_data["current_session"] = session
    context.user_data["current_session_id"] = session.id

    logger.info(f"Session selected: {value[:20]}... for project {project_path}")

    await query.edit_message_text(
        f"\u2705 Session resumed!\n\n"
        f"\U0001F4C2 Project: {project_path}\n\n"
        "You can now continue chatting with Claude."
    )
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_select_session_creates_record_for_terminal -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/callbacks.py tests/test_unified_sessions.py
git commit -m "feat: session selection creates SQLite record for terminal sessions"
```

---

## Task 7: Update Lazy Session Creation in Streaming

**Files:**
- Modify: `src/bot/handlers.py:606-618`
- Test: `tests/test_unified_sessions.py`

**Step 1: Write the failing test**

Add to `tests/test_unified_sessions.py`:

```python
@pytest.mark.asyncio
async def test_result_message_creates_session_lazily():
    """ResultMessage with session_id creates SQLite record lazily."""
    from unittest.mock import AsyncMock, MagicMock, patch

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
```

**Step 2: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py::test_result_message_creates_session_lazily -v`
Expected: PASS (repository already has this method)

**Step 3: Update ResultMessage handling in _execute_claude_prompt**

Modify `src/bot/handlers.py` - update the ResultMessage handling section (around line 606-618):

```python
elif isinstance(message, ResultMessage):
    # Lazy session creation: create/update SQLite record when SDK returns session_id
    if message.session_id:
        logger.info(f"Got session_id from Claude: {message.session_id}")

        # Get project path from current session context
        project_path = session.project_path if session else None

        if project_path:
            async with get_session() as db:
                repo = SessionRepository(db)
                db_session = await repo.get_or_create_session(
                    session_id=message.session_id,
                    telegram_user_id=update.effective_user.id,
                    project_path=project_path,
                )
                # Update context with the database session
                context.user_data["current_session"] = db_session
                context.user_data["current_session_id"] = db_session.id

            logger.info(f"Session record created/updated: {message.session_id}")

        # Cache in user_data for persistence/change detection
        context.user_data["cached_claude_session_id"] = message.session_id

    # Update session cost
    if session and message.total_cost_usd:
        async with get_session() as db:
            repo = SessionRepository(db)
            await repo.add_cost(session.id, message.total_cost_usd)
```

**Step 4: Run all tests**

Run: `./venv/bin/python -m pytest tests/test_unified_sessions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handlers.py tests/test_unified_sessions.py
git commit -m "feat: lazy session creation from SDK ResultMessage"
```

---

## Task 8: Remove Old Session Creation

**Files:**
- Modify: `src/bot/handlers.py:633-670`
- Modify: `src/bot/callbacks.py:83-127`

**Step 1: Update _create_session to not create SQLite record**

The old `_create_session` created a SQLite record immediately. With lazy creation, we only need to set up the context for the first message.

Modify `src/bot/handlers.py` - update `_create_session`:

```python
async def _create_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project_path: str,
    project_name: str | None = None,
) -> None:
    """Set up context for a new session (lazy SQLite creation)."""
    # Create a temporary session object for context
    # SQLite record will be created lazily when SDK returns session_id
    from types import SimpleNamespace

    temp_session = SimpleNamespace(
        id=None,  # No ID yet - will be set from SDK
        project_path=project_path,
        project_name=project_name,
        total_cost_usd=0.0,
    )

    context.user_data["current_session"] = temp_session
    context.user_data["current_project_path"] = project_path

    # Refresh commands for this project
    registry = context.bot_data.get("command_registry")
    cmd_count = await registry.refresh(update.get_bot(), project_path=project_path)

    display_name = project_name or project_path

    # Get MCP server count
    mcp_manager = context.bot_data.get("mcp_manager")
    mcp_count = len(mcp_manager.config.get_enabled_servers()) if mcp_manager else 0
    mcp_msg = f"\n\U0001F50C {mcp_count} MCP server(s) enabled." if mcp_count > 0 else ""

    await update.message.reply_text(
        f"\u2705 Ready for new session in {display_name}\n"
        f"\U0001F4CB {cmd_count} Claude command(s) available.{mcp_msg}\n\n"
        "Send a message to start chatting with Claude."
    )
```

**Step 2: Update project selection callback similarly**

Modify `src/bot/callbacks.py` - update `_handle_project_select`:

```python
async def _handle_project_select(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle project selection callback."""
    query = update.callback_query
    config = context.bot_data.get("config")

    if value == "other":
        await query.edit_message_text(
            "\U0001F4C1 Send me the path to your project directory."
        )
        context.user_data["awaiting_path"] = True
        return

    if value and value in config.projects:
        project_path = config.projects[value]

        # Set up context for new session (lazy SQLite creation)
        from types import SimpleNamespace

        temp_session = SimpleNamespace(
            id=None,
            project_path=project_path,
            project_name=value,
            total_cost_usd=0.0,
        )
        context.user_data["current_session"] = temp_session
        context.user_data["current_project_path"] = project_path

        # Refresh commands for this project
        registry = context.bot_data.get("command_registry")
        cmd_count = await registry.refresh(query.get_bot(), project_path=project_path)

        await query.edit_message_text(
            f"\u2705 Ready for session in `{value}`\n\n"
            f"\U0001F4C2 Path: `{project_path}`\n"
            f"\U0001F4CB {cmd_count} Claude command(s) available.\n\n"
            "Send a message to chat with Claude."
        )
    else:
        await query.edit_message_text(f"\u274c Project not found: {value}")
```

**Step 3: Run all tests**

Run: `./venv/bin/python -m pytest tests/ -v --ignore=tests/test_formatting.py`
Expected: PASS (some tests may need updates for the new flow)

**Step 4: Commit**

```bash
git add src/bot/handlers.py src/bot/callbacks.py
git commit -m "refactor: remove eager session creation, use lazy approach"
```

---

## Task 9: Database Migration Script

**Files:**
- Create: `scripts/migrate_sessions.py`

**Step 1: Write migration script**

Create `scripts/migrate_sessions.py`:

```python
#!/usr/bin/env python3
"""Migrate sessions table to unified schema.

This script:
1. Renames claude_session_id to id for rows that have it
2. Deletes rows without claude_session_id (orphaned)
3. Drops removed columns
"""
import sqlite3
import sys
from pathlib import Path


def migrate(db_path: str) -> None:
    """Run migration on database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Migrating {db_path}...")

    # Check current schema
    cursor.execute("PRAGMA table_info(sessions)")
    columns = {row[1] for row in cursor.fetchall()}

    if "claude_session_id" not in columns:
        print("Already migrated (no claude_session_id column)")
        return

    # Count rows to migrate
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE claude_session_id IS NOT NULL")
    to_keep = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sessions WHERE claude_session_id IS NULL")
    to_delete = cursor.fetchone()[0]

    print(f"Sessions to migrate: {to_keep}")
    print(f"Orphaned sessions to delete: {to_delete}")

    # Create new table with simplified schema
    cursor.execute("""
        CREATE TABLE sessions_new (
            id TEXT PRIMARY KEY,
            telegram_user_id INTEGER NOT NULL,
            project_path TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            last_active TIMESTAMP NOT NULL,
            total_cost_usd REAL NOT NULL DEFAULT 0.0
        )
    """)

    # Migrate valid rows
    cursor.execute("""
        INSERT INTO sessions_new (id, telegram_user_id, project_path, created_at, last_active, total_cost_usd)
        SELECT claude_session_id, telegram_user_id, project_path, created_at,
               COALESCE(last_active, created_at), COALESCE(total_cost_usd, 0.0)
        FROM sessions
        WHERE claude_session_id IS NOT NULL
    """)

    # Drop old table and rename
    cursor.execute("DROP TABLE sessions")
    cursor.execute("ALTER TABLE sessions_new RENAME TO sessions")

    # Create index
    cursor.execute("CREATE INDEX ix_sessions_telegram_user_id ON sessions(telegram_user_id)")

    conn.commit()
    print(f"Migration complete! {to_keep} sessions migrated, {to_delete} orphaned deleted.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default path
        db_path = Path.home() / ".teleclaude" / "teleclaude.db"
    else:
        db_path = Path(sys.argv[1])

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    migrate(str(db_path))
```

**Step 2: Test migration script**

Run: `./venv/bin/python scripts/migrate_sessions.py`
Expected: Migration output showing rows processed

**Step 3: Commit**

```bash
git add scripts/migrate_sessions.py
git commit -m "feat: add database migration script for unified sessions"
```

---

## Task 10: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update project documentation**

Add to the "Key Features" section in `CLAUDE.md`:

```markdown
### Unified Sessions
- Sessions visible in both `claude --resume` and Telegram `/sessions`
- Origin icons: 📱 Telegram, 💻 Terminal
- Lazy session creation: SQLite record created when SDK returns session_id
- Single ID: claude_session_id is the primary key everywhere
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add unified sessions to CLAUDE.md"
```

---

## Task 11: Run Full Test Suite

**Step 1: Run all tests**

Run: `./venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

**Step 2: Run linting**

Run: `./venv/bin/ruff check src/ tests/`
Expected: No errors

**Step 3: Fix any issues found**

Address any test failures or linting errors.

**Step 4: Final commit**

```bash
git add .
git commit -m "chore: fix test and lint issues"
```

---

## Task 12: Manual Testing

**Step 1: Start fresh session in Telegram**

1. Send `/new` and select a project
2. Send a message to Claude
3. Check `~/.claude/projects/<project>/` for new `.jsonl` file
4. Verify session appears in Telegram `/sessions`

**Step 2: Resume from terminal**

1. Run `claude --resume` in terminal
2. Verify the Telegram session appears in the list
3. Continue the conversation
4. Go back to Telegram `/sessions` - should still see it

**Step 3: Resume terminal session from Telegram**

1. Start a session in terminal with `claude`
2. In Telegram, run `/sessions`
3. Session should appear with 💻 icon
4. Select it and continue conversation
5. Session should now show 📱 icon (claimed)

**Step 4: Restart bot and verify**

1. Restart the bot
2. Send `/start` - should restore session
3. Run `/sessions` - should show all sessions

---

Plan complete and saved to `docs/plans/2025-12-03-unified-sessions-plan.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
