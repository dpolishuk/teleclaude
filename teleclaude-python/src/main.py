"""TeleClaude entry point."""
import asyncio
import logging
import os

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable required")
        return

    logger.info("TeleClaude starting...")
    logger.info("Token found, bot ready to initialize")


if __name__ == "__main__":
    asyncio.run(main())
