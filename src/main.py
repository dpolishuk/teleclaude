"""TeleClaude entry point."""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from src.config.settings import load_config
from src.storage.database import init_database
from src.bot.application import create_application

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def init_app():
    """Initialize database and return configured app."""
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable required")
        return None

    # Load configuration
    config_path = Path.home() / ".teleclaude" / "config.yaml"
    config = load_config(config_path)
    config.telegram_token = token

    # Initialize database
    await init_database(config.database.path)

    # Create app
    return create_application(config)


def main() -> None:
    """Main entry point."""
    # Initialize app with async (for database)
    app = asyncio.run(init_app())

    if app is None:
        return

    logger.info("TeleClaude starting...")
    # run_polling() manages its own event loop
    app.run_polling()


if __name__ == "__main__":
    main()
