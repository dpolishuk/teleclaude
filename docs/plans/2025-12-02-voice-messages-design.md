# Voice Messages Design

## Overview

Add voice message support to TeleClaude, allowing users to speak to Claude instead of typing. Voice and audio files are transcribed using OpenAI Whisper API, then sent to Claude as text.

## User Flow

1. User sends voice note or audio file in Telegram
2. Bot validates file size and duration against configured limits
3. Bot shows "Transcribing..." status
4. Audio is sent to OpenAI Whisper API
5. Bot shows transcript with confirmation buttons: **Send / Edit / Cancel**
6. On Send: transcript is sent to Claude as normal prompt
7. On Edit: user types corrected text, then it's sent to Claude
8. On Cancel: transcript is discarded

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram User                        │
│                  sends voice/audio                      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              VoiceHandler                               │
│  - Validates file size/duration against config limits   │
│  - Downloads .ogg/.mp3/etc to temp file                 │
│  - Sends "Transcribing..." status                       │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│           TranscriptionService                          │
│  - Calls OpenAI Whisper API                             │
│  - Converts audio → text                                │
│  - Returns transcript + duration/language metadata      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│            Confirmation UI                              │
│  "I heard:"                                             │
│  "<transcript text>"                                    │
│  [Send] [Edit] [Cancel]                                 │
└─────────────────┬───────────────────────────────────────┘
                  │ User taps Send
                  ▼
┌─────────────────────────────────────────────────────────┐
│     Existing: _execute_claude_prompt()                  │
│     (handlers.py)                                       │
└─────────────────────────────────────────────────────────┘
```

## New Files

| File | Purpose |
|------|---------|
| `src/voice/__init__.py` | Module init |
| `src/voice/transcription.py` | `TranscriptionService` - OpenAI Whisper API wrapper |
| `src/voice/handler.py` | `handle_voice()`, `handle_audio()` - Telegram handlers |

## Modified Files

| File | Changes |
|------|---------|
| `src/config/settings.py` | Add `VoiceConfig` dataclass |
| `src/bot/application.py` | Register voice/audio handlers, init TranscriptionService |
| `src/bot/callbacks.py` | Add `voice_confirm_send`, `voice_confirm_edit`, `voice_confirm_cancel` |
| `src/bot/keyboards.py` | Add `build_voice_confirm_keyboard()`, `build_voice_retry_keyboard()` |
| `src/bot/handlers.py` | Handle `editing_voice_text` state in `handle_message()` |

## Configuration

```yaml
voice:
  enabled: true
  openai_api_key: ${OPENAI_API_KEY}
  max_duration_seconds: 600  # 10 minutes
  max_file_size_mb: 20
  language: "ru"  # Default Russian, auto-detect if null
```

## TranscriptionService

```python
@dataclass
class TranscriptResult:
    text: str
    duration_seconds: float
    language: str

class TranscriptionService:
    WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"

    def __init__(self, api_key: str, default_language: str = "ru"):
        self.api_key = api_key
        self.default_language = default_language

    async def transcribe(self, audio_path: Path, language: str | None = None) -> TranscriptResult:
        # POST to Whisper API with audio file
        # Returns transcript text, duration, detected language
```

Uses `httpx` async client with 120s timeout for longer files.

## Voice Handler

```python
async def handle_voice(update, context):
    voice = update.message.voice
    await _process_audio(update, context, voice.file_id, voice.duration, voice.file_size)

async def handle_audio(update, context):
    audio = update.message.audio
    await _process_audio(update, context, audio.file_id, audio.duration, audio.file_size)

async def _process_audio(update, context, file_id, duration, file_size):
    # 1. Check session exists
    # 2. Validate duration and file size limits
    # 3. Download to temp file
    # 4. Transcribe via TranscriptionService
    # 5. Cleanup temp file
    # 6. Show confirmation UI with transcript
    # 7. Store transcript in user_data["pending_voice_text"]
    # 8. Store file_id in user_data["pending_voice_file_id"] for retry
```

## Confirmation Callbacks

| Callback | Action |
|----------|--------|
| `voice:send` | Pop `pending_voice_text`, call `_execute_claude_prompt()` |
| `voice:edit` | Set `editing_voice_text` flag, prompt user to type corrected text |
| `voice:cancel` | Pop `pending_voice_text`, show cancelled message |
| `voice:retry` | Re-download and transcribe using stored `file_id` |

## Error Handling

| Scenario | Handling |
|----------|----------|
| OpenAI API key missing | Voice handlers disabled at startup, log warning |
| Transcription fails | Show error with retry button |
| Empty transcript | Show "Couldn't understand audio" message |
| Network timeout | 120s timeout, friendly error message |
| Temp file cleanup | Always in `finally` block |
| Voice while another pending | Replace previous pending transcript |
| Session expires mid-confirmation | Check session in callbacks |

## Dependencies

- `httpx` - async HTTP client for Whisper API (add to requirements)

## Decisions Made

- **Transcription service**: OpenAI Whisper API (simple, reliable, reasonable cost)
- **Scope**: Both voice notes and audio files supported
- **User flow**: Show transcript with Send/Edit/Cancel confirmation
- **API key**: Shared server config (`OPENAI_API_KEY`)
- **Default language**: Russian (`ru`)
- **Limits**: Configurable, default 10 min / 20MB
