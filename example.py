#!/usr/bin/env python3
"""Example script demonstrating bridge usage."""

import asyncio
import logging
from bridge import SimpleBridge, BridgeConfig
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def example_generate_address():
    """Example: Generate a deposit address for a user."""
    # Load environment variables
    load_dotenv()

    # Create bridge
    config = BridgeConfig.from_env()
    bridge = SimpleBridge(config)

    # Start the bridge (initializes database and clients)
    await bridge.db.start()
    await bridge.wallet_manager.start()

    # Generate deposit address for a Secret Network user
    secret_address = "secret1abc123def456ghi789jkl012mno345pqr678st"
    deposit_address = await bridge.generate_deposit_address(secret_address)

    logger.info(f"User {secret_address} should deposit XMR to: {deposit_address}")

    # Cleanup
    await bridge.wallet_manager.stop()
    await bridge.db.stop()


async def run_bridge():
    """Example: Run the full bridge."""
    # Load environment variables
    load_dotenv()

    # Create and run bridge
    config = BridgeConfig.from_env()
    bridge = SimpleBridge(config)

    logger.info("Starting bridge...")
    await bridge.run()


if __name__ == "__main__":
    # Uncomment the example you want to run:

    # Example 1: Generate a deposit address
    # asyncio.run(example_generate_address())

    # Example 2: Run the full bridge
    asyncio.run(run_bridge())
