# Claude Commands Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable TeleClaude to discover and execute Claude Code slash commands from `.claude/commands/*.md` files, displayed in Telegram's native `/` menu.

**Architecture:** New `src/commands/` module handles discovery, parsing, and registry. Commands are scanned from personal (`~/.claude/commands/`) and project directories, merged with project priority. Telegram menu updated via `set_my_commands()` when sessions change.

**Tech Stack:** Python 3.10+, python-telegram-bot v21, PyYAML (already installed), dataclasses

---

### Task 1: ClaudeCommand Model

**Files:**
- Create: `src/commands/__init__.py`
- Create: `src/commands/models.py`
- Test: `tests/test_commands.py`

**Step 1: Write the failing test**

Create `tests/test_commands.py`:

```python
"""Test Claude commands module."""
import pytest
from src.commands.models import ClaudeCommand


def test_claude_command_creation():
    """ClaudeCommand can be created with all fields."""
    cmd = ClaudeCommand(
        name="fix-bug",
        description="Fix a bug in the code",
        prompt="Fix this bug: $ARGUMENTS",
        needs_args=True,
        source="project",
    )
    assert cmd.name == "fix-bug"
    assert cmd.description == "Fix a bug in the code"
    assert cmd.prompt == "Fix this bug: $ARGUMENTS"
    assert cmd.needs_args is True
    assert cmd.source == "project"


def test_claude_command_defaults():
    """ClaudeCommand has sensible defaults."""
    cmd = ClaudeCommand(
        name="review",
        description="Review code",
        prompt="Review this code",
    )
    assert cmd.needs_args is False
    assert cmd.source == "personal"
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_commands.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.commands'"

**Step 3: Create the module structure**

Create `src/commands/__init__.py`:

```python
"""Claude commands integration."""
from .models import ClaudeCommand

__all__ = ["ClaudeCommand"]
```

Create `src/commands/models.py`:

```python
"""Data models for Claude commands."""
from dataclasses import dataclass, field


@dataclass
class ClaudeCommand:
    """Represents a Claude slash command from .claude/commands/*.md."""

    name: str
    description: str
    prompt: str
    needs_args: bool = False
    source: str = "personal"
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_commands.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/commands/ tests/test_commands.py
git commit -m "feat(commands): add ClaudeCommand model"
```

---

### Task 2: Command File Parser

**Files:**
- Modify: `src/commands/__init__.py`
- Create: `src/commands/discovery.py`
- Modify: `tests/test_commands.py`

**Step 1: Write the failing test**

Add to `tests/test_commands.py`:

```python
from src.commands.discovery import parse_command_file
from pathlib import Path


def test_parse_command_file_simple(tmp_path):
    """Parse command file without frontmatter."""
    cmd_file = tmp_path / "review.md"
    cmd_file.write_text("Review this code for bugs and improvements.")

    cmd = parse_command_file(cmd_file)

    assert cmd.name == "review"
    assert cmd.prompt == "Review this code for bugs and improvements."
    assert cmd.description == "Review this code for bugs and improvements."
    assert cmd.needs_args is False


def test_parse_command_file_with_frontmatter(tmp_path):
    """Parse command file with YAML frontmatter."""
    cmd_file = tmp_path / "fix-bug.md"
    cmd_file.write_text("""---
description: Fix a specific bug
allowed-tools: Bash(git:*), Read
---
Fix this bug: $ARGUMENTS
""")

    cmd = parse_command_file(cmd_file)

    assert cmd.name == "fix-bug"
    assert cmd.description == "Fix a specific bug"
    assert cmd.prompt == "Fix this bug: $ARGUMENTS"
    assert cmd.needs_args is True


def test_parse_command_file_with_positional_args(tmp_path):
    """Parse command file with $1, $2 placeholders."""
    cmd_file = tmp_path / "rename.md"
    cmd_file.write_text("Rename $1 to $2 in all files.")

    cmd = parse_command_file(cmd_file)

    assert cmd.needs_args is True


def test_parse_command_file_truncates_long_description(tmp_path):
    """Long descriptions are truncated to 256 chars."""
    cmd_file = tmp_path / "long.md"
    long_desc = "A" * 300
    cmd_file.write_text(f"""---
description: {long_desc}
---
Do something.
""")

    cmd = parse_command_file(cmd_file)

    assert len(cmd.description) <= 256
    assert cmd.description.endswith("...")
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_commands.py::test_parse_command_file_simple -v`
Expected: FAIL with "cannot import name 'parse_command_file'"

**Step 3: Write the implementation**

Create `src/commands/discovery.py`:

```python
"""Discover and parse Claude command files."""
import re
from pathlib import Path

import yaml

from .models import ClaudeCommand


def parse_command_file(path: Path, source: str = "personal") -> ClaudeCommand:
    """Parse a .md command file into a ClaudeCommand.

    Args:
        path: Path to the .md file.
        source: Where command came from ("personal" or "project").

    Returns:
        Parsed ClaudeCommand.
    """
    content = path.read_text()
    name = path.stem  # filename without extension

    # Parse frontmatter if present
    frontmatter = {}
    prompt = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                pass  # Invalid YAML, skip frontmatter
            prompt = parts[2].strip()

    # Get description from frontmatter or first line of prompt
    description = frontmatter.get("description", "")
    if not description:
        first_line = prompt.split("\n")[0].strip()
        description = first_line[:256] if first_line else name

    # Truncate description to Telegram limit
    if len(description) > 256:
        description = description[:253] + "..."

    # Check if command needs arguments
    needs_args = bool(
        re.search(r"\$ARGUMENTS|\$[1-9]", prompt)
    )

    return ClaudeCommand(
        name=name,
        description=description,
        prompt=prompt,
        needs_args=needs_args,
        source=source,
    )
```

Update `src/commands/__init__.py`:

```python
"""Claude commands integration."""
from .models import ClaudeCommand
from .discovery import parse_command_file

__all__ = ["ClaudeCommand", "parse_command_file"]
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_commands.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/commands/
git commit -m "feat(commands): add command file parser"
```

---

### Task 3: Command Directory Scanner

**Files:**
- Modify: `src/commands/discovery.py`
- Modify: `src/commands/__init__.py`
- Modify: `tests/test_commands.py`

**Step 1: Write the failing test**

Add to `tests/test_commands.py`:

```python
import os
from src.commands.discovery import scan_commands


def test_scan_commands_empty_dirs(tmp_path, monkeypatch):
    """Returns empty list when no command dirs exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    commands = scan_commands(project_path=str(tmp_path / "nonexistent"))

    assert commands == []


def test_scan_commands_personal_only(tmp_path, monkeypatch):
    """Scans personal commands from ~/.claude/commands/."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    cmd_dir = home / ".claude" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "review.md").write_text("Review code.")
    (cmd_dir / "test.md").write_text("Run tests.")

    commands = scan_commands(project_path=None)

    assert len(commands) == 2
    names = {c.name for c in commands}
    assert names == {"review", "test"}
    assert all(c.source == "personal" for c in commands)


def test_scan_commands_project_overrides_personal(tmp_path, monkeypatch):
    """Project commands override personal commands with same name."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    # Personal command
    personal_dir = home / ".claude" / "commands"
    personal_dir.mkdir(parents=True)
    (personal_dir / "review.md").write_text("Personal review.")

    # Project command with same name
    project = tmp_path / "myproject"
    project_dir = project / ".claude" / "commands"
    project_dir.mkdir(parents=True)
    (project_dir / "review.md").write_text("Project review.")

    commands = scan_commands(project_path=str(project))

    assert len(commands) == 1
    assert commands[0].name == "review"
    assert commands[0].prompt == "Project review."
    assert commands[0].source == "project"


def test_scan_commands_merges_both(tmp_path, monkeypatch):
    """Merges personal and project commands."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    # Personal commands
    personal_dir = home / ".claude" / "commands"
    personal_dir.mkdir(parents=True)
    (personal_dir / "personal-cmd.md").write_text("Personal only.")

    # Project commands
    project = tmp_path / "myproject"
    project_dir = project / ".claude" / "commands"
    project_dir.mkdir(parents=True)
    (project_dir / "project-cmd.md").write_text("Project only.")

    commands = scan_commands(project_path=str(project))

    assert len(commands) == 2
    names = {c.name for c in commands}
    assert names == {"personal-cmd", "project-cmd"}
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_commands.py::test_scan_commands_empty_dirs -v`
Expected: FAIL with "cannot import name 'scan_commands'"

**Step 3: Write the implementation**

Add to `src/commands/discovery.py`:

```python
import logging

logger = logging.getLogger(__name__)


def scan_commands(project_path: str | None = None) -> list[ClaudeCommand]:
    """Scan personal and project directories for commands.

    Personal commands from ~/.claude/commands/ are loaded first,
    then project commands override any with the same name.

    Args:
        project_path: Optional project directory path.

    Returns:
        List of discovered commands, with project commands taking priority.
    """
    commands: dict[str, ClaudeCommand] = {}

    # 1. Scan personal commands
    personal_dir = Path.home() / ".claude" / "commands"
    if personal_dir.is_dir():
        for md_file in personal_dir.glob("*.md"):
            try:
                cmd = parse_command_file(md_file, source="personal")
                commands[cmd.name] = cmd
            except Exception as e:
                logger.warning(f"Failed to parse {md_file}: {e}")

    # 2. Scan project commands (override personal)
    if project_path:
        project_dir = Path(project_path) / ".claude" / "commands"
        if project_dir.is_dir():
            for md_file in project_dir.glob("*.md"):
                try:
                    cmd = parse_command_file(md_file, source="project")
                    commands[cmd.name] = cmd
                except Exception as e:
                    logger.warning(f"Failed to parse {md_file}: {e}")

    return list(commands.values())
```

Update `src/commands/__init__.py`:

```python
"""Claude commands integration."""
from .models import ClaudeCommand
from .discovery import parse_command_file, scan_commands

__all__ = ["ClaudeCommand", "parse_command_file", "scan_commands"]
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_commands.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/commands/
git commit -m "feat(commands): add directory scanner with merge logic"
```

---

### Task 4: Command Registry

**Files:**
- Create: `src/commands/registry.py`
- Modify: `src/commands/__init__.py`
- Modify: `tests/test_commands.py`

**Step 1: Write the failing test**

Add to `tests/test_commands.py`:

```python
from src.commands.registry import CommandRegistry


def test_registry_get_command():
    """Registry returns command by name."""
    registry = CommandRegistry()
    cmd = ClaudeCommand(name="test", description="Test", prompt="Test prompt")
    registry._commands = {"test": cmd}

    result = registry.get("test")

    assert result == cmd


def test_registry_get_unknown_returns_none():
    """Registry returns None for unknown command."""
    registry = CommandRegistry()

    result = registry.get("unknown")

    assert result is None


def test_registry_substitute_args_simple():
    """Substitutes $ARGUMENTS in prompt."""
    registry = CommandRegistry()
    cmd = ClaudeCommand(
        name="fix",
        description="Fix bug",
        prompt="Fix this bug: $ARGUMENTS",
        needs_args=True,
    )

    result = registry.substitute_args(cmd, "login is broken")

    assert result == "Fix this bug: login is broken"


def test_registry_substitute_args_positional():
    """Substitutes $1, $2 in prompt."""
    registry = CommandRegistry()
    cmd = ClaudeCommand(
        name="rename",
        description="Rename",
        prompt="Rename $1 to $2",
        needs_args=True,
    )

    result = registry.substitute_args(cmd, "old_name new_name")

    assert result == "Rename old_name to new_name"


def test_registry_builtin_commands():
    """Registry provides list of built-in command names."""
    registry = CommandRegistry()

    builtins = registry.builtin_names

    assert "new" in builtins
    assert "help" in builtins
    assert "cancel" in builtins
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_commands.py::test_registry_get_command -v`
Expected: FAIL with "cannot import name 'CommandRegistry'"

**Step 3: Write the implementation**

Create `src/commands/registry.py`:

```python
"""Command registry for storing and managing commands."""
import logging
import re

from telegram import Bot, BotCommand

from .models import ClaudeCommand
from .discovery import scan_commands

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Stores and manages Claude commands."""

    # Built-in TeleClaude commands (cannot be overridden)
    BUILTIN_COMMANDS = [
        ("start", "Start the bot"),
        ("new", "Start new session"),
        ("continue", "Resume last session"),
        ("sessions", "List all sessions"),
        ("switch", "Switch to session"),
        ("help", "Show help"),
        ("cancel", "Stop current operation"),
        ("cost", "Show usage costs"),
        ("cd", "Change directory"),
        ("ls", "List directory"),
        ("pwd", "Show current directory"),
        ("git", "Git operations"),
        ("export", "Export session"),
        ("refresh", "Rescan Claude commands"),
    ]

    def __init__(self):
        self._commands: dict[str, ClaudeCommand] = {}

    @property
    def builtin_names(self) -> set[str]:
        """Get set of built-in command names."""
        return {name for name, _ in self.BUILTIN_COMMANDS}

    @property
    def commands(self) -> list[ClaudeCommand]:
        """Get all registered commands."""
        return list(self._commands.values())

    def get(self, name: str) -> ClaudeCommand | None:
        """Get command by name."""
        return self._commands.get(name)

    def substitute_args(self, cmd: ClaudeCommand, args: str) -> str:
        """Substitute arguments into command prompt.

        Handles both $ARGUMENTS (all args) and $1, $2, etc. (positional).

        Args:
            cmd: The command to substitute into.
            args: User-provided arguments string.

        Returns:
            Prompt with arguments substituted.
        """
        prompt = cmd.prompt

        # Substitute $ARGUMENTS with full args string
        prompt = prompt.replace("$ARGUMENTS", args)

        # Substitute positional args $1, $2, etc.
        parts = args.split()
        for i, part in enumerate(parts, start=1):
            prompt = prompt.replace(f"${i}", part)

        return prompt

    async def refresh(self, bot: Bot, project_path: str | None = None) -> int:
        """Rescan commands and update Telegram menu.

        Args:
            bot: Telegram bot instance.
            project_path: Optional project directory.

        Returns:
            Number of Claude commands loaded.
        """
        # Scan directories
        discovered = scan_commands(project_path)

        # Filter out conflicts with built-in commands
        self._commands.clear()
        for cmd in discovered:
            if cmd.name in self.builtin_names:
                logger.warning(
                    f"Skipping command '{cmd.name}' - conflicts with built-in"
                )
                continue
            self._commands[cmd.name] = cmd

        # Build Telegram command list
        telegram_commands = [
            BotCommand(name, desc) for name, desc in self.BUILTIN_COMMANDS
        ]

        # Add Claude commands (respect Telegram's 100 command limit)
        remaining_slots = 100 - len(telegram_commands)
        claude_cmds = list(self._commands.values())[:remaining_slots]

        if len(self._commands) > remaining_slots:
            logger.warning(
                f"Too many commands ({len(self._commands)}), "
                f"truncated to {remaining_slots}"
            )

        for cmd in claude_cmds:
            telegram_commands.append(BotCommand(cmd.name, cmd.description))

        # Update Telegram menu
        await bot.set_my_commands(telegram_commands)

        return len(self._commands)
```

Update `src/commands/__init__.py`:

```python
"""Claude commands integration."""
from .models import ClaudeCommand
from .discovery import parse_command_file, scan_commands
from .registry import CommandRegistry

__all__ = ["ClaudeCommand", "parse_command_file", "scan_commands", "CommandRegistry"]
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_commands.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/commands/
git commit -m "feat(commands): add CommandRegistry with Telegram integration"
```

---

### Task 5: Integrate Registry into Application

**Files:**
- Modify: `src/bot/application.py`
- Modify: `tests/test_application.py`

**Step 1: Write the failing test**

Add to `tests/test_application.py`:

```python
def test_create_application_has_command_registry():
    """Application has CommandRegistry in bot_data."""
    from src.commands import CommandRegistry

    config = MagicMock()
    config.telegram_token = "test_token"
    config.allowed_users = [123]

    with patch("src.bot.application.Application") as mock_app_class:
        mock_builder = MagicMock()
        mock_app = MagicMock()
        mock_builder.token.return_value = mock_builder
        mock_builder.build.return_value = mock_app
        mock_app.bot_data = {}
        mock_app_class.builder.return_value = mock_builder

        app = create_application(config)

        assert "command_registry" in app.bot_data
        assert isinstance(app.bot_data["command_registry"], CommandRegistry)
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_application.py::test_create_application_has_command_registry -v`
Expected: FAIL with "KeyError: 'command_registry'"

**Step 3: Write the implementation**

Update `src/bot/application.py` - add import and registry initialization:

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
from src.commands import CommandRegistry
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
    refresh_commands,
)
from .callbacks import handle_callback


def create_application(config: Config) -> Application:
    """Create and configure Telegram Application."""
    app = Application.builder().token(config.telegram_token).build()

    # Store config in bot_data for handlers to access
    app.bot_data["config"] = config

    # Initialize command registry
    app.bot_data["command_registry"] = CommandRegistry()

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
        ("refresh", refresh_commands),
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

    # Callback handler for inline keyboards (with auth)
    app.add_handler(CallbackQueryHandler(auth_middleware(handle_callback)))

    return app
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_application.py -v`
Expected: FAIL (refresh_commands not defined yet - will fix in next task)

**Step 5: Commit (partial - will complete after Task 6)**

Hold commit until handlers are updated.

---

### Task 6: Add /refresh Handler and Update /new

**Files:**
- Modify: `src/bot/handlers.py`
- Modify: `tests/test_handlers.py`

**Step 1: Write the failing tests**

Add to `tests/test_handlers.py`:

```python
from src.bot.handlers import refresh_commands


@pytest.mark.asyncio
async def test_refresh_commands_updates_registry(mock_update, mock_context):
    """refresh_commands calls registry.refresh."""
    mock_registry = AsyncMock()
    mock_registry.refresh = AsyncMock(return_value=5)
    mock_context.bot_data["command_registry"] = mock_registry
    mock_context.user_data["current_session"] = MagicMock(project_path="/test")

    await refresh_commands(mock_update, mock_context)

    mock_registry.refresh.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "5" in call_args  # Shows command count


@pytest.mark.asyncio
async def test_refresh_commands_no_session(mock_update, mock_context):
    """refresh_commands works without active session."""
    mock_registry = AsyncMock()
    mock_registry.refresh = AsyncMock(return_value=2)
    mock_context.bot_data["command_registry"] = mock_registry
    mock_context.user_data = {}

    await refresh_commands(mock_update, mock_context)

    mock_registry.refresh.assert_called_once_with(
        mock_update.get_bot(), project_path=None
    )
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_handlers.py::test_refresh_commands_updates_registry -v`
Expected: FAIL with "cannot import name 'refresh_commands'"

**Step 3: Write the implementation**

Add to `src/bot/handlers.py`:

```python
async def refresh_commands(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /refresh command - rescan Claude commands."""
    registry = context.bot_data.get("command_registry")
    session = context.user_data.get("current_session")
    project_path = session.project_path if session else None

    count = await registry.refresh(update.get_bot(), project_path=project_path)

    await update.message.reply_text(
        f"🔄 Commands refreshed. {count} Claude command(s) loaded."
    )
```

Update `_create_session` in `src/bot/handlers.py` to refresh commands:

```python
async def _create_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project_path: str,
    project_name: str | None = None,
) -> None:
    """Create a new session."""
    user_id = update.effective_user.id

    async with get_session() as db:
        repo = SessionRepository(db)
        session = await repo.create_session(
            telegram_user_id=user_id,
            project_path=project_path,
            project_name=project_name,
        )
        # Store session in user_data for quick access
        context.user_data["current_session"] = session

    # Refresh commands for this project
    registry = context.bot_data.get("command_registry")
    cmd_count = await registry.refresh(update.get_bot(), project_path=project_path)

    display_name = project_name or project_path
    await update.message.reply_text(
        f"✅ Created new session for {display_name}\n"
        f"📋 {cmd_count} Claude command(s) available.\n\n"
        "Send a message to start chatting with Claude."
    )
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_handlers.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bot/application.py src/bot/handlers.py tests/
git commit -m "feat(commands): integrate registry with /new and /refresh"
```

---

### Task 7: Dynamic Command Handler

**Files:**
- Modify: `src/bot/application.py`
- Create: `src/bot/command_handler.py`
- Modify: `tests/test_commands.py`

**Step 1: Write the failing test**

Add to `tests/test_commands.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_handle_claude_command_no_args():
    """Executes command immediately when no args needed."""
    from src.bot.command_handler import handle_claude_command

    mock_update = MagicMock()
    mock_update.message = AsyncMock()
    mock_update.message.text = "/review"
    mock_update.message.reply_text = AsyncMock(return_value=AsyncMock())

    mock_context = MagicMock()
    mock_context.user_data = {
        "current_session": MagicMock(
            project_path="/test",
            total_cost_usd=0.0,
        )
    }
    mock_context.bot_data = {
        "config": MagicMock(
            streaming=MagicMock(edit_throttle_ms=1000, chunk_size=3800)
        ),
        "command_registry": MagicMock(
            get=MagicMock(return_value=ClaudeCommand(
                name="review",
                description="Review code",
                prompt="Review this code for bugs.",
                needs_args=False,
            )),
            substitute_args=MagicMock(return_value="Review this code for bugs."),
        ),
    }

    with patch("src.bot.command_handler.TeleClaudeClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive():
            if False:
                yield

        mock_client.receive_response = MagicMock(return_value=mock_receive())
        mock_client_class.return_value = mock_client

        with patch("src.bot.command_handler.MessageStreamer"):
            await handle_claude_command(mock_update, mock_context)

        mock_client.query.assert_called_once_with("Review this code for bugs.")


@pytest.mark.asyncio
async def test_handle_claude_command_needs_args():
    """Prompts for arguments when command needs them."""
    from src.bot.command_handler import handle_claude_command

    mock_update = MagicMock()
    mock_update.message = AsyncMock()
    mock_update.message.text = "/fix-bug"
    mock_update.message.reply_text = AsyncMock()

    mock_context = MagicMock()
    mock_context.user_data = {
        "current_session": MagicMock(project_path="/test"),
    }
    mock_context.bot_data = {
        "command_registry": MagicMock(
            get=MagicMock(return_value=ClaudeCommand(
                name="fix-bug",
                description="Fix a bug",
                prompt="Fix this bug: $ARGUMENTS",
                needs_args=True,
            )),
        ),
    }

    await handle_claude_command(mock_update, mock_context)

    # Should prompt for args, not execute
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "requires input" in call_args
    assert "pending_command" in mock_context.user_data
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_commands.py::test_handle_claude_command_no_args -v`
Expected: FAIL with "No module named 'src.bot.command_handler'"

**Step 3: Write the implementation**

Create `src/bot/command_handler.py`:

```python
"""Handler for dynamic Claude commands."""
from telegram import Update
from telegram.ext import ContextTypes

from claude_agent_sdk import (
    AssistantMessage,
    UserMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

from src.claude import TeleClaudeClient, MessageStreamer
from src.claude.streaming import escape_html
from src.utils.keyboards import cancel_keyboard


async def handle_claude_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle a Claude slash command.

    If command needs args, prompts user and stores pending state.
    Otherwise executes immediately.
    """
    registry = context.bot_data.get("command_registry")
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text(
            "❌ No active session. Use /new to start one."
        )
        return

    # Extract command name from message
    text = update.message.text
    parts = text.split(maxsplit=1)
    cmd_name = parts[0][1:]  # Remove leading /
    inline_args = parts[1] if len(parts) > 1 else ""

    cmd = registry.get(cmd_name)
    if not cmd:
        await update.message.reply_text(
            f"❌ Unknown command: /{cmd_name}"
        )
        return

    # Check if args are needed
    if cmd.needs_args and not inline_args:
        # Store pending command and prompt for args
        context.user_data["pending_command"] = {
            "name": cmd.name,
            "prompt": cmd.prompt,
        }
        await update.message.reply_text(
            f"🔧 /{cmd.name} requires input.\n\n"
            f"📝 {cmd.description}\n\n"
            "Enter your input or /cancel:"
        )
        return

    # Execute command
    prompt = registry.substitute_args(cmd, inline_args)
    await _execute_prompt(update, context, prompt)


async def _execute_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
) -> None:
    """Execute a prompt and stream response."""
    session = context.user_data.get("current_session")
    config = context.bot_data.get("config")

    # Send "thinking" message
    thinking_msg = await update.message.reply_text(
        "🤔 Thinking...",
        reply_markup=cancel_keyboard(),
    )

    # Create streamer
    streamer = MessageStreamer(
        message=thinking_msg,
        throttle_ms=config.streaming.edit_throttle_ms,
        chunk_size=config.streaming.chunk_size,
    )

    try:
        async with TeleClaudeClient(config, session) as client:
            context.user_data["active_client"] = client

            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            await streamer.append_text(escape_html(block.text))
                        elif isinstance(block, ToolUseBlock):
                            tool_info = f"\n🔧 <b>{escape_html(block.name)}</b>\n"
                            if block.input:
                                for key, value in block.input.items():
                                    str_val = str(value)
                                    if len(str_val) > 200:
                                        str_val = str_val[:200] + "..."
                                    tool_info += f"   <code>{escape_html(key)}</code>: {escape_html(str_val)}\n"
                            await streamer.append_text(tool_info)

                elif isinstance(message, UserMessage):
                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            result_text = str(block.content) if block.content else "(no output)"
                            if len(result_text) > 500:
                                result_text = result_text[:500] + "\n... (truncated)"
                            result_info = f"\n📄 Result:\n<pre>{escape_html(result_text)}</pre>\n"
                            await streamer.append_text(result_info)

                elif isinstance(message, ResultMessage):
                    if message.total_cost_usd:
                        session.total_cost_usd += message.total_cost_usd

            await streamer.flush()

    except Exception as e:
        await thinking_msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        context.user_data.pop("active_client", None)
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_commands.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bot/command_handler.py tests/test_commands.py
git commit -m "feat(commands): add dynamic command handler"
```

---

### Task 8: Wire Dynamic Commands to Application

**Files:**
- Modify: `src/bot/application.py`
- Modify: `src/bot/handlers.py`

**Step 1: Write the failing test**

Add to `tests/test_handlers.py`:

```python
@pytest.mark.asyncio
async def test_handle_message_pending_command(mock_update, mock_context):
    """handle_message processes pending command args."""
    mock_context.user_data = {
        "current_session": MagicMock(
            project_path="/test",
            total_cost_usd=0.0,
        ),
        "pending_command": {
            "name": "fix-bug",
            "prompt": "Fix this bug: $ARGUMENTS",
        },
    }
    mock_context.bot_data["command_registry"] = MagicMock(
        substitute_args=MagicMock(return_value="Fix this bug: login broken"),
    )

    mock_thinking_msg = AsyncMock()
    mock_update.message.reply_text.return_value = mock_thinking_msg
    mock_update.message.text = "login broken"

    with patch("src.bot.handlers.TeleClaudeClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive():
            if False:
                yield

        mock_client.receive_response = MagicMock(return_value=mock_receive())
        mock_client_class.return_value = mock_client

        with patch("src.bot.handlers.MessageStreamer"):
            await handle_message(mock_update, mock_context)

        # Should have used substituted prompt
        mock_client.query.assert_called_once_with("Fix this bug: login broken")

    # pending_command should be cleared
    assert "pending_command" not in mock_context.user_data
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_handlers.py::test_handle_message_pending_command -v`
Expected: FAIL (pending_command not handled yet)

**Step 3: Write the implementation**

Update `handle_message` in `src/bot/handlers.py`:

```python
async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle regular text messages (Claude interaction)."""
    # Check if awaiting custom project path from /new -> Other
    if context.user_data.get("awaiting_path"):
        context.user_data["awaiting_path"] = False
        path = update.message.text.strip()
        await _create_session(update, context, path)
        return

    # Check if awaiting arguments for pending command
    if context.user_data.get("pending_command"):
        pending = context.user_data.pop("pending_command")
        registry = context.bot_data.get("command_registry")
        cmd = ClaudeCommand(
            name=pending["name"],
            description="",
            prompt=pending["prompt"],
            needs_args=True,
        )
        prompt = registry.substitute_args(cmd, update.message.text)
        await _execute_claude_prompt(update, context, prompt)
        return

    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text(
            "❌ No active session. Use /new to start one or /continue to resume."
        )
        return

    prompt = update.message.text
    await _execute_claude_prompt(update, context, prompt)
```

Extract `_execute_claude_prompt` from existing code in `handle_message`:

```python
async def _execute_claude_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
) -> None:
    """Execute a prompt and stream Claude's response."""
    session = context.user_data.get("current_session")
    config = context.bot_data.get("config")

    # Send "thinking" message
    thinking_msg = await update.message.reply_text(
        "🤔 Thinking...",
        reply_markup=cancel_keyboard(),
    )

    # Create streamer for this response
    streamer = MessageStreamer(
        message=thinking_msg,
        throttle_ms=config.streaming.edit_throttle_ms,
        chunk_size=config.streaming.chunk_size,
    )

    try:
        async with TeleClaudeClient(config, session) as client:
            # Track client for cancel
            context.user_data["active_client"] = client

            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            await streamer.append_text(escape_html(block.text))
                        elif isinstance(block, ToolUseBlock):
                            # Format tool usage with full details (HTML)
                            tool_info = f"\n🔧 <b>{escape_html(block.name)}</b>\n"
                            if block.input:
                                for key, value in block.input.items():
                                    # Truncate long values
                                    str_val = str(value)
                                    if len(str_val) > 200:
                                        str_val = str_val[:200] + "..."
                                    tool_info += f"   <code>{escape_html(key)}</code>: {escape_html(str_val)}\n"
                            await streamer.append_text(tool_info)

                elif isinstance(message, UserMessage):
                    # Show tool results
                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            result_text = str(block.content) if block.content else "(no output)"
                            # Truncate long results
                            if len(result_text) > 500:
                                result_text = result_text[:500] + "\n... (truncated)"
                            result_info = f"\n📄 Result:\n<pre>{escape_html(result_text)}</pre>\n"
                            await streamer.append_text(result_info)

                elif isinstance(message, ResultMessage):
                    # Update session cost
                    if message.total_cost_usd:
                        session.total_cost_usd += message.total_cost_usd

            # Final flush
            await streamer.flush()

    except Exception as e:
        await thinking_msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        context.user_data.pop("active_client", None)
```

Add import at top of handlers.py:

```python
from src.commands import ClaudeCommand
```

Update `src/bot/application.py` to add dynamic command handler:

```python
from .command_handler import handle_claude_command

# In create_application, add after other handlers:

    # Dynamic Claude command handler (catch-all for unknown commands)
    app.add_handler(
        MessageHandler(
            filters.COMMAND,
            auth_middleware(handle_claude_command),
        )
    )
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_handlers.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bot/
git commit -m "feat(commands): wire dynamic commands to message handler"
```

---

### Task 9: Full Integration Test

**Files:**
- Modify: `tests/test_commands.py`

**Step 1: Write the integration test**

Add to `tests/test_commands.py`:

```python
@pytest.mark.asyncio
async def test_full_command_flow(tmp_path, monkeypatch):
    """Full flow: scan commands, register, execute."""
    from src.commands import CommandRegistry, scan_commands

    # Setup mock home with commands
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    cmd_dir = home / ".claude" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "greet.md").write_text("""---
description: Greet someone
---
Say hello to $ARGUMENTS
""")

    # Create registry and scan
    registry = CommandRegistry()
    commands = scan_commands(project_path=None)

    # Verify scan found command
    assert len(commands) == 1
    assert commands[0].name == "greet"
    assert commands[0].needs_args is True

    # Test substitution
    cmd = commands[0]
    result = registry.substitute_args(cmd, "World")
    assert result == "Say hello to World"
```

**Step 2: Run test**

Run: `./venv/bin/python -m pytest tests/test_commands.py::test_full_command_flow -v`
Expected: PASS

**Step 3: Run all tests**

Run: `./venv/bin/python -m pytest tests/ -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/test_commands.py
git commit -m "test(commands): add full integration test"
```

---

### Task 10: Final Cleanup and Documentation

**Files:**
- Update: `src/bot/handlers.py` (update HELP_TEXT)

**Step 1: Update HELP_TEXT**

Update HELP_TEXT in `src/bot/handlers.py`:

```python
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
/refresh \\- Rescan Claude commands

*Help*
/help \\- Show this message

💡 Claude commands from \\.claude/commands/ appear in the / menu\\!
"""
```

**Step 2: Run all tests**

Run: `./venv/bin/python -m pytest tests/ -v`
Expected: All PASS

**Step 3: Final commit**

```bash
git add src/bot/handlers.py
git commit -m "docs: update help text with /refresh command"
```

---

Plan complete and saved to `docs/plans/2025-12-01-claude-commands-implementation.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
