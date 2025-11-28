"""Main entry point for Simple XMR Bridge."""

import asyncio
import logging
import sys
from pathlib import Path

from bridge import SimpleBridge, BridgeConfig
from dotenv import load_dotenv


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("xmr-bridge.log"),
        ],
    )


async def async_main() -> int:
    """Async main function.

    Returns:
        Exit code
    """
    logger = logging.getLogger(__name__)

    # Load environment variables
    env_path = Path(".env")
    if not env_path.exists():
        logger.error(
            "Environment file not found. "
            "Please copy .env.example to .env and configure it."
        )
        return 1

    load_dotenv(env_path)

    try:
        # Load configuration from environment
        config = BridgeConfig.from_env()
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Create and run bridge
    try:
        bridge = SimpleBridge(config)
        await bridge.run()
        return 0
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


def main() -> None:
    """Main entry point."""
    import os

    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting Simple XMR Bridge...")

    exit_code = asyncio.run(async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
