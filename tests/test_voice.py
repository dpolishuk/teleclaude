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


@pytest.mark.asyncio
async def test_process_audio_works_with_callback_context():
    """_process_audio works with callback query context (for retry)."""
    from src.voice.handler import _process_audio

    # Simulate callback context (no update.message, only update.callback_query)
    update = MagicMock()
    update.message = None
    update.callback_query = MagicMock()
    update.callback_query.message = AsyncMock()
    update.callback_query.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"current_session": MagicMock()}
    context.bot_data = {
        "config": MagicMock(
            voice=MagicMock(max_duration_seconds=600, max_file_size_mb=20)
        ),
        "transcription_service": None,  # Not configured
    }

    await _process_audio(update, context, file_id="abc", duration=None, file_size=None)

    # Should use callback_query.message to reply
    update.callback_query.message.reply_text.assert_called_once()
    call_args = str(update.callback_query.message.reply_text.call_args)
    assert "not configured" in call_args.lower()
