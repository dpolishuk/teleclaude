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
