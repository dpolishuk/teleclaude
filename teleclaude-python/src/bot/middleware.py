"""Bot middleware for authentication and logging."""
from functools import wraps
from typing import Callable, TypeVar

from telegram import Update
from telegram.ext import ContextTypes

F = TypeVar("F", bound=Callable)


async def _send_error(update: Update, message: str) -> None:
    """Send error message via appropriate channel (message or callback)."""
    if update.message:
        await update.message.reply_text(message)
    elif update.callback_query:
        await update.callback_query.answer(message, show_alert=True)


def auth_middleware(handler: F) -> F:
    """Decorator to check user authentication.

    Works with both message handlers and callback query handlers.
    """

    @wraps(handler)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        config = context.bot_data.get("config")

        if config is None:
            await _send_error(update, "⚠️ Bot not configured")
            return

        user_id = update.effective_user.id

        if not config.is_user_allowed(user_id):
            await _send_error(update, "⛔ Unauthorized")
            return

        return await handler(update, context)

    return wrapper
