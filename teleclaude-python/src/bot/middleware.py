"""Bot middleware for authentication and logging."""
from functools import wraps
from typing import Callable, TypeVar

from telegram import Update
from telegram.ext import ContextTypes

F = TypeVar("F", bound=Callable)


def auth_middleware(handler: F) -> F:
    """Decorator to check user authentication."""

    @wraps(handler)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        config = context.bot_data.get("config")

        if config is None:
            await update.message.reply_text("⚠️ Bot not configured")
            return

        user_id = update.effective_user.id

        if not config.is_user_allowed(user_id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        return await handler(update, context)

    return wrapper
