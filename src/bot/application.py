"""Telegram bot application setup."""
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from src.config.settings import Config
from src.commands import CommandRegistry
from .middleware import auth_middleware
from .handlers import (
    start,
    help_cmd,
    new_session,
    continue_session,
    list_sessions,
    switch_session,
    show_cost,
    cancel,
    cd,
    ls,
    pwd,
    git,
    export_session,
    handle_message,
    refresh_commands,
)
from .callbacks import handle_callback
from .command_handler import handle_claude_command


def create_application(config: Config) -> Application:
    """Create and configure Telegram Application."""
    app = Application.builder().token(config.telegram_token).build()

    # Store config in bot_data for handlers to access
    app.bot_data["config"] = config

    # Initialize command registry
    app.bot_data["command_registry"] = CommandRegistry()

    # Command handlers with auth middleware
    commands = [
        ("start", start),
        ("help", help_cmd),
        ("new", new_session),
        ("continue", continue_session),
        ("sessions", list_sessions),
        ("switch", switch_session),
        ("cost", show_cost),
        ("cancel", cancel),
        ("cd", cd),
        ("ls", ls),
        ("pwd", pwd),
        ("git", git),
        ("export", export_session),
        ("refresh", refresh_commands),
    ]

    for command, handler in commands:
        app.add_handler(CommandHandler(command, auth_middleware(handler)))

    # Message handler for Claude interactions
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            auth_middleware(handle_message),
        )
    )

    # Dynamic Claude command handler (catch-all for unknown commands)
    app.add_handler(
        MessageHandler(
            filters.COMMAND,
            auth_middleware(handle_claude_command),
        )
    )

    # Callback handler for inline keyboards (with auth)
    app.add_handler(CallbackQueryHandler(auth_middleware(handle_callback)))

    return app
