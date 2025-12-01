"""Telegram callback query handlers."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.storage.database import get_session
from src.storage.repository import SessionRepository
from src.claude.permissions import get_permission_manager
from src.claude.sessions import scan_sessions
from src.bot.keyboards import build_session_keyboard, build_mode_keyboard

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

    # Store session_id in context for later use
    context.user_data["resume_session_id"] = value

    # Build mode selection keyboard
    keyboard = build_mode_keyboard(value)
    await query.edit_message_text(
        "🔀 Choose resume mode:\n\n"
        "Fork (safe): Creates a new branch from session history\n"
        "Continue (same): Continues the exact same session thread",
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

    # Store mode and session_id in context for Task 4
    context.user_data["resume_session_id"] = session_id
    context.user_data["resume_mode"] = mode

    # Show confirmation message
    mode_text = "fork mode (new branch)" if mode == "fork" else "continue mode (same session)"
    await query.edit_message_text(
        f"⏳ Resuming session... ({mode_text})\n\n"
        "Session will be loaded shortly."
    )

    # TODO: Actual resume execution will be handled by Task 4
