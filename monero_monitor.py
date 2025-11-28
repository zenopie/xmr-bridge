"""Monero blockchain monitoring for deposits."""

import asyncio
import logging
from typing import Callable, Set
from monero_wallet import MoneroWalletManager, MoneroDeposit

logger = logging.getLogger(__name__)


class MoneroDepositMonitor:
    """Monitors the Monero blockchain for incoming deposits."""

    def __init__(
        self,
        wallet_manager: MoneroWalletManager,
        min_confirmations: int = 10,
        poll_interval: int = 60,
        on_deposit: Callable[[MoneroDeposit], None] = None
    ):
        """Initialize the deposit monitor.

        Args:
            wallet_manager: Monero wallet manager
            min_confirmations: Minimum confirmations before processing deposit
            poll_interval: Seconds between blockchain checks
            on_deposit: Callback for confirmed deposits
        """
        self.wallet_manager = wallet_manager
        self.min_confirmations = min_confirmations
        self.poll_interval = poll_interval
        self.on_deposit = on_deposit

        # Track processed transaction hashes
        self.processed_txs: Set[str] = set()

        # Last checked block height
        self.last_checked_height = 0

        # Running flag
        self.running = False

        logger.info(
            f"Initialized deposit monitor "
            f"(min_confirmations={min_confirmations}, poll_interval={poll_interval}s)"
        )

    async def start(self) -> None:
        """Start monitoring for deposits."""
        logger.info("Starting deposit monitor...")
        self.running = True

        # Get current block height as starting point
        self.last_checked_height = await self.wallet_manager.get_block_height()
        logger.info(f"Starting from block height {self.last_checked_height}")

        # Start monitoring loop
        asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop monitoring."""
        logger.info("Stopping deposit monitor...")
        self.running = False

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                await self._check_deposits()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)

            # Wait before next check
            await asyncio.sleep(self.poll_interval)

    async def _check_deposits(self) -> None:
        """Check for new deposits."""
        # Get current block height
        current_height = await self.wallet_manager.get_block_height()

        if current_height == 0:
            logger.warning("Could not get block height")
            return

        # Get all transfers since last check
        deposits = await self.wallet_manager.get_transfers(
            min_height=self.last_checked_height
        )

        logger.debug(
            f"Checked blocks {self.last_checked_height} to {current_height}, "
            f"found {len(deposits)} transfers"
        )

        # Process each deposit
        for deposit in deposits:
            await self._process_deposit(deposit, current_height)

        # Update last checked height
        self.last_checked_height = current_height

    async def _process_deposit(self, deposit: MoneroDeposit, current_height: int) -> None:
        """Process a potential deposit.

        Args:
            deposit: Deposit information
            current_height: Current blockchain height
        """
        # Skip if already processed
        if deposit.tx_hash in self.processed_txs:
            return

        # Calculate confirmations
        confirmations = current_height - deposit.block_height + 1

        logger.info(
            f"Deposit {deposit.tx_hash[:16]}... "
            f"has {confirmations}/{self.min_confirmations} confirmations"
        )

        # Check if deposit has enough confirmations
        if confirmations < self.min_confirmations:
            logger.debug(f"Deposit {deposit.tx_hash[:16]}... needs more confirmations")
            return

        # Get user identifier for this subaddress
        user_id = self.wallet_manager.get_user_for_subaddress(
            deposit.subaddress_index[0],
            deposit.subaddress_index[1]
        )

        if not user_id:
            logger.error(
                f"No user mapping for subaddress "
                f"{deposit.subaddress_index[0]}/{deposit.subaddress_index[1]}"
            )
            return

        logger.info(
            f"Confirmed deposit: {deposit.amount} piconeros "
            f"from tx {deposit.tx_hash[:16]}... for user {user_id[:8]}..."
        )

        # Mark as processed
        self.processed_txs.add(deposit.tx_hash)

        # Call callback
        if self.on_deposit:
            try:
                if asyncio.iscoroutinefunction(self.on_deposit):
                    await self.on_deposit(deposit)
                else:
                    self.on_deposit(deposit)
            except Exception as e:
                logger.error(f"Error in deposit callback: {e}", exc_info=True)
