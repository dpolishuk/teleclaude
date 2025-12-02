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
        async with httpx.AsyncClient(timeout=120.0) as client:
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
                )
            response.raise_for_status()
            data = response.json()

            return TranscriptResult(
                text=data["text"].strip(),
                duration_seconds=data.get("duration", 0),
                language=data.get("language", self.default_language),
            )
