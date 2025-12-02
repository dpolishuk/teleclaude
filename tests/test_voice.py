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
