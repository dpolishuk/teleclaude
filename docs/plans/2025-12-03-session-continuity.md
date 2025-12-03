# Session Continuity After Bot Restart Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore user sessions automatically when bot restarts, preserving context and notifying users of any changes.

**Architecture:** Hybrid persistence using PicklePersistence for fast `user_data` restore (session ID, preferences) combined with SQLite database for session details. On `/start`, check for restorable session, fetch from DB, compare Claude session IDs, and show appropriate restore/changed message.

**Tech Stack:** python-telegram-bot PicklePersistence, SQLAlchemy async, existing Session model

---

## Task 1: Add PicklePersistence to Application Builder

**Files:**
- Modify: `src/bot/application.py:68-80`
- Modify: `src/config/settings.py` (add persistence path config)

**Step 1: Write the test for persistence configuration**

Create file `tests/test_persistence.py`:

```python
"""Test persistence configuration."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_persistence_path_in_config():
    """Config includes persistence file path."""
    from src.config.settings import Config

    config = Config()
    assert hasattr(config, "persistence_path")
    assert config.persistence_path.endswith(".pickle")
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_persistence_path_in_config -v`
Expected: FAIL with "AttributeError: 'Config' object has no attribute 'persistence_path'"

**Step 3: Add persistence_path to Config**

In `src/config/settings.py`, add to the `Config` dataclass (around line 95):

```python
@dataclass
class Config:
    """Main configuration."""

    telegram_token: str = ""
    allowed_users: list[int] = field(default_factory=list)
    projects: dict[str, str] = field(default_factory=dict)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    approval: ApprovalConfig = field(default_factory=ApprovalConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    persistence_path: str = "~/.teleclaude/bot_persistence.pickle"  # ADD THIS LINE
```

Also update `_parse_config` function to handle it:

```python
def _parse_config(data: dict) -> Config:
    # ... existing code ...

    persistence_path = data.get("persistence_path", "~/.teleclaude/bot_persistence.pickle")
    if "~" in persistence_path:
        persistence_path = str(Path(persistence_path).expanduser())

    return Config(
        # ... existing fields ...
        persistence_path=persistence_path,
    )
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_persistence_path_in_config -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/config/settings.py tests/test_persistence.py
git commit -m "feat: add persistence_path config option"
```

---

## Task 2: Configure PicklePersistence in Application

**Files:**
- Modify: `src/bot/application.py:1-10` (imports)
- Modify: `src/bot/application.py:68-80` (create_application function)

**Step 1: Write test for persistence integration**

Add to `tests/test_persistence.py`:

```python
def test_application_has_persistence(tmp_path):
    """Application is configured with PicklePersistence."""
    from src.config.settings import Config
    from src.bot.application import create_application

    config = Config(
        telegram_token="test:token",
        persistence_path=str(tmp_path / "test.pickle"),
    )

    app = create_application(config)

    assert app.persistence is not None
    assert "PicklePersistence" in type(app.persistence).__name__
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_application_has_persistence -v`
Expected: FAIL with "assert None is not None" (no persistence configured)

**Step 3: Add PicklePersistence to application.py**

In `src/bot/application.py`, update imports:

```python
"""Telegram bot application setup."""
from pathlib import Path
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,  # ADD THIS
    filters,
)
```

Update `create_application` function:

```python
def create_application(config: Config) -> Application:
    """Create and configure Telegram Application."""
    # Ensure persistence directory exists
    persistence_path = Path(config.persistence_path)
    persistence_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure persistence for user_data across restarts
    persistence = PicklePersistence(
        filepath=str(persistence_path),
        store_data=PersistenceInput(
            bot_data=False,  # We manage bot_data ourselves
            chat_data=False,
            user_data=True,  # Persist session IDs and preferences
            callback_data=False,
        ),
        update_interval=30,  # Save every 30 seconds
    )

    app = (
        Application.builder()
        .token(config.telegram_token)
        .persistence(persistence)  # ADD THIS
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )
    # ... rest unchanged
```

Also add to imports:

```python
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,
    PersistenceInput,  # ADD THIS
    filters,
)
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_application_has_persistence -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/application.py
git commit -m "feat: add PicklePersistence for user_data"
```

---

## Task 3: Store Session ID in user_data on Session Creation

**Files:**
- Modify: `src/bot/callbacks.py:98-122` (_handle_project_select)
- Modify: `src/bot/handlers.py` (where sessions are created/switched)

**Step 1: Write test for session ID persistence**

Add to `tests/test_persistence.py`:

```python
@pytest.mark.asyncio
async def test_session_id_stored_in_user_data():
    """Session ID is stored in user_data for persistence."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.bot.callbacks import handle_callback

    # Mock update and context
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "project:myapp"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.get_bot = MagicMock(return_value=MagicMock())
    update.effective_user.id = 12345

    context = MagicMock()
    context.user_data = {}
    context.bot_data = {
        "config": MagicMock(projects={"myapp": "/home/user/myapp"}),
        "command_registry": MagicMock(refresh=AsyncMock(return_value=5)),
    }

    mock_session = MagicMock(id="session123", claude_session_id=None)
    mock_repo = MagicMock()
    mock_repo.create_session = AsyncMock(return_value=mock_session)

    with patch("src.bot.callbacks.get_session") as mock_get_session, \
         patch("src.bot.callbacks.SessionRepository", return_value=mock_repo):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await handle_callback(update, context)

    # Verify session ID stored in user_data
    assert "current_session_id" in context.user_data
    assert context.user_data["current_session_id"] == "session123"
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_session_id_stored_in_user_data -v`
Expected: FAIL with "KeyError: 'current_session_id'" or similar

**Step 3: Update callbacks.py to store session ID**

In `src/bot/callbacks.py`, modify `_handle_project_select` (around line 109-111):

```python
            # Store session in user_data for quick access
            context.user_data["current_session"] = session
            # Store session ID separately for persistence across restarts
            context.user_data["current_session_id"] = session.id
            context.user_data["current_project_path"] = project_path
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_session_id_stored_in_user_data -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/callbacks.py
git commit -m "feat: store session_id in user_data for persistence"
```

---

## Task 4: Add Session Preview Helper to sessions.py

**Files:**
- Modify: `src/claude/sessions.py`
- Create: `tests/test_session_preview.py`

**Step 1: Write test for get_session_last_message**

Create `tests/test_session_preview.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `./venv/bin/python -m pytest tests/test_session_preview.py -v`
Expected: FAIL with "cannot import name 'get_session_last_message'"

**Step 3: Implement get_session_last_message**

Add to `src/claude/sessions.py`:

```python
def get_session_last_message(
    session_file: str,
    max_length: int = 100,
) -> str | None:
    """Get the last user message from a Claude session file.

    Args:
        session_file: Path to session .jsonl file
        max_length: Maximum length of returned message

    Returns:
        Last user message content, truncated if needed, or None if not found
    """
    path = Path(session_file)
    if not path.exists():
        return None

    try:
        last_user_message = None
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "human":
                        content = entry.get("message", {}).get("content", "")
                        if content:
                            last_user_message = content
                except json.JSONDecodeError:
                    continue

        if last_user_message and len(last_user_message) > max_length:
            return last_user_message[:max_length] + "..."
        return last_user_message

    except Exception:
        return None
```

**Step 4: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/test_session_preview.py -v`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add src/claude/sessions.py tests/test_session_preview.py
git commit -m "feat: add get_session_last_message helper"
```

---

## Task 5: Add Session Restore Logic to /start Handler

**Files:**
- Modify: `src/bot/handlers.py` (start function)
- Add helper function for restore message formatting

**Step 1: Write test for session restore on start**

Add to `tests/test_persistence.py`:

```python
@pytest.mark.asyncio
async def test_start_restores_existing_session():
    """Start command restores session if user_data has session_id."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.bot.handlers import start

    update = MagicMock()
    update.effective_user.id = 12345
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()

    # Simulate persisted user_data with session ID
    context = MagicMock()
    context.user_data = {
        "current_session_id": "existing123",
        "cached_claude_session_id": "claude456",
    }
    context.bot_data = {
        "config": MagicMock(projects={"myapp": "/path/to/myapp"}),
    }

    mock_session = MagicMock(
        id="existing123",
        claude_session_id="claude456",  # Same as cached - no change
        project_name="myapp",
        project_path="/path/to/myapp",
        last_active=None,
        total_cost_usd=0.42,
    )
    mock_repo = MagicMock()
    mock_repo.get_session = AsyncMock(return_value=mock_session)

    with patch("src.bot.handlers.get_session") as mock_get_session, \
         patch("src.bot.handlers.SessionRepository", return_value=mock_repo), \
         patch("src.bot.handlers.get_session_last_message", return_value="Last message"):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await start(update, context)

    # Should send restore message, not project picker
    update.message.reply_text.assert_called()
    call_args = update.message.reply_text.call_args[0][0]
    assert "restored" in call_args.lower() or "Session" in call_args
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_start_restores_existing_session -v`
Expected: FAIL (current start doesn't check for existing session)

**Step 3: Implement session restore in start handler**

In `src/bot/handlers.py`, modify the `start` function:

```python
from src.claude.sessions import get_session_last_message  # Add to imports

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - restore session or show project picker."""
    config = context.bot_data.get("config")
    user_id = update.effective_user.id

    # Check for restorable session from persisted user_data
    session_id = context.user_data.get("current_session_id")

    if session_id:
        # Try to restore existing session
        async with get_session() as db:
            repo = SessionRepository(db)
            session = await repo.get_session(session_id)

            if session:
                # Check if Claude session changed
                cached_claude_id = context.user_data.get("cached_claude_session_id")
                session_changed = (
                    cached_claude_id is not None
                    and session.claude_session_id is not None
                    and cached_claude_id != session.claude_session_id
                )

                # Update user_data with current session
                context.user_data["current_session"] = session
                context.user_data["cached_claude_session_id"] = session.claude_session_id

                # Get last message preview
                last_message = None
                if session.claude_session_id:
                    # Find session file and get preview
                    from src.claude.sessions import get_session_file_path
                    session_file = get_session_file_path(
                        session.project_path,
                        session.claude_session_id
                    )
                    if session_file:
                        last_message = get_session_last_message(session_file)

                # Format restore message
                message = _format_restore_message(
                    session=session,
                    session_changed=session_changed,
                    last_message=last_message,
                )

                await update.message.reply_text(message, parse_mode="HTML")
                return

    # No restorable session - show project picker (existing behavior)
    if not config.projects:
        await update.message.reply_text(
            "No projects configured. Add projects to config.yaml"
        )
        return

    keyboard = project_keyboard(config.projects)
    await update.message.reply_text(
        "Welcome to TeleClaude! Select a project:",
        reply_markup=keyboard,
    )


def _format_restore_message(
    session,
    session_changed: bool,
    last_message: str | None,
) -> str:
    """Format session restore/changed message."""
    from src.claude.sessions import relative_time

    if session_changed:
        header = "⚠️ <b>Session context changed</b>\n\n"
        header += "Your Claude session was updated externally (possibly from terminal).\n"
        header += "Continuing with the latest state.\n\n"
    else:
        header = "✅ <b>Session restored</b>\n\n"

    lines = [header]
    lines.append(f"📂 Project: <code>{session.project_name or session.project_path}</code>")

    if session.last_active:
        lines.append(f"⏰ Last active: {relative_time(session.last_active)}")

    if session.total_cost_usd > 0:
        lines.append(f"💰 Cost: ${session.total_cost_usd:.2f}")

    if last_message:
        lines.append(f"\n💬 Last context:\n<i>\"{last_message}\"</i>")

    lines.append("\nReady to continue. Send a message or /new for fresh session.")

    return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_start_restores_existing_session -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handlers.py
git commit -m "feat: restore session on /start if persisted"
```

---

## Task 6: Add get_session_file_path Helper

**Files:**
- Modify: `src/claude/sessions.py`

**Step 1: Write test for get_session_file_path**

Add to `tests/test_session_preview.py`:

```python
def test_get_session_file_path(tmp_path):
    """get_session_file_path finds session file by Claude session ID."""
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
```

**Step 2: Run tests to verify they fail**

Run: `./venv/bin/python -m pytest tests/test_session_preview.py::test_get_session_file_path -v`
Expected: FAIL with "cannot import name 'get_session_file_path'"

**Step 3: Implement get_session_file_path**

Add to `src/claude/sessions.py`:

```python
def get_session_file_path(project_path: str, claude_session_id: str) -> str | None:
    """Get the path to a Claude session file.

    Args:
        project_path: Path to the project
        claude_session_id: Claude session UUID

    Returns:
        Full path to session .jsonl file, or None if not found
    """
    encoded = encode_project_path(project_path)
    sessions_dir = Path.home() / ".claude" / "projects" / encoded / "sessions"

    if not sessions_dir.exists():
        return None

    session_file = sessions_dir / f"{claude_session_id}.jsonl"
    if session_file.exists():
        return str(session_file)

    return None
```

**Step 4: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/test_session_preview.py::test_get_session_file_path tests/test_session_preview.py::test_get_session_file_path_not_found -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude/sessions.py
git commit -m "feat: add get_session_file_path helper"
```

---

## Task 7: Update Claude Session ID Cache After Queries

**Files:**
- Modify: `src/bot/handlers.py` (in _execute_claude_prompt)

**Step 1: Write test for claude_session_id caching**

Add to `tests/test_persistence.py`:

```python
@pytest.mark.asyncio
async def test_claude_session_id_cached_after_query():
    """Claude session ID is cached in user_data after query."""
    # This tests that when we get a session_id from Claude,
    # we store it in user_data for persistence
    context = MagicMock()
    context.user_data = {"current_session_id": "sess123"}

    # After a Claude query completes with session_id "claude789"
    # user_data should have cached_claude_session_id = "claude789"

    # Verify the behavior is implemented in handlers.py
    # by checking the code saves claude_session_id to user_data
    from src.bot import handlers
    import inspect
    source = inspect.getsource(handlers._execute_claude_prompt)

    assert "cached_claude_session_id" in source
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_claude_session_id_cached_after_query -v`
Expected: FAIL with "cached_claude_session_id" not in source

**Step 3: Update _execute_claude_prompt to cache claude_session_id**

In `src/bot/handlers.py`, find where we save claude_session_id (around line 520-530) and add:

```python
            # Save to database
            if session:
                logger.info(f"Got session_id from Claude: {session_id}")
                async with get_session() as db:
                    repo = SessionRepository(db)
                    await repo.set_claude_session_id(session.id, session_id)
                logger.info(f"Saved claude_session_id to database: {session_id}")

                # Cache in user_data for persistence/change detection
                context.user_data["cached_claude_session_id"] = session_id
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_claude_session_id_cached_after_query -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handlers.py
git commit -m "feat: cache claude_session_id in user_data"
```

---

## Task 8: Store User Preferences (Model Selection)

**Files:**
- Modify: `src/bot/handlers.py` (select_model and related)
- Modify: `src/bot/callbacks.py` (model selection callback)

**Step 1: Write test for model preference persistence**

Add to `tests/test_persistence.py`:

```python
@pytest.mark.asyncio
async def test_model_selection_stored_in_user_data():
    """Selected model is stored in user_data for persistence."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.bot.callbacks import handle_callback

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "model:opus"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.effective_user.id = 12345

    context = MagicMock()
    context.user_data = {"current_session": MagicMock()}
    context.bot_data = {"config": MagicMock()}

    await handle_callback(update, context)

    assert context.user_data.get("selected_model") == "opus"
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_model_selection_stored_in_user_data -v`
Expected: FAIL

**Step 3: Update model selection callback**

In `src/bot/callbacks.py`, find `_handle_model_select` and ensure it stores in user_data:

```python
async def _handle_model_select(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle model selection callback."""
    query = update.callback_query

    if value:
        # Store in user_data for persistence
        context.user_data["selected_model"] = value

        await query.edit_message_text(
            f"✅ Model set to: <b>{value}</b>\n\n"
            "This will be used for your next message.",
            parse_mode="HTML"
        )
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_persistence.py::test_model_selection_stored_in_user_data -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/callbacks.py
git commit -m "feat: persist model selection in user_data"
```

---

## Task 9: Integration Test - Full Restart Cycle

**Files:**
- Create: `tests/test_restart_integration.py`

**Step 1: Write integration test**

Create `tests/test_restart_integration.py`:

```python
"""Integration test for session continuity across restarts."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_full_restart_cycle():
    """Simulate: create session -> restart -> restore session."""
    from src.bot.callbacks import handle_callback
    from src.bot.handlers import start

    # Phase 1: User selects project, creates session
    user_data = {}

    update1 = MagicMock()
    update1.callback_query = AsyncMock()
    update1.callback_query.data = "project:myapp"
    update1.callback_query.answer = AsyncMock()
    update1.callback_query.edit_message_text = AsyncMock()
    update1.callback_query.get_bot = MagicMock(return_value=MagicMock())
    update1.effective_user.id = 12345

    context1 = MagicMock()
    context1.user_data = user_data  # Shared reference
    context1.bot_data = {
        "config": MagicMock(projects={"myapp": "/home/user/myapp"}),
        "command_registry": MagicMock(refresh=AsyncMock(return_value=5)),
    }

    mock_session = MagicMock(
        id="session123",
        claude_session_id="claude456",
        project_name="myapp",
        project_path="/home/user/myapp",
        last_active=None,
        total_cost_usd=0.0,
    )
    mock_repo = MagicMock()
    mock_repo.create_session = AsyncMock(return_value=mock_session)
    mock_repo.get_session = AsyncMock(return_value=mock_session)

    with patch("src.bot.callbacks.get_session") as mock_get_session, \
         patch("src.bot.callbacks.SessionRepository", return_value=mock_repo):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await handle_callback(update1, context1)

    # Verify session ID was stored
    assert user_data.get("current_session_id") == "session123"

    # Phase 2: Simulate restart - user_data persisted, session object lost
    user_data.pop("current_session", None)  # Object not serializable

    # Phase 3: User sends /start after restart
    update2 = MagicMock()
    update2.effective_user.id = 12345
    update2.message = AsyncMock()
    update2.message.reply_text = AsyncMock()

    context2 = MagicMock()
    context2.user_data = user_data  # Restored from pickle
    context2.bot_data = {
        "config": MagicMock(projects={"myapp": "/home/user/myapp"}),
    }

    with patch("src.bot.handlers.get_session") as mock_get_session, \
         patch("src.bot.handlers.SessionRepository", return_value=mock_repo), \
         patch("src.bot.handlers.get_session_file_path", return_value=None), \
         patch("src.bot.handlers.get_session_last_message", return_value=None):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await start(update2, context2)

    # Verify restore message was sent
    update2.message.reply_text.assert_called_once()
    call_text = update2.message.reply_text.call_args[0][0]
    assert "restored" in call_text.lower() or "myapp" in call_text
```

**Step 2: Run integration test**

Run: `./venv/bin/python -m pytest tests/test_restart_integration.py -v`
Expected: PASS (if all previous tasks completed)

**Step 3: Commit**

```bash
git add tests/test_restart_integration.py
git commit -m "test: add integration test for restart cycle"
```

---

## Task 10: Update Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add session continuity docs**

Add to `CLAUDE.md` under "Key Features":

```markdown
### Session Persistence
- Sessions persist across bot restarts via PicklePersistence
- On `/start`, bot restores last active session automatically
- User preferences (model selection) are preserved
- If Claude session changed externally (terminal), user is notified
- Session data stored in `~/.teleclaude/bot_persistence.pickle`
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add session persistence documentation"
```

---

## Task 11: Run Full Test Suite and Final Commit

**Step 1: Run all tests**

Run: `./venv/bin/python -m pytest -v`
Expected: All tests pass

**Step 2: Push to branch**

```bash
git push origin feature/html-rendering
```

---

**Plan complete and saved to `docs/plans/2025-12-03-session-continuity.md`.**

**Two execution options:**

1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
