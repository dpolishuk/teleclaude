# Voice Messages Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add voice and audio message support to TeleClaude, transcribing speech via OpenAI Whisper API and sending to Claude.

**Architecture:** Voice/audio handlers download files from Telegram, send to Whisper API for transcription, display transcript with confirmation UI, then route to existing Claude prompt execution on user confirmation.

**Tech Stack:** python-telegram-bot v21 (filters.VOICE, filters.AUDIO), httpx (async HTTP), OpenAI Whisper API

---

## Task 1: Add httpx dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add httpx to requirements**

Add this line to `requirements.txt`:

```
httpx>=0.27
```

**Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Successfully installed httpx

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add httpx for async HTTP requests"
```

---

## Task 2: Add VoiceConfig to settings

**Files:**
- Modify: `src/config/settings.py:104-116`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_voice_config_defaults():
    """VoiceConfig has correct defaults."""
    from src.config.settings import VoiceConfig

    config = VoiceConfig()

    assert config.enabled is True
    assert config.openai_api_key == ""
    assert config.max_duration_seconds == 600
    assert config.max_file_size_mb == 20
    assert config.language == "ru"


def test_config_includes_voice():
    """Config includes voice configuration."""
    from src.config.settings import Config

    config = Config()

    assert hasattr(config, "voice")
    assert config.voice.enabled is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_voice_config_defaults -v`
Expected: FAIL with "cannot import name 'VoiceConfig'"

**Step 3: Write minimal implementation**

Add to `src/config/settings.py` after `DatabaseConfig` (around line 102):

```python
@dataclass
class VoiceConfig:
    """Voice message transcription settings."""

    enabled: bool = True
    openai_api_key: str = ""
    max_duration_seconds: int = 600  # 10 minutes
    max_file_size_mb: int = 20
    language: str = "ru"  # Default Russian
```

Update `Config` class (around line 105) to add voice field:

```python
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
    mcp: MCPConfig = field(default_factory=MCPConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)  # ADD THIS LINE
    telegram_token: str = ""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py::test_voice_config_defaults tests/test_config.py::test_config_includes_voice -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/config/settings.py tests/test_config.py
git commit -m "feat(config): add VoiceConfig for voice message settings"
```

---

## Task 3: Parse voice config from YAML

**Files:**
- Modify: `src/config/settings.py:203-254` (in `_parse_config`)
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_parse_voice_config_from_yaml():
    """Voice config is parsed from YAML data."""
    from src.config.settings import _parse_config

    data = {
        "voice": {
            "enabled": True,
            "openai_api_key": "sk-test123",
            "max_duration_seconds": 300,
            "max_file_size_mb": 10,
            "language": "en",
        }
    }

    config = _parse_config(data)

    assert config.voice.enabled is True
    assert config.voice.openai_api_key == "sk-test123"
    assert config.voice.max_duration_seconds == 300
    assert config.voice.max_file_size_mb == 10
    assert config.voice.language == "en"


def test_parse_voice_config_uses_defaults():
    """Voice config uses defaults when not in YAML."""
    from src.config.settings import _parse_config

    data = {}
    config = _parse_config(data)

    assert config.voice.enabled is True
    assert config.voice.language == "ru"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_parse_voice_config_from_yaml -v`
Expected: FAIL (voice config not parsed, uses defaults only)

**Step 3: Write minimal implementation**

Add to `_parse_config()` function in `src/config/settings.py`, after the database config parsing (around line 252):

```python
    if "voice" in data:
        config.voice = VoiceConfig(
            enabled=data["voice"].get("enabled", True),
            openai_api_key=data["voice"].get("openai_api_key", ""),
            max_duration_seconds=data["voice"].get("max_duration_seconds", 600),
            max_file_size_mb=data["voice"].get("max_file_size_mb", 20),
            language=data["voice"].get("language", "ru"),
        )

    return config
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py::test_parse_voice_config_from_yaml tests/test_config.py::test_parse_voice_config_uses_defaults -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/config/settings.py tests/test_config.py
git commit -m "feat(config): parse voice config from YAML"
```

---

## Task 4: Create TranscriptionService

**Files:**
- Create: `src/voice/__init__.py`
- Create: `src/voice/transcription.py`
- Create: `tests/test_voice.py`

**Step 1: Create module init**

Create `src/voice/__init__.py`:

```python
"""Voice message handling module."""
from .transcription import TranscriptionService, TranscriptResult

__all__ = ["TranscriptionService", "TranscriptResult"]
```

**Step 2: Write the failing test**

Create `tests/test_voice.py`:

```python
"""Tests for voice message handling."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from src.voice.transcription import TranscriptionService, TranscriptResult


def test_transcript_result_dataclass():
    """TranscriptResult holds transcription data."""
    result = TranscriptResult(
        text="Hello world",
        duration_seconds=5.5,
        language="ru",
    )

    assert result.text == "Hello world"
    assert result.duration_seconds == 5.5
    assert result.language == "ru"


def test_transcription_service_init():
    """TranscriptionService initializes with API key and language."""
    service = TranscriptionService(api_key="sk-test", default_language="ru")

    assert service.api_key == "sk-test"
    assert service.default_language == "ru"


@pytest.mark.asyncio
async def test_transcription_service_transcribe():
    """TranscriptionService calls Whisper API and returns result."""
    service = TranscriptionService(api_key="sk-test", default_language="ru")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "text": "Transcribed text",
        "duration": 10.5,
        "language": "ru",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("src.voice.transcription.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_instance

        # Create a temp file for testing
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(b"fake audio data")
            temp_path = Path(f.name)

        try:
            result = await service.transcribe(temp_path)
        finally:
            temp_path.unlink()

    assert result.text == "Transcribed text"
    assert result.duration_seconds == 10.5
    assert result.language == "ru"
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_voice.py::test_transcript_result_dataclass -v`
Expected: FAIL with "No module named 'src.voice'"

**Step 4: Write minimal implementation**

Create `src/voice/transcription.py`:

```python
"""OpenAI Whisper API transcription service."""
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class TranscriptResult:
    """Result from audio transcription."""

    text: str
    duration_seconds: float
    language: str


class TranscriptionService:
    """OpenAI Whisper API wrapper for audio transcription."""

    WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"

    def __init__(self, api_key: str, default_language: str = "ru"):
        """Initialize transcription service.

        Args:
            api_key: OpenAI API key
            default_language: Default language code for transcription
        """
        self.api_key = api_key
        self.default_language = default_language

    async def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
    ) -> TranscriptResult:
        """Transcribe audio file using Whisper API.

        Args:
            audio_path: Path to audio file
            language: Optional language override

        Returns:
            TranscriptResult with text, duration, and language

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        async with httpx.AsyncClient() as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    self.WHISPER_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"file": (audio_path.name, f)},
                    data={
                        "model": "whisper-1",
                        "language": language or self.default_language,
                        "response_format": "verbose_json",
                    },
                    timeout=120.0,
                )
            response.raise_for_status()
            data = response.json()

            return TranscriptResult(
                text=data["text"].strip(),
                duration_seconds=data.get("duration", 0),
                language=data.get("language", self.default_language),
            )
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_voice.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/voice/__init__.py src/voice/transcription.py tests/test_voice.py
git commit -m "feat(voice): add TranscriptionService for Whisper API"
```

---

## Task 5: Add voice confirmation keyboard

**Files:**
- Modify: `src/bot/keyboards.py`
- Modify: `tests/test_keyboards.py`

**Step 1: Write the failing test**

Add to `tests/test_keyboards.py`:

```python
def test_build_voice_confirm_keyboard():
    """Voice confirm keyboard has Send/Edit/Cancel buttons."""
    from src.bot.keyboards import build_voice_confirm_keyboard

    keyboard = build_voice_confirm_keyboard()

    # Should have one row with three buttons
    assert len(keyboard.inline_keyboard) == 1
    row = keyboard.inline_keyboard[0]
    assert len(row) == 3

    # Check button labels and callback data
    assert "Send" in row[0].text
    assert row[0].callback_data == "voice:send"

    assert "Edit" in row[1].text
    assert row[1].callback_data == "voice:edit"

    assert "Cancel" in row[2].text
    assert row[2].callback_data == "voice:cancel"


def test_build_voice_retry_keyboard():
    """Voice retry keyboard has Retry button."""
    from src.bot.keyboards import build_voice_retry_keyboard

    keyboard = build_voice_retry_keyboard()

    assert len(keyboard.inline_keyboard) == 1
    row = keyboard.inline_keyboard[0]
    assert len(row) == 1

    assert "Retry" in row[0].text
    assert row[0].callback_data == "voice:retry"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_keyboards.py::test_build_voice_confirm_keyboard -v`
Expected: FAIL with "cannot import name 'build_voice_confirm_keyboard'"

**Step 3: Write minimal implementation**

Add to `src/bot/keyboards.py` at the end:

```python
def build_voice_confirm_keyboard() -> InlineKeyboardMarkup:
    """Build Send/Edit/Cancel keyboard for voice confirmation.

    Returns:
        InlineKeyboardMarkup with three buttons in one row.
        Callback data pattern: voice:<action>
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Send", callback_data="voice:send"),
            InlineKeyboardButton("✏️ Edit", callback_data="voice:edit"),
            InlineKeyboardButton("❌ Cancel", callback_data="voice:cancel"),
        ]
    ])


def build_voice_retry_keyboard() -> InlineKeyboardMarkup:
    """Build Retry keyboard for failed transcription.

    Returns:
        InlineKeyboardMarkup with single Retry button.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Retry", callback_data="voice:retry")]
    ])
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_keyboards.py::test_build_voice_confirm_keyboard tests/test_keyboards.py::test_build_voice_retry_keyboard -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/keyboards.py tests/test_keyboards.py
git commit -m "feat(keyboards): add voice confirmation and retry keyboards"
```

---

## Task 6: Create voice handlers

**Files:**
- Create: `src/voice/handler.py`
- Modify: `src/voice/__init__.py`
- Add to: `tests/test_voice.py`

**Step 1: Write the failing test**

Add to `tests/test_voice.py`:

```python
@pytest.mark.asyncio
async def test_handle_voice_no_session():
    """handle_voice returns error when no session."""
    from src.voice.handler import handle_voice

    update = MagicMock()
    update.message = AsyncMock()
    update.message.voice = MagicMock(file_id="abc", duration=10, file_size=1000)
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {}
    context.bot_data = {"config": MagicMock()}

    await handle_voice(update, context)

    update.message.reply_text.assert_called_once()
    call_args = str(update.message.reply_text.call_args)
    assert "No active session" in call_args


@pytest.mark.asyncio
async def test_handle_voice_exceeds_duration():
    """handle_voice returns error when duration exceeds limit."""
    from src.voice.handler import handle_voice

    update = MagicMock()
    update.message = AsyncMock()
    update.message.voice = MagicMock(file_id="abc", duration=700, file_size=1000)
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"current_session": MagicMock()}
    context.bot_data = {
        "config": MagicMock(
            voice=MagicMock(max_duration_seconds=600, max_file_size_mb=20)
        )
    }

    await handle_voice(update, context)

    update.message.reply_text.assert_called_once()
    call_args = str(update.message.reply_text.call_args)
    assert "too long" in call_args.lower()


@pytest.mark.asyncio
async def test_handle_voice_exceeds_file_size():
    """handle_voice returns error when file size exceeds limit."""
    from src.voice.handler import handle_voice

    update = MagicMock()
    update.message = AsyncMock()
    update.message.voice = MagicMock(
        file_id="abc",
        duration=10,
        file_size=25 * 1024 * 1024  # 25MB
    )
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"current_session": MagicMock()}
    context.bot_data = {
        "config": MagicMock(
            voice=MagicMock(max_duration_seconds=600, max_file_size_mb=20)
        )
    }

    await handle_voice(update, context)

    update.message.reply_text.assert_called_once()
    call_args = str(update.message.reply_text.call_args)
    assert "too large" in call_args.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_voice.py::test_handle_voice_no_session -v`
Expected: FAIL with "No module named 'src.voice.handler'"

**Step 3: Write minimal implementation**

Create `src/voice/handler.py`:

```python
"""Voice message handlers for Telegram."""
import logging
from pathlib import Path
import tempfile

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.keyboards import build_voice_confirm_keyboard, build_voice_retry_keyboard
from src.claude.streaming import escape_html

logger = logging.getLogger(__name__)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages.

    Args:
        update: Telegram update with voice message
        context: Bot context
    """
    voice = update.message.voice
    await _process_audio(
        update,
        context,
        file_id=voice.file_id,
        duration=voice.duration,
        file_size=voice.file_size,
    )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio file messages.

    Args:
        update: Telegram update with audio file
        context: Bot context
    """
    audio = update.message.audio
    await _process_audio(
        update,
        context,
        file_id=audio.file_id,
        duration=audio.duration,
        file_size=audio.file_size,
    )


async def _process_audio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_id: str,
    duration: int | None,
    file_size: int | None,
) -> None:
    """Process voice or audio message.

    Args:
        update: Telegram update
        context: Bot context
        file_id: Telegram file ID
        duration: Audio duration in seconds
        file_size: File size in bytes
    """
    config = context.bot_data["config"]

    # Check session exists
    session = context.user_data.get("current_session")
    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    # Validate duration
    if duration and duration > config.voice.max_duration_seconds:
        await update.message.reply_text(
            f"❌ Audio too long ({duration}s). Max: {config.voice.max_duration_seconds}s"
        )
        return

    # Validate file size
    max_bytes = config.voice.max_file_size_mb * 1024 * 1024
    if file_size and file_size > max_bytes:
        await update.message.reply_text(
            f"❌ File too large. Max: {config.voice.max_file_size_mb}MB"
        )
        return

    # Show transcribing status
    status_msg = await update.message.reply_text("🎤 Transcribing...")

    # Download file to temp location
    try:
        file = await context.bot.get_file(file_id)

        # Create temp file with appropriate extension
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            temp_path = Path(tmp.name)

        await file.download_to_drive(temp_path)

        # Get transcription service
        service = context.bot_data.get("transcription_service")
        if not service:
            await status_msg.edit_text(
                "❌ Voice transcription not configured. "
                "Set openai_api_key in voice config."
            )
            return

        # Transcribe
        try:
            result = await service.transcribe(temp_path)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            # Store file_id for retry
            context.user_data["pending_voice_file_id"] = file_id
            await status_msg.edit_text(
                f"❌ Transcription failed: {escape_html(str(e))}",
                parse_mode="HTML",
                reply_markup=build_voice_retry_keyboard(),
            )
            return

        # Check for empty transcript
        if not result.text.strip():
            context.user_data["pending_voice_file_id"] = file_id
            await status_msg.edit_text(
                "❌ Couldn't understand audio. Please try again.",
                reply_markup=build_voice_retry_keyboard(),
            )
            return

        # Store transcript for confirmation
        context.user_data["pending_voice_text"] = result.text
        context.user_data["pending_voice_file_id"] = file_id

        # Show confirmation UI
        await status_msg.edit_text(
            f"🎤 <b>I heard:</b>\n\n<i>{escape_html(result.text)}</i>",
            parse_mode="HTML",
            reply_markup=build_voice_confirm_keyboard(),
        )

    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()
```

Update `src/voice/__init__.py`:

```python
"""Voice message handling module."""
from .transcription import TranscriptionService, TranscriptResult
from .handler import handle_voice, handle_audio

__all__ = ["TranscriptionService", "TranscriptResult", "handle_voice", "handle_audio"]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_voice.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/voice/handler.py src/voice/__init__.py tests/test_voice.py
git commit -m "feat(voice): add voice and audio message handlers"
```

---

## Task 7: Add voice callbacks

**Files:**
- Modify: `src/bot/callbacks.py`
- Add to: `tests/test_callbacks.py`

**Step 1: Write the failing test**

Add to `tests/test_callbacks.py`:

```python
@pytest.mark.asyncio
async def test_voice_send_callback():
    """voice:send callback sends transcript to Claude."""
    from src.bot.callbacks import handle_callback

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "voice:send"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.effective_user.id = 12345

    context = MagicMock()
    context.user_data = {
        "pending_voice_text": "Hello Claude",
        "current_session": MagicMock(),
    }
    context.bot_data = {
        "config": MagicMock(
            streaming=MagicMock(edit_throttle_ms=1000, chunk_size=3800)
        )
    }

    # Mock _execute_claude_prompt to avoid full execution
    with patch("src.bot.callbacks._execute_claude_prompt", new_callable=AsyncMock) as mock_execute:
        await handle_callback(update, context)

        # Should have cleared pending text
        assert "pending_voice_text" not in context.user_data

        # Should call Claude with transcript
        mock_execute.assert_called_once()


@pytest.mark.asyncio
async def test_voice_cancel_callback():
    """voice:cancel callback clears pending transcript."""
    from src.bot.callbacks import handle_callback

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "voice:cancel"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"pending_voice_text": "Hello Claude"}

    await handle_callback(update, context)

    # Should have cleared pending text
    assert "pending_voice_text" not in context.user_data

    # Should show cancelled message
    update.callback_query.edit_message_text.assert_called()
    call_args = str(update.callback_query.edit_message_text.call_args)
    assert "cancelled" in call_args.lower()


@pytest.mark.asyncio
async def test_voice_edit_callback():
    """voice:edit callback prompts user to type correction."""
    from src.bot.callbacks import handle_callback

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "voice:edit"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"pending_voice_text": "Hello Claude"}

    await handle_callback(update, context)

    # Should set editing flag
    assert context.user_data.get("editing_voice_text") is True

    # Should show edit prompt
    update.callback_query.edit_message_text.assert_called()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_callbacks.py::test_voice_cancel_callback -v`
Expected: FAIL (handler not found for voice:cancel)

**Step 3: Write minimal implementation**

Add imports at top of `src/bot/callbacks.py`:

```python
from src.bot.handlers import _execute_claude_prompt
from src.claude.streaming import escape_html
```

Add to the `handlers` dict in `handle_callback` function (around line 52):

```python
        # Voice callbacks
        "voice": _handle_voice_callback,
```

Add the voice callback handler functions at the end of `src/bot/callbacks.py`:

```python
async def _handle_voice_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Route voice callbacks to specific handlers."""
    if value == "send":
        await _handle_voice_send(update, context)
    elif value == "edit":
        await _handle_voice_edit(update, context)
    elif value == "cancel":
        await _handle_voice_cancel(update, context)
    elif value == "retry":
        await _handle_voice_retry(update, context)
    else:
        query = update.callback_query
        await query.edit_message_text(f"❓ Unknown voice action: {value}")


async def _handle_voice_send(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle voice send - send transcript to Claude."""
    query = update.callback_query

    text = context.user_data.pop("pending_voice_text", None)
    context.user_data.pop("pending_voice_file_id", None)

    if not text:
        await query.edit_message_text("❌ No pending voice message.")
        return

    # Show transcript without buttons
    await query.edit_message_text(
        f"🎤 <i>{escape_html(text)}</i>",
        parse_mode="HTML",
    )

    # Execute Claude prompt
    await _execute_claude_prompt(update, context, text)


async def _handle_voice_edit(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle voice edit - prompt user to type correction."""
    query = update.callback_query

    text = context.user_data.get("pending_voice_text", "")

    # Set flag so next text message replaces transcript
    context.user_data["editing_voice_text"] = True

    await query.edit_message_text(
        f"🎤 Current transcript:\n<i>{escape_html(text)}</i>\n\n"
        "Type your corrected message:",
        parse_mode="HTML",
    )


async def _handle_voice_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle voice cancel - discard transcript."""
    query = update.callback_query

    context.user_data.pop("pending_voice_text", None)
    context.user_data.pop("pending_voice_file_id", None)

    await query.edit_message_text("🚫 Voice message cancelled.")


async def _handle_voice_retry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle voice retry - re-transcribe stored file."""
    query = update.callback_query

    file_id = context.user_data.get("pending_voice_file_id")
    if not file_id:
        await query.edit_message_text("❌ No voice message to retry.")
        return

    # Import here to avoid circular import
    from src.voice.handler import _process_audio

    await query.edit_message_text("🎤 Retrying transcription...")

    # Re-process with stored file_id (duration/size already validated)
    await _process_audio(update, context, file_id, duration=None, file_size=None)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_callbacks.py::test_voice_send_callback tests/test_callbacks.py::test_voice_cancel_callback tests/test_callbacks.py::test_voice_edit_callback -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/callbacks.py tests/test_callbacks.py
git commit -m "feat(callbacks): add voice confirmation callbacks"
```

---

## Task 8: Handle edited voice text in handle_message

**Files:**
- Modify: `src/bot/handlers.py:363-398`
- Add to: `tests/test_handlers.py`

**Step 1: Write the failing test**

Add to `tests/test_handlers.py`:

```python
@pytest.mark.asyncio
async def test_handle_message_editing_voice_text():
    """handle_message sends edited voice text to Claude."""
    from src.bot.handlers import handle_message

    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "Corrected transcript"
    update.message.reply_text = AsyncMock(return_value=AsyncMock())
    update.effective_chat.id = 123

    context = MagicMock()
    context.user_data = {
        "editing_voice_text": True,
        "pending_voice_text": "Original transcript",
        "current_session": MagicMock(),
    }
    context.bot_data = {
        "config": MagicMock(
            streaming=MagicMock(edit_throttle_ms=1000, chunk_size=3800)
        )
    }
    context.bot = AsyncMock()

    # Mock _execute_claude_prompt
    with patch("src.bot.handlers._execute_claude_prompt", new_callable=AsyncMock) as mock_execute:
        await handle_message(update, context)

        # Should clear editing flag
        assert "editing_voice_text" not in context.user_data

        # Should clear pending text
        assert "pending_voice_text" not in context.user_data

        # Should call Claude with corrected text
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        assert call_args[0][2] == "Corrected transcript"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_handlers.py::test_handle_message_editing_voice_text -v`
Expected: FAIL (editing_voice_text not handled)

**Step 3: Write minimal implementation**

Modify `handle_message` function in `src/bot/handlers.py`. Add this block after the `pending_command` check (around line 386):

```python
    # Check if editing voice transcript
    if context.user_data.get("editing_voice_text"):
        context.user_data.pop("editing_voice_text")
        context.user_data.pop("pending_voice_text", None)
        context.user_data.pop("pending_voice_file_id", None)
        # User's typed message replaces transcript
        await _execute_claude_prompt(update, context, update.message.text)
        return
```

The full `handle_message` function should now look like:

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

    # Check if editing voice transcript
    if context.user_data.get("editing_voice_text"):
        context.user_data.pop("editing_voice_text")
        context.user_data.pop("pending_voice_text", None)
        context.user_data.pop("pending_voice_file_id", None)
        # User's typed message replaces transcript
        await _execute_claude_prompt(update, context, update.message.text)
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

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_handlers.py::test_handle_message_editing_voice_text -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handlers.py tests/test_handlers.py
git commit -m "feat(handlers): handle edited voice transcript in message handler"
```

---

## Task 9: Register voice handlers in application

**Files:**
- Modify: `src/bot/application.py`
- Modify: `tests/test_application.py`

**Step 1: Write the failing test**

Add to `tests/test_application.py`:

```python
def test_voice_handlers_registered_when_enabled():
    """Voice handlers are registered when voice is enabled."""
    from src.bot.application import create_application
    from src.config.settings import Config, VoiceConfig

    config = Config(
        telegram_token="test-token",
        voice=VoiceConfig(enabled=True, openai_api_key="sk-test"),
    )

    app = create_application(config)

    # Check that voice and audio handlers exist
    from telegram.ext import MessageHandler
    from telegram import filters

    handler_filters = [
        h.filters for h in app.handlers[0]
        if isinstance(h, MessageHandler)
    ]

    # Should have VOICE filter
    voice_found = any(
        hasattr(f, '_name') and 'VOICE' in str(f)
        for f in handler_filters
    )
    audio_found = any(
        hasattr(f, '_name') and 'AUDIO' in str(f)
        for f in handler_filters
    )

    assert voice_found or audio_found, "Voice/Audio handlers not registered"


def test_voice_handlers_not_registered_when_disabled():
    """Voice handlers are not registered when voice is disabled."""
    from src.bot.application import create_application
    from src.config.settings import Config, VoiceConfig

    config = Config(
        telegram_token="test-token",
        voice=VoiceConfig(enabled=False),
    )

    app = create_application(config)

    # Voice handlers should not exist
    from telegram.ext import MessageHandler

    handler_filters = [
        str(h.filters) for h in app.handlers[0]
        if isinstance(h, MessageHandler)
    ]

    voice_found = any('VOICE' in f for f in handler_filters)
    assert not voice_found, "Voice handlers registered when disabled"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_application.py::test_voice_handlers_registered_when_enabled -v`
Expected: FAIL (voice handlers not registered)

**Step 3: Write minimal implementation**

Modify `src/bot/application.py`:

Add imports at the top:

```python
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from src.config.settings import Config
from src.commands import CommandRegistry
from src.mcp import MCPManager
from src.voice import TranscriptionService, handle_voice, handle_audio
```

Modify `post_init` function to initialize TranscriptionService:

```python
async def post_init(application: Application) -> None:
    """Initialize commands after bot is ready."""
    import logging
    logger = logging.getLogger(__name__)

    # Initialize command registry
    registry = application.bot_data["command_registry"]
    count = await registry.refresh(application.bot, project_path=None)
    logger.info(f"Loaded {count} Claude commands at startup")

    # Initialize MCP manager
    config = application.bot_data["config"]
    mcp_manager = MCPManager(config.mcp)
    application.bot_data["mcp_manager"] = mcp_manager

    enabled_count = len(mcp_manager.config.get_enabled_servers())
    logger.info(f"MCP manager initialized: {len(mcp_manager.list_servers())} servers, {enabled_count} enabled")

    # Initialize transcription service if voice enabled
    if config.voice.enabled and config.voice.openai_api_key:
        application.bot_data["transcription_service"] = TranscriptionService(
            api_key=config.voice.openai_api_key,
            default_language=config.voice.language,
        )
        logger.info("Voice transcription service initialized")
    elif config.voice.enabled:
        logger.warning("Voice enabled but no OpenAI API key configured")
```

Modify `create_application` function to register voice handlers. Add after the text message handler (around line 107):

```python
    # Voice message handlers (if enabled)
    if config.voice.enabled:
        app.add_handler(
            MessageHandler(
                filters.VOICE,
                auth_middleware(handle_voice),
            )
        )
        app.add_handler(
            MessageHandler(
                filters.AUDIO,
                auth_middleware(handle_audio),
            )
        )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_application.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/application.py tests/test_application.py
git commit -m "feat(application): register voice handlers and transcription service"
```

---

## Task 10: Add example voice config to config.yaml

**Files:**
- Create: `config.example.yaml` (or modify existing example)

**Step 1: Create/update config example**

If `config.example.yaml` exists, add voice section. Otherwise create it:

```yaml
# TeleClaude Configuration Example
# Copy to ~/.teleclaude/config.yaml and customize

# Telegram whitelist (user IDs)
allowed_users:
  - 123456789

# Project shortcuts
projects:
  myapp: /home/user/projects/myapp
  teleclaude: /home/user/projects/teleclaude

# Claude settings
claude:
  max_turns: 50
  permission_mode: default
  max_budget_usd: 10.0

# Streaming behavior
streaming:
  edit_throttle_ms: 1000
  chunk_size: 3800

# Voice message transcription
voice:
  enabled: true
  openai_api_key: ${OPENAI_API_KEY}  # Set via environment variable
  max_duration_seconds: 600  # 10 minutes
  max_file_size_mb: 20
  language: ru  # Default language for transcription

# Database
database:
  path: ~/.teleclaude/teleclaude.db

# MCP servers (optional)
mcp:
  enabled: true
  config_path: ~/.teleclaude/.mcp.json
```

**Step 2: Commit**

```bash
git add config.example.yaml
git commit -m "docs: add voice config example"
```

---

## Task 11: Run full test suite

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 2: Run type checks (if mypy configured)**

Run: `mypy src/voice/`
Expected: No errors (or only existing errors)

**Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address test/lint issues"
```

---

## Task 12: Update CLAUDE.md documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add voice section to CLAUDE.md**

Add to the "Key Features" section:

```markdown
### Voice Messages
- Send voice notes or audio files to chat with Claude
- Transcription via OpenAI Whisper API (default: Russian)
- Confirmation UI: Send / Edit / Cancel before sending to Claude
- Configurable duration and file size limits
```

Add to "Bot Commands" section:

```markdown
- Voice/Audio messages - Transcribed and sent to Claude with confirmation
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add voice message feature to CLAUDE.md"
```

---

## Summary

**Files created:**
- `src/voice/__init__.py`
- `src/voice/transcription.py`
- `src/voice/handler.py`
- `tests/test_voice.py`

**Files modified:**
- `requirements.txt` - added httpx
- `src/config/settings.py` - added VoiceConfig
- `src/bot/keyboards.py` - added voice confirm/retry keyboards
- `src/bot/callbacks.py` - added voice callbacks
- `src/bot/handlers.py` - handle edited voice text
- `src/bot/application.py` - register handlers and service
- `config.example.yaml` - added voice config example
- `CLAUDE.md` - documented feature
- `tests/test_config.py`
- `tests/test_keyboards.py`
- `tests/test_callbacks.py`
- `tests/test_handlers.py`
- `tests/test_application.py`
