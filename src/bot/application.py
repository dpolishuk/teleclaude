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
from src.mcp import MCPManager
from src.voice import TranscriptionService, handle_voice, handle_audio
from .middleware import auth_middleware
from .handlers import (
    start,
    help_cmd,
    new_session,
    continue_session,
    list_sessions,
    switch_session,
    select_model,
    show_cost,
    cancel,
    cd,
    ls,
    pwd,
    git,
    export_session,
    handle_message,
    refresh_commands,
    mcp_cmd,
    resume_cmd,
)
from .callbacks import handle_callback
from .command_handler import handle_claude_command


async def post_init(application: Application) -> None:
    """Initialize commands after bot is ready."""
    import logging
    logger = logging.getLogger(__name__)

    # Initialize command registry
    registry = application.bot_data["command_registry"]
    count = await registry.refresh(application.bot, project_path=None)
    logger.info(f"Loaded {count} Claude commands at startup")

    # Initialize MCP manager
    config = application.bot_data["config"]
    mcp_manager = MCPManager(config.mcp)
    application.bot_data["mcp_manager"] = mcp_manager

    enabled_count = len(mcp_manager.config.get_enabled_servers())
    logger.info(f"MCP manager initialized: {len(mcp_manager.list_servers())} servers, {enabled_count} enabled")

    # Initialize transcription service if voice enabled
    if config.voice.enabled and config.voice.openai_api_key:
        application.bot_data["transcription_service"] = TranscriptionService(
            api_key=config.voice.openai_api_key,
            default_language=config.voice.language,
        )
        logger.info("Voice transcription service initialized")
    elif config.voice.enabled:
        logger.warning("Voice enabled but no OpenAI API key configured")


def create_application(config: Config) -> Application:
    """Create and configure Telegram Application."""
    # Enable concurrent_updates to allow callback queries to be processed
    # while another handler (like Claude message processing) is running.
    # This is critical for permission prompts to work - without it,
    # button clicks can't be processed while waiting for permission response.
    app = (
        Application.builder()
        .token(config.telegram_token)
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )

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
        ("models", select_model),
        ("cost", show_cost),
        ("cancel", cancel),
        ("cd", cd),
        ("ls", ls),
        ("pwd", pwd),
        ("git", git),
        ("export", export_session),
        ("refresh", refresh_commands),
        ("mcp", mcp_cmd),
        ("resume", resume_cmd),
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

    # Voice message handlers (if enabled)
    if config.voice.enabled:
        app.add_handler(
            MessageHandler(
                filters.VOICE,
                auth_middleware(handle_voice),
            )
        )
        app.add_handler(
            MessageHandler(
                filters.AUDIO,
                auth_middleware(handle_audio),
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
