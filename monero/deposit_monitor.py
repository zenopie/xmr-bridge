"""Monitor Monero blockchain for deposits."""

import asyncio
import logging
from typing import Optional, Callable

from monero.node import MoneroNode
from core.types import Deposit

logger = logging.getLogger(__name__)


class MoneroDepositMonitor:
    """Monitors the Monero blockchain for incoming deposits."""

    def __init__(
        self,
        node: MoneroNode,
        min_confirmations: int = 10,
        callback: Optional[Callable[[Deposit], None]] = None
    ):
        """Initialize deposit monitor.

        Args:
            node: MoneroNode instance to use for blockchain queries
            min_confirmations: Minimum confirmations before processing deposit
            callback: Optional callback function to call when deposit is detected
        """
        self.node = node
        self.min_confirmations = min_confirmations
        self.callback = callback
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start monitoring for deposits."""
        if self._running:
            logger.warning("Deposit monitor already running")
            return

        logger.info("Starting deposit monitor")
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop monitoring for deposits."""
        if not self._running:
            return

        logger.info("Stopping deposit monitor")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        last_height = await self.node.get_block_height()

        while self._running:
            try:
                current_height = await self.node.get_block_height()

                # Process new blocks
                if current_height > last_height:
                    logger.info(
                        f"New blocks detected: {last_height + 1} to {current_height}"
                    )

                    for height in range(last_height + 1, current_height + 1):
                        await self._process_block(height)

                    last_height = current_height

                # Wait before checking again
                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in deposit monitor loop: {e}")
                await asyncio.sleep(10)

    async def _process_block(self, height: int) -> None:
        """Process a block for deposits.

        Args:
            height: Block height to process
        """
        try:
            block = await self.node.get_block(height)
            # TODO: Parse block for relevant transactions
            # TODO: Check transactions for deposits to our addresses
            # TODO: Verify confirmations
            # TODO: Call callback if deposit is confirmed

            logger.debug(f"Processed block {height}")

        except Exception as e:
            logger.error(f"Error processing block {height}: {e}")
