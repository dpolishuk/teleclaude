"""Telegram callback query handlers.

TODO (Tasks 5-8): References to removed fields (claude_session_id, project_name,
current_directory) are intentionally left for later tasks which will update this file.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.storage.database import get_session
from src.storage.repository import SessionRepository
from src.claude.permissions import get_permission_manager
from src.claude.sessions import scan_sessions, decode_project_name
from src.bot.keyboards import build_session_keyboard, build_mode_keyboard, build_models_keyboard, MODELS
from src.bot.handlers import _execute_claude_prompt
from src.claude.streaming import escape_html

logger = logging.getLogger(__name__)


def parse_callback_data(data: str) -> tuple[str, str | None]:
    """Parse callback data into action and value."""
    if ":" in data:
        action, _, value = data.partition(":")
        return action, value
    return data, None


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()

    action, value = parse_callback_data(query.data)

    handlers = {
        "cancel": _handle_cancel,
        "project": _handle_project_select,
        "session": _handle_session_select,
        "approve": _handle_approve,
        "deny": _handle_deny,
        "confirm": _handle_confirm,
        # Permission callbacks
        "perm_allow": _handle_permission_allow,
        "perm_always": _handle_permission_always,
        "perm_deny": _handle_permission_deny,
        # Resume callbacks
        "resume_project": _handle_resume_project,
        "resume_session": _handle_resume_session,
        "resume_mode": _handle_resume_mode,
        # /sessions command callback
        "select_session": _handle_select_session,
        # /models command callback
        "select_model": _handle_select_model,
        # Voice callbacks
        "voice": _handle_voice_callback,
    }

    handler = handlers.get(action)
    if handler:
        await handler(update, context, value)
    else:
        await query.edit_message_text(f"❓ Unknown action: {action}")


async def _handle_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle cancel button press."""
    query = update.callback_query
    client = context.user_data.get("active_client")

    if client:
        try:
            await client.interrupt()
        except Exception:
            pass
        finally:
            context.user_data.pop("active_client", None)

    await query.edit_message_text("🛑 Operation cancelled.")


async def _handle_project_select(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle project selection callback."""
    query = update.callback_query
    config = context.bot_data.get("config")
    user_id = update.effective_user.id

    if value == "other":
        await query.edit_message_text(
            "📁 Send me the path to your project directory."
        )
        context.user_data["awaiting_path"] = True
        return

    if value and value in config.projects:
        project_path = config.projects[value]

        # Create session in database
        async with get_session() as db:
            repo = SessionRepository(db)
            session = await repo.create_session(
                telegram_user_id=user_id,
                project_path=project_path,
                project_name=value,
            )
            # Store session in user_data for quick access
            context.user_data["current_session"] = session
            # Store session ID separately for persistence across restarts
            context.user_data["current_session_id"] = session.id
            context.user_data["current_project_path"] = project_path

        # Refresh commands for this project
        registry = context.bot_data.get("command_registry")
        cmd_count = await registry.refresh(query.get_bot(), project_path=project_path)

        await query.edit_message_text(
            f"✅ Created session for `{value}`\n\n"
            f"📂 Path: `{project_path}`\n"
            f"📋 {cmd_count} Claude command(s) available.\n\n"
            "Send a message to chat with Claude."
        )
    else:
        await query.edit_message_text(f"❌ Project not found: {value}")


async def _handle_session_select(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle session selection callback."""
    query = update.callback_query

    if value:
        # TODO: Load and switch to session
        await query.edit_message_text(f"🔄 Switched to session: {value[:8]}...")
    else:
        await query.edit_message_text("❌ Invalid session.")


async def _handle_approve(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle approval callback."""
    query = update.callback_query

    if value:
        # TODO: Approve the operation
        await query.edit_message_text(f"✅ Approved operation: {value[:8]}...")
    else:
        await query.edit_message_text("❌ Invalid approval request.")


async def _handle_deny(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle denial callback."""
    query = update.callback_query

    if value:
        # TODO: Deny the operation
        await query.edit_message_text(f"❌ Denied operation: {value[:8]}...")
    else:
        await query.edit_message_text("❌ Invalid denial request.")


async def _handle_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle confirmation callback."""
    query = update.callback_query

    if value:
        # TODO: Execute confirmed action
        await query.edit_message_text(f"✅ Confirmed: {value}")
    else:
        await query.edit_message_text("❌ Invalid confirmation.")


async def _handle_permission_allow(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle permission allow callback."""
    query = update.callback_query
    manager = get_permission_manager()

    logger.info(f"Permission allow callback: request_id={value}")

    if value:
        success, message = manager.handle_permission_response(value, "allow")
        logger.info(f"Permission response: success={success}, message={message}")
        await query.edit_message_text(message)
    else:
        await query.edit_message_text("❌ Invalid permission request.")


async def _handle_permission_always(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle permission always-allow callback."""
    query = update.callback_query
    manager = get_permission_manager()

    logger.info(f"Permission always callback: request_id={value}")

    if value:
        success, message = manager.handle_permission_response(value, "always")
        logger.info(f"Permission response: success={success}, message={message}")
        await query.edit_message_text(message)
    else:
        await query.edit_message_text("❌ Invalid permission request.")


async def _handle_permission_deny(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle permission deny callback."""
    query = update.callback_query
    manager = get_permission_manager()

    logger.info(f"Permission deny callback: request_id={value}")

    if value:
        success, message = manager.handle_permission_response(value, "deny")
        logger.info(f"Permission response: success={success}, message={message}")
        await query.edit_message_text(message)
    else:
        await query.edit_message_text("❌ Invalid permission request.")


async def _handle_resume_project(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle resume project selection callback."""
    query = update.callback_query

    if not value:
        await query.edit_message_text("❌ Invalid project selection.")
        return

    # Store project name for later use
    context.user_data["resume_project_name"] = value

    # Scan sessions for the selected project
    sessions = scan_sessions(value)

    if not sessions:
        await query.edit_message_text("❌ No sessions found for this project.")
        return

    # Build session selection keyboard
    keyboard = build_session_keyboard(sessions)
    await query.edit_message_text(
        "📋 Select a session to resume:",
        reply_markup=keyboard,
    )


async def _handle_resume_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle resume session selection callback."""
    query = update.callback_query

    if not value:
        await query.edit_message_text("❌ Invalid session selection.")
        return

    # Get the session info to retrieve preview
    project_name = context.user_data.get("resume_project_name")
    if not project_name:
        await query.edit_message_text("❌ Project information lost. Please start over with /resume")
        return

    # Scan sessions again to get the full session info
    sessions = scan_sessions(project_name)
    session_info = next((s for s in sessions if s.session_id == value), None)

    if not session_info:
        await query.edit_message_text("❌ Session not found.")
        return

    # Store session_id and preview in context for later use
    context.user_data["resume_session_id"] = value
    context.user_data["resume_session_preview"] = session_info.preview

    # Build mode selection keyboard
    keyboard = build_mode_keyboard(value)

    # Create message with session preview
    preview_text = session_info.preview if session_info.preview else "(no preview)"
    await query.edit_message_text(
        f"🔀 Choose resume mode:\n\n"
        f"Session: \"{preview_text}\"\n\n"
        f"Fork (safe): Creates a new branch from session history\n"
        f"Continue (same): Continues the exact same session thread",
        reply_markup=keyboard,
    )


async def _handle_resume_mode(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle resume mode selection callback."""
    query = update.callback_query

    if not value:
        await query.edit_message_text("❌ Invalid mode selection.")
        return

    # Parse value as "session_id:mode"
    if ":" not in value:
        await query.edit_message_text("❌ Invalid mode data format.")
        return

    session_id, mode = value.split(":", 1)

    if mode not in ("fork", "continue"):
        await query.edit_message_text("❌ Invalid mode selection.")
        return

    # Get project name from context
    project_name = context.user_data.get("resume_project_name")
    if not project_name:
        await query.edit_message_text("❌ Project information lost. Please start over with /resume")
        return

    # Decode project name to get project path
    project_path = decode_project_name(project_name)

    # Store mode and session_id in context
    context.user_data["resume_session_id"] = session_id
    context.user_data["resume_mode"] = mode

    # Create TeleClaude Session record in database
    user_id = update.effective_user.id
    async with get_session() as db:
        repo = SessionRepository(db)
        session = await repo.create_session(
            telegram_user_id=user_id,
            project_path=project_path,
            current_directory=project_path,
            claude_session_id=session_id,
        )
        # Store session in user_data for quick access
        context.user_data["current_session"] = session
        # Store session ID separately for persistence across restarts
        context.user_data["current_session_id"] = session.id
        context.user_data["current_project_path"] = project_path

    # Refresh commands for this project
    registry = context.bot_data.get("command_registry")
    if registry:
        await registry.refresh(query.get_bot(), project_path=project_path)

    # Show confirmation message
    mode_text = "forked (new branch)" if mode == "fork" else "continued (same session)"
    await query.edit_message_text(
        f"✅ Session resumed! ({mode_text})\n\n"
        f"📂 Project: {project_path}\n\n"
        "You can now continue chatting with Claude."
    )


async def _handle_select_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle session selection from /sessions command - resume immediately."""
    query = update.callback_query

    if not value:
        await query.edit_message_text("❌ Invalid session selection.")
        return

    # Get current session to know project path
    current_session = context.user_data.get("current_session")
    if not current_session:
        await query.edit_message_text("❌ No active project. Use /new first.")
        return

    # Update current session with the selected Claude session_id
    current_session.claude_session_id = value

    # Persist to database
    async with get_session() as db:
        repo = SessionRepository(db)
        await repo.set_claude_session_id(current_session.id, value)

    logger.info(f"Session selected: {value[:20]}... for project {current_session.project_path}")

    await query.edit_message_text(
        f"✅ Session resumed!\n\n"
        f"📂 Project: {current_session.project_path}\n\n"
        "You can now continue chatting with Claude."
    )


async def _handle_select_model(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str | None
) -> None:
    """Handle model selection from /models command."""
    query = update.callback_query

    if not value or value not in MODELS:
        await query.edit_message_text("❌ Invalid model selection.")
        return

    # Check if already selected (avoid "message not modified" error)
    current_model = context.user_data.get("selected_model")
    if current_model == value:
        await query.answer(f"Already using {value}")
        return

    # Store model preference in user_data for persistence
    context.user_data["selected_model"] = value

    logger.info(f"Model selected: {value} for user {update.effective_user.id}")

    # Update message with new keyboard showing selection
    keyboard = build_models_keyboard(value)
    await query.edit_message_text(
        f"Current model: {value}",
        reply_markup=keyboard
    )


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
