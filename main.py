"""Main entry point for XMR Bridge."""

import asyncio
import logging
import sys
from pathlib import Path

from bridge import XMRBridge
from config import BridgeConfig
from core.errors import BridgeError, ConfigurationError


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

    # Load configuration
    config_path = Path("config.toml")
    if not config_path.exists():
        logger.error(
            "Configuration file not found. "
            "Please copy config.example.toml to config.toml and edit it."
        )
        return 1

    try:
        config = BridgeConfig.from_file(config_path)
        config.validate()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Create and run bridge
    try:
        bridge = XMRBridge(config)
        await bridge.run()
        return 0
    except BridgeError as e:
        logger.error(f"Bridge error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


def main() -> None:
    """Main entry point."""
    # Setup logging from environment or default to INFO
    import os
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting XMR Bridge...")

    # Run async main
    exit_code = asyncio.run(async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
