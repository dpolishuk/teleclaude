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


async def main() -> None:
    """Main entry point."""
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable required")
        return

    # Load configuration
    config_path = Path.home() / ".teleclaude" / "config.yaml"
    config = load_config(config_path)
    config.telegram_token = token

    # Initialize database
    await init_database(config.database.path)

    # Create and run bot
    app = create_application(config)

    logger.info("TeleClaude starting...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
