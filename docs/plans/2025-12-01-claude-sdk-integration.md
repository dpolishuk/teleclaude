# Claude Agent SDK Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate the official `claude-agent-sdk` to replace placeholder code and enable real Claude Code interactions via Telegram.

**Architecture:** Use `ClaudeSDKClient` for stateful multi-turn conversations per user session. Stream responses to Telegram with throttled message edits. Use PreToolUse hooks to intercept dangerous commands and request Telegram approval via inline keyboards.

**Tech Stack:** claude-agent-sdk 0.1.10, python-telegram-bot v21+, asyncio for concurrent message handling

---

## Task 1: Update Claude Client to Use Real SDK

**Files:**
- Modify: `src/claude/client.py`
- Test: `tests/test_claude_client.py`

**Step 1: Write the failing test**

Create `tests/test_claude_client.py` (replace existing):

```python
"""Test Claude client wrapper."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.claude.client import TeleClaudeClient, create_claude_options
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
        project_path="/home/user/myapp",
    )


def test_create_claude_options_basic(mock_config, mock_session):
    """create_claude_options builds correct options."""
    options = create_claude_options(mock_config, mock_session)

    assert options.max_turns == 10
    assert options.permission_mode == "acceptEdits"
    assert options.max_budget_usd == 5.0
    assert options.cwd == "/home/user/myapp"


def test_create_claude_options_with_resume(mock_config, mock_session):
    """create_claude_options includes fork_session when session has claude_session_id."""
    mock_session.claude_session_id = "claude_abc123"
    options = create_claude_options(mock_config, mock_session)

    assert options.fork_session == "claude_abc123"


def test_create_claude_options_allowed_tools(mock_config, mock_session):
    """create_claude_options includes standard tools."""
    options = create_claude_options(mock_config, mock_session)

    assert "Read" in options.allowed_tools
    assert "Write" in options.allowed_tools
    assert "Bash" in options.allowed_tools


def test_teleclaude_client_init(mock_config, mock_session):
    """TeleClaudeClient initializes with config and session."""
    client = TeleClaudeClient(mock_config, mock_session)

    assert client.config == mock_config
    assert client.session == mock_session
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_claude_client.py -v`
Expected: FAIL - `create_claude_options` not found

**Step 3: Implement Claude client with real SDK**

Modify `src/claude/client.py`:

```python
"""Claude SDK client wrapper."""
from typing import Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
)

from src.config.settings import Config
from src.storage.models import Session
from src.claude.hooks import check_dangerous_command


def create_claude_options(
    config: Config,
    session: Session,
    hooks: dict | None = None,
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions from config and session.

    Args:
        config: Application configuration.
        session: Current user session.
        hooks: Optional custom hooks dict. If None, uses default dangerous command hooks.

    Returns:
        Configured ClaudeAgentOptions.
    """
    # Build hooks with HookMatcher format
    if hooks is None:
        hooks = {
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[check_dangerous_command]),
            ],
        }

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permission_mode=config.claude.permission_mode,
        max_turns=config.claude.max_turns,
        max_budget_usd=config.claude.max_budget_usd,
        cwd=session.current_directory or session.project_path,
        hooks=hooks,
    )

    # Resume from previous Claude session if available
    if session.claude_session_id:
        options.fork_session = session.claude_session_id

    return options


class TeleClaudeClient:
    """Wrapper for Claude SDK client with Telegram integration."""

    def __init__(
        self,
        config: Config,
        session: Session,
        hooks: dict | None = None,
    ):
        """Initialize with configuration and session.

        Args:
            config: Application configuration.
            session: Current user session.
            hooks: Optional custom hooks for tool approval.
        """
        self.config = config
        self.session = session
        self.hooks = hooks
        self._client: Optional[ClaudeSDKClient] = None
        self._options: Optional[ClaudeAgentOptions] = None

    async def __aenter__(self) -> "TeleClaudeClient":
        """Enter async context - create SDK client."""
        self._options = create_claude_options(
            self.config, self.session, self.hooks
        )
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args) -> None:
        """Exit async context - cleanup."""
        if self._client:
            await self._client.__aexit__(*args)

    async def query(self, prompt: str):
        """Send prompt to Claude.

        Args:
            prompt: User's message to Claude.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        await self._client.query(prompt)

    def receive_response(self):
        """Get async iterator for response messages.

        Returns:
            AsyncIterator of SDK messages.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client.receive_response()

    async def interrupt(self):
        """Interrupt current operation."""
        if self._client:
            await self._client.interrupt()

    @property
    def client(self) -> Optional[ClaudeSDKClient]:
        """Access underlying SDK client."""
        return self._client
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_claude_client.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/claude/client.py tests/test_claude_client.py
git commit -m "feat(claude): integrate real claude-agent-sdk client"
```

---

## Task 2: Update Hooks to Use SDK HookMatcher Format

**Files:**
- Modify: `src/claude/hooks.py`
- Test: `tests/test_hooks.py`

**Step 1: Write the failing test**

Create `tests/test_hooks.py` (replace existing):

```python
"""Test Claude hooks."""
import pytest
from src.claude.hooks import (
    is_dangerous_command,
    check_dangerous_command,
    create_approval_hooks,
    DANGEROUS_PATTERNS,
)


def test_is_dangerous_command_matches_rm_rf():
    """Detects rm -rf as dangerous."""
    assert is_dangerous_command("rm -rf /tmp/test") is True


def test_is_dangerous_command_safe():
    """Allows safe commands."""
    assert is_dangerous_command("ls -la") is False


def test_is_dangerous_command_case_insensitive():
    """Pattern matching is case insensitive."""
    assert is_dangerous_command("SUDO apt install") is True


def test_is_dangerous_command_custom_patterns():
    """Custom patterns override defaults."""
    assert is_dangerous_command("rm test.txt", patterns=["rm"]) is True
    assert is_dangerous_command("ls", patterns=["rm"]) is False


@pytest.mark.asyncio
async def test_check_dangerous_command_blocks_dangerous():
    """Hook returns ask decision for dangerous commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /important"},
    }

    result = await check_dangerous_command(input_data, "tool123", {})

    assert result["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert "rm -rf" in result["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.asyncio
async def test_check_dangerous_command_allows_safe():
    """Hook returns empty dict for safe commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
    }

    result = await check_dangerous_command(input_data, "tool123", {})

    assert result == {}


@pytest.mark.asyncio
async def test_check_dangerous_command_ignores_non_bash():
    """Hook ignores non-Bash tools."""
    input_data = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/etc/passwd"},
    }

    result = await check_dangerous_command(input_data, "tool123", {})

    assert result == {}


def test_create_approval_hooks_returns_hookmatcher_format():
    """create_approval_hooks returns SDK-compatible format."""
    hooks = create_approval_hooks()

    assert "PreToolUse" in hooks
    # Should be a list of HookMatcher objects
    assert isinstance(hooks["PreToolUse"], list)
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_hooks.py -v`
Expected: FAIL - `create_approval_hooks` returns wrong format

**Step 3: Update hooks to use HookMatcher**

Modify `src/claude/hooks.py`:

```python
"""Claude SDK hooks for approval workflow."""
from typing import Any, Callable

from claude_agent_sdk import HookMatcher

# Default patterns that require user approval (must be lowercase for comparison)
DANGEROUS_PATTERNS: list[str] = [
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


def is_dangerous_command(
    command: str, patterns: list[str] | None = None
) -> bool:
    """Check if command matches dangerous patterns.

    Args:
        command: The command to check.
        patterns: Custom patterns to check against. If None, uses DANGEROUS_PATTERNS.

    Returns:
        True if command matches any dangerous pattern.
    """
    check_patterns = patterns if patterns is not None else DANGEROUS_PATTERNS
    command_lower = command.lower()
    return any(pattern.lower() in command_lower for pattern in check_patterns)


def _find_matched_pattern(command: str, patterns: list[str]) -> str:
    """Find which pattern matched the command."""
    command_lower = command.lower()
    return next(
        (p for p in patterns if p.lower() in command_lower),
        "dangerous pattern",
    )


async def check_dangerous_command(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    """PreToolUse hook to intercept dangerous operations.

    This hook checks Bash commands against DANGEROUS_PATTERNS and returns
    an "ask" decision if a match is found, prompting for user approval.

    Args:
        input_data: Contains tool_name and tool_input from SDK.
        tool_use_id: Unique ID for this tool use.
        context: Hook context from SDK.

    Returns:
        Empty dict to allow, or dict with permissionDecision to block/ask.
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Bash":
        return {}

    command = tool_input.get("command", "")

    if is_dangerous_command(command):
        matched = _find_matched_pattern(command, DANGEROUS_PATTERNS)

        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"Command contains: {matched}",
            }
        }

    return {}


def create_dangerous_command_hook(
    patterns: list[str],
) -> Callable[[dict[str, Any], str | None, dict[str, Any]], Any]:
    """Create a hook function with custom dangerous patterns.

    Args:
        patterns: List of patterns to check against.

    Returns:
        An async hook function for PreToolUse.
    """
    async def hook(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name != "Bash":
            return {}

        command = tool_input.get("command", "")

        if is_dangerous_command(command, patterns):
            matched = _find_matched_pattern(command, patterns)

            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": f"Command contains: {matched}",
                }
            }

        return {}

    return hook


def create_approval_hooks(dangerous_commands: list[str] | None = None) -> dict:
    """Create hooks dict for ClaudeAgentOptions.

    Args:
        dangerous_commands: Optional list of additional dangerous patterns.
            If provided, these are combined with DANGEROUS_PATTERNS.
            If None, only DANGEROUS_PATTERNS are used.

    Returns:
        A dict with HookMatcher format suitable for ClaudeAgentOptions.
    """
    if dangerous_commands is None:
        hook = check_dangerous_command
    else:
        combined_patterns = list(DANGEROUS_PATTERNS) + dangerous_commands
        hook = create_dangerous_command_hook(combined_patterns)

    return {
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[hook]),
        ],
    }
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_hooks.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/claude/hooks.py tests/test_hooks.py
git commit -m "feat(claude): update hooks to use SDK HookMatcher format"
```

---

## Task 3: Add Streaming Module for Telegram

**Files:**
- Create: `src/claude/streaming.py`
- Create: `tests/test_streaming.py`

**Step 1: Write the failing test**

Create `tests/test_streaming.py`:

```python
"""Test streaming to Telegram."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.claude.streaming import MessageStreamer


@pytest.fixture
def mock_message():
    """Create mock Telegram message."""
    msg = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.message_id = 123
    return msg


@pytest.fixture
def streamer(mock_message):
    """Create MessageStreamer instance."""
    return MessageStreamer(
        message=mock_message,
        throttle_ms=100,
        chunk_size=100,
    )


@pytest.mark.asyncio
async def test_streamer_init(streamer, mock_message):
    """Streamer initializes with message."""
    assert streamer.message == mock_message
    assert streamer.current_text == ""


@pytest.mark.asyncio
async def test_streamer_append_text(streamer):
    """append_text accumulates text."""
    await streamer.append_text("Hello ")
    await streamer.append_text("World")

    assert streamer.current_text == "Hello World"


@pytest.mark.asyncio
async def test_streamer_flush_updates_message(streamer, mock_message):
    """flush sends edit to Telegram."""
    streamer.current_text = "Test content"
    await streamer.flush()

    mock_message.edit_text.assert_called()


@pytest.mark.asyncio
async def test_streamer_truncates_long_text(streamer):
    """Long text is truncated with indicator."""
    streamer.chunk_size = 50
    streamer.current_text = "x" * 100

    display = streamer._get_display_text()

    assert len(display) <= 60  # chunk_size + some buffer for truncation marker
    assert "..." in display or "[truncated]" in display


@pytest.mark.asyncio
async def test_streamer_throttles_edits(streamer, mock_message):
    """Multiple rapid appends don't spam edits."""
    streamer.throttle_ms = 500

    for i in range(10):
        await streamer.append_text(f"chunk{i} ")
        await asyncio.sleep(0.01)

    # Should have fewer edits than appends due to throttling
    assert mock_message.edit_text.call_count < 10
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_streaming.py -v`
Expected: FAIL - module not found

**Step 3: Implement streaming module**

Create `src/claude/streaming.py`:

```python
"""Streaming responses to Telegram with throttling."""
import asyncio
import time
from typing import Optional

from telegram import Message
from telegram.error import BadRequest, TimedOut


class MessageStreamer:
    """Streams Claude responses to a Telegram message with throttling.

    Accumulates text and periodically updates the Telegram message,
    respecting rate limits and handling message size limits.
    """

    def __init__(
        self,
        message: Message,
        throttle_ms: int = 1000,
        chunk_size: int = 3800,
    ):
        """Initialize streamer.

        Args:
            message: Telegram message to edit with updates.
            throttle_ms: Minimum milliseconds between message edits.
            chunk_size: Maximum characters to display (Telegram limit ~4096).
        """
        self.message = message
        self.throttle_ms = throttle_ms
        self.chunk_size = chunk_size
        self.current_text = ""
        self._last_edit_time: float = 0
        self._pending_flush: bool = False
        self._lock = asyncio.Lock()

    async def append_text(self, text: str) -> None:
        """Append text and schedule flush if throttle allows.

        Args:
            text: Text to append to current content.
        """
        async with self._lock:
            self.current_text += text
            await self._maybe_flush()

    async def _maybe_flush(self) -> None:
        """Flush if enough time has passed since last edit."""
        now = time.time() * 1000  # ms
        elapsed = now - self._last_edit_time

        if elapsed >= self.throttle_ms:
            await self._do_flush()
        else:
            self._pending_flush = True

    async def _do_flush(self) -> None:
        """Actually send the edit to Telegram."""
        if not self.current_text:
            return

        display_text = self._get_display_text()

        try:
            await self.message.edit_text(display_text)
            self._last_edit_time = time.time() * 1000
            self._pending_flush = False
        except BadRequest as e:
            # Message content unchanged or other Telegram error
            if "not modified" not in str(e).lower():
                raise
        except TimedOut:
            # Telegram timeout, will retry on next flush
            pass

    def _get_display_text(self) -> str:
        """Get text for display, truncated if needed."""
        if len(self.current_text) <= self.chunk_size:
            return self.current_text

        # Truncate with indicator
        truncated = self.current_text[-(self.chunk_size - 20):]
        return f"[...truncated...]\n{truncated}"

    async def flush(self) -> None:
        """Force flush current content to Telegram."""
        async with self._lock:
            await self._do_flush()

    async def finish(self, final_text: Optional[str] = None) -> None:
        """Finalize streaming with optional final text.

        Args:
            final_text: Optional text to replace current content.
        """
        async with self._lock:
            if final_text is not None:
                self.current_text = final_text
            await self._do_flush()

    def set_text(self, text: str) -> None:
        """Replace current text entirely."""
        self.current_text = text
```

Update `src/claude/__init__.py`:

```python
"""Claude integration module."""
from .client import TeleClaudeClient, create_claude_options
from .streaming import MessageStreamer

__all__ = ["TeleClaudeClient", "create_claude_options", "MessageStreamer"]
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_streaming.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/claude/streaming.py src/claude/__init__.py tests/test_streaming.py
git commit -m "feat(claude): add MessageStreamer for throttled Telegram updates"
```

---

## Task 4: Update Message Handler to Use Claude SDK

**Files:**
- Modify: `src/bot/handlers.py`
- Test: `tests/test_handlers.py`

**Step 1: Write the failing test**

Add to `tests/test_handlers.py`:

```python
"""Test bot handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_update():
    """Create mock Telegram Update."""
    update = MagicMock()
    update.effective_user = MagicMock(id=12345, first_name="Test")
    update.message = AsyncMock()
    update.message.text = "Hello Claude"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context."""
    context = MagicMock()
    context.user_data = {}
    context.bot_data = {
        "config": MagicMock(
            claude=MagicMock(max_turns=10, permission_mode="acceptEdits", max_budget_usd=5.0),
            streaming=MagicMock(edit_throttle_ms=1000, chunk_size=3800),
        )
    }
    return context


@pytest.mark.asyncio
async def test_handle_message_no_session(mock_update, mock_context):
    """handle_message prompts to create session when none exists."""
    mock_context.user_data = {}

    from src.bot.handlers import handle_message
    await handle_message(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "No active session" in call_args


@pytest.mark.asyncio
async def test_handle_message_with_session_calls_claude(mock_update, mock_context):
    """handle_message sends prompt to Claude when session exists."""
    mock_session = MagicMock(
        id="sess123",
        claude_session_id=None,
        current_directory="/test",
        project_path="/test",
    )
    mock_context.user_data = {"current_session": mock_session}

    with patch("src.bot.handlers.TeleClaudeClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = MagicMock(return_value=AsyncMock().__aiter__())
        mock_client_class.return_value = mock_client

        from src.bot.handlers import handle_message
        await handle_message(mock_update, mock_context)

        # Should have called query with the user's message
        mock_client.query.assert_called_once_with("Hello Claude")
```

**Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_handlers.py::test_handle_message_with_session_calls_claude -v`
Expected: FAIL - handler doesn't use TeleClaudeClient yet

**Step 3: Update handle_message to use Claude SDK**

Modify `src/bot/handlers.py` - update the imports and `handle_message` function:

```python
"""Telegram bot command handlers."""
from telegram import Update
from telegram.ext import ContextTypes

from claude_agent_sdk import (
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)

from src.storage.database import get_session
from src.storage.repository import SessionRepository
from src.claude import TeleClaudeClient, MessageStreamer
from src.utils.keyboards import project_keyboard, cancel_keyboard

# ... keep existing HELP_TEXT and other handlers ...

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

    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text(
            "❌ No active session. Use /new to start one or /continue to resume."
        )
        return

    prompt = update.message.text
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
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            await streamer.append_text(block.text)
                        elif isinstance(block, ToolUseBlock):
                            tool_info = f"\n🔧 Using: {block.name}\n"
                            await streamer.append_text(tool_info)

                elif isinstance(message, ResultMessage):
                    # Update session cost
                    if message.total_cost_usd:
                        session.total_cost_usd += message.total_cost_usd

            # Final flush
            await streamer.flush()

    except Exception as e:
        await thinking_msg.edit_text(f"❌ Error: {str(e)}")
```

**Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_handlers.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/bot/handlers.py tests/test_handlers.py
git commit -m "feat(bot): integrate Claude SDK into message handler"
```

---

## Task 5: Add Cancel Handler for Interrupts

**Files:**
- Modify: `src/bot/handlers.py`
- Modify: `src/bot/callbacks.py`

**Step 1: Update cancel command handler**

Modify cancel handler in `src/bot/handlers.py`:

```python
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command."""
    client = context.user_data.get("active_client")

    if client:
        try:
            await client.interrupt()
            await update.message.reply_text("🛑 Operation cancelled.")
        except Exception:
            await update.message.reply_text("🛑 Cancel requested.")
        finally:
            context.user_data.pop("active_client", None)
    else:
        await update.message.reply_text("ℹ️ No operation in progress.")
```

**Step 2: Update handle_message to track client**

In `handle_message`, add client tracking:

```python
async def handle_message(...):
    # ... existing code ...

    try:
        async with TeleClaudeClient(config, session) as client:
            # Track client for cancel
            context.user_data["active_client"] = client

            await client.query(prompt)
            # ... rest of handler ...

    finally:
        context.user_data.pop("active_client", None)
```

**Step 3: Update cancel callback**

Modify `src/bot/callbacks.py` to handle cancel button:

```python
async def _handle_cancel(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle cancel button press."""
    client = context.user_data.get("active_client")

    if client:
        try:
            await client.interrupt()
        except Exception:
            pass
        finally:
            context.user_data.pop("active_client", None)

    await query.answer("Cancelled")
    await query.edit_message_text("🛑 Operation cancelled.")
```

**Step 4: Run all tests**

Run: `./venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/bot/handlers.py src/bot/callbacks.py
git commit -m "feat(bot): add cancel/interrupt support for Claude operations"
```

---

## Task 6: Integration Test with Real SDK

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test (marked skip without API key)**

Create `tests/test_integration.py`:

```python
"""Integration tests with real Claude SDK."""
import os
import pytest
from unittest.mock import MagicMock

from src.claude import TeleClaudeClient, create_claude_options
from src.config.settings import Config, ClaudeConfig


# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)


@pytest.fixture
def config():
    """Real config for integration tests."""
    return Config(
        allowed_users=[12345],
        claude=ClaudeConfig(
            max_turns=2,
            permission_mode="acceptEdits",
            max_budget_usd=0.10,
        ),
    )


@pytest.fixture
def session(tmp_path):
    """Real session for integration tests."""
    return MagicMock(
        id="integ_test",
        claude_session_id=None,
        current_directory=str(tmp_path),
        project_path=str(tmp_path),
    )


@pytest.mark.asyncio
async def test_simple_query(config, session):
    """Test a simple query returns response."""
    async with TeleClaudeClient(config, session) as client:
        await client.query("What is 2+2? Reply with just the number.")

        responses = []
        async for message in client.receive_response():
            responses.append(message)

        assert len(responses) > 0


@pytest.mark.asyncio
async def test_options_creation(config, session):
    """Test options are created correctly."""
    options = create_claude_options(config, session)

    assert options.max_turns == 2
    assert options.max_budget_usd == 0.10
    assert "Bash" in options.allowed_tools
```

**Step 2: Run integration test (will skip without API key)**

Run: `./venv/bin/python -m pytest tests/test_integration.py -v`
Expected: SKIPPED (unless ANTHROPIC_API_KEY is set)

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for Claude SDK"
```

---

## Task 7: Final Testing and Bot Restart

**Step 1: Run full test suite**

Run: `./venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

**Step 2: Restart bot and test manually**

```bash
pkill -f "python.*src.main" || true
./venv/bin/python -m src.main &
```

**Step 3: Test flow in Telegram**

1. Send `/new`
2. Click "📁 Other..."
3. Enter a project path
4. Send a message like "What files are in this directory?"
5. Verify Claude responds with actual file listing
6. Send `/cancel` during a long response to test interrupt

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Claude Agent SDK integration"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Update Claude Client | `src/claude/client.py` |
| 2 | Update Hooks Format | `src/claude/hooks.py` |
| 3 | Add Streaming Module | `src/claude/streaming.py` |
| 4 | Update Message Handler | `src/bot/handlers.py` |
| 5 | Add Cancel Support | `src/bot/handlers.py`, `src/bot/callbacks.py` |
| 6 | Integration Tests | `tests/test_integration.py` |
| 7 | Final Testing | Manual verification |

**Total estimated tasks:** 7 tasks, ~35 steps
