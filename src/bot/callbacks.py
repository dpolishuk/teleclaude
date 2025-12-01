"""Telegram callback query handlers."""
from telegram import Update
from telegram.ext import ContextTypes


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

    if value == "other":
        await query.edit_message_text(
            "📁 Send me the path to your project directory."
        )
        context.user_data["awaiting_path"] = True
        return

    if value and value in config.projects:
        project_path = config.projects[value]
        # TODO: Create session
        await query.edit_message_text(
            f"✅ Starting session for `{value}`\n\n"
            f"Path: `{project_path}`\n\n"
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
