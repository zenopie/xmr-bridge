"""Simple Monero to Secret Network bridge."""

import asyncio
import logging
import os
from typing import Dict, Set
from dataclasses import dataclass

from monero_wallet import MoneroWalletManager, MoneroDeposit
from monero_monitor import MoneroDepositMonitor
from secret_client import SecretNetworkClient, BurnEvent
from database import BridgeDatabase

logger = logging.getLogger(__name__)


@dataclass
class BridgeConfig:
    """Bridge configuration."""

    # Monero settings
    monero_rpc_url: str
    monero_network: str
    monero_seed: str = ""  # 25-word Monero seed
    monero_wallet_address: str = ""  # Can be derived from seed or provided
    monero_view_key: str = ""  # Can be derived from seed or provided
    monero_spend_key: str = ""  # Can be derived from seed or provided

    # Monero Wallet RPC (for withdrawals)
    monero_wallet_rpc_url: str = ""
    monero_wallet_rpc_user: str = ""
    monero_wallet_rpc_password: str = ""

    # Secret Network settings
    secret_rpc_url: str
    secret_chain_id: str
    secret_mnemonic: str
    sxmr_contract_address: str
    sxmr_contract_hash: str

    # Bridge settings
    min_confirmations: int = 10
    poll_interval: int = 60
    database_path: str = "bridge.db"

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        """Load configuration from environment variables."""
        return cls(
            monero_rpc_url=os.getenv("MONERO_RPC_URL", "http://node.moneroworld.com:18089/json_rpc"),
            monero_network=os.getenv("MONERO_NETWORK", "mainnet"),
            monero_seed=os.getenv("MONERO_SEED", ""),
            monero_wallet_address=os.getenv("MONERO_WALLET_ADDRESS", ""),
            monero_view_key=os.getenv("MONERO_VIEW_KEY", ""),
            monero_spend_key=os.getenv("MONERO_SPEND_KEY", ""),
            monero_wallet_rpc_url=os.getenv("MONERO_WALLET_RPC_URL", "http://127.0.0.1:18083/json_rpc"),
            monero_wallet_rpc_user=os.getenv("MONERO_WALLET_RPC_USER", ""),
            monero_wallet_rpc_password=os.getenv("MONERO_WALLET_RPC_PASSWORD", ""),
            secret_rpc_url=os.getenv("SECRET_NETWORK_RPC", "https://lcd.mainnet.secretsaturn.net"),
            secret_chain_id=os.getenv("SECRET_NETWORK_CHAIN_ID", "secret-4"),
            secret_mnemonic=os.getenv("SECRET_WALLET_MNEMONIC", ""),
            sxmr_contract_address=os.getenv("SXMR_CONTRACT_ADDRESS", ""),
            sxmr_contract_hash=os.getenv("SXMR_CONTRACT_HASH", ""),
            min_confirmations=int(os.getenv("MIN_CONFIRMATIONS", "10")),
            poll_interval=int(os.getenv("POLL_INTERVAL", "60")),
            database_path=os.getenv("DATABASE_PATH", "bridge.db"),
        )

    def validate(self) -> None:
        """Validate configuration."""
        # Check if we have either seed or address+keys
        if not self.monero_seed:
            if not self.monero_wallet_address:
                raise ValueError("Either MONERO_SEED or MONERO_WALLET_ADDRESS is required")
            if not self.monero_view_key:
                raise ValueError("MONERO_VIEW_KEY is required when not using seed")

        if not self.secret_mnemonic:
            raise ValueError("SECRET_WALLET_MNEMONIC is required")
        if not self.sxmr_contract_address:
            raise ValueError("SXMR_CONTRACT_ADDRESS is required")


class SimpleBridge:
    """Simple Monero to Secret Network bridge.

    Monitors Monero deposits and mints corresponding sXMR on Secret Network.
    """

    def __init__(self, config: BridgeConfig):
        """Initialize the bridge.

        Args:
            config: Bridge configuration
        """
        self.config = config
        self.running = False

        # Initialize database
        self.db = BridgeDatabase(config.database_path)

        # Initialize Monero wallet manager
        self.wallet_manager = MoneroWalletManager(
            seed=config.monero_seed,
            wallet_address=config.monero_wallet_address,
            view_key=config.monero_view_key,
            spend_key=config.monero_spend_key,
            rpc_url=config.monero_rpc_url,
            wallet_rpc_url=config.monero_wallet_rpc_url,
            wallet_rpc_user=config.monero_wallet_rpc_user,
            wallet_rpc_password=config.monero_wallet_rpc_password,
            network=config.monero_network,
            db=self.db
        )

        # Initialize Secret Network client
        self.secret_client = SecretNetworkClient(
            mnemonic=config.secret_mnemonic,
            contract_address=config.sxmr_contract_address,
            contract_hash=config.sxmr_contract_hash,
            rpc_url=config.secret_rpc_url,
            chain_id=config.secret_chain_id
        )

        # Initialize deposit monitor (will be started later)
        self.deposit_monitor = MoneroDepositMonitor(
            wallet_manager=self.wallet_manager,
            min_confirmations=config.min_confirmations,
            poll_interval=config.poll_interval,
            on_deposit=self._on_deposit
        )

        # Last checked block height for withdrawals
        self.last_withdrawal_check_height = 0

        logger.info("Initialized Simple Monero Bridge")

    async def start(self) -> None:
        """Start the bridge."""
        logger.info("Starting Simple Monero Bridge...")

        self.config.validate()

        # Start database
        await self.db.start()

        # Start Monero wallet manager
        await self.wallet_manager.start()

        # Start Secret Network client
        await self.secret_client.start()

        # Get initial block height for withdrawal monitoring
        self.last_withdrawal_check_height = await self.secret_client.get_latest_block_height()

        # Start deposit monitor
        await self.deposit_monitor.start()

        self.running = True
        logger.info("Bridge started successfully")

    async def stop(self) -> None:
        """Stop the bridge."""
        logger.info("Stopping bridge...")
        self.running = False

        # Stop deposit monitor
        await self.deposit_monitor.stop()

        # Stop clients
        await self.secret_client.stop()
        await self.wallet_manager.stop()

        # Stop database
        await self.db.stop()

        logger.info("Bridge stopped")

    async def generate_deposit_address(self, secret_address: str) -> str:
        """Generate a Monero subaddress for a user's Secret Network address.

        Args:
            secret_address: Secret Network address to map to

        Returns:
            Monero subaddress for deposits
        """
        subaddress = await self.wallet_manager.generate_subaddress(secret_address)
        logger.info(f"Generated deposit address {subaddress[:16]}... for {secret_address[:16]}...")
        return subaddress

    async def _on_deposit(self, deposit: MoneroDeposit) -> None:
        """Internal callback for deposit monitor.

        Args:
            deposit: Confirmed deposit information
        """
        # Check if already processed in database
        if await self.db.is_deposit_processed(deposit.tx_hash):
            logger.debug(f"Deposit {deposit.tx_hash[:16]}... already processed")
            return

        # Get user identifier (Secret Network address)
        user_id = await self.wallet_manager.get_user_for_subaddress(
            deposit.subaddress_index[0],
            deposit.subaddress_index[1]
        )

        if not user_id:
            logger.error(
                f"No user mapping for deposit {deposit.tx_hash[:16]}... "
                f"to subaddress {deposit.subaddress_index}"
            )
            return

        logger.info(
            f"Processing deposit {deposit.tx_hash[:16]}...: "
            f"{deposit.amount} piconeros to {user_id[:16]}..."
        )

        try:
            # Mint sXMR on Secret Network
            secret_tx_hash = await self.secret_client.mint(
                recipient=user_id,
                amount=deposit.amount,
                memo=f"Deposit from XMR tx {deposit.tx_hash}"
            )

            # Mark as processed in database
            await self.db.mark_deposit_processed(
                tx_hash=deposit.tx_hash,
                amount=deposit.amount,
                subaddress=deposit.subaddress,
                secret_address=user_id,
                secret_tx_hash=secret_tx_hash
            )

            logger.info(
                f"Successfully minted {deposit.amount} sXMR for deposit {deposit.tx_hash[:16]}... "
                f"in Secret tx {secret_tx_hash[:16]}..."
            )
        except Exception as e:
            logger.error(f"Failed to mint sXMR for deposit {deposit.tx_hash[:16]}...: {e}", exc_info=True)

    async def monitor_withdrawals(self) -> None:
        """Monitor Secret Network for sXMR burn events."""
        logger.info("Starting withdrawal monitoring...")

        while self.running:
            try:
                # Get burn events since last check
                burn_events = await self.secret_client.monitor_burn_events(
                    start_height=self.last_withdrawal_check_height,
                    poll_interval=self.config.poll_interval
                )

                # Process each burn event
                for burn_event in burn_events:
                    await self._handle_withdrawal(burn_event)

                # Update last checked height
                current_height = await self.secret_client.get_latest_block_height()
                if current_height > 0:
                    self.last_withdrawal_check_height = current_height

                await asyncio.sleep(self.config.poll_interval)
            except Exception as e:
                logger.error(f"Error monitoring withdrawals: {e}", exc_info=True)
                await asyncio.sleep(self.config.poll_interval)

    async def _handle_withdrawal(self, burn_event: BurnEvent) -> None:
        """Handle an sXMR burn withdrawal request.

        Args:
            burn_event: Burn event information
        """
        # Check if already processed in database
        if await self.db.is_withdrawal_processed(burn_event.tx_hash):
            logger.debug(f"Withdrawal {burn_event.tx_hash[:16]}... already processed")
            return

        logger.info(
            f"Processing withdrawal {burn_event.tx_hash[:16]}...: "
            f"{burn_event.amount} piconeros to {burn_event.monero_address[:16]}..."
        )

        try:
            # Send XMR from bridge wallet to destination address
            monero_tx_hash = await self.wallet_manager.send_transaction(
                destination=burn_event.monero_address,
                amount=burn_event.amount,
                payment_id=None
            )

            # Mark as processed in database
            await self.db.mark_withdrawal_processed(
                secret_tx_hash=burn_event.tx_hash,
                amount=burn_event.amount,
                monero_address=burn_event.monero_address,
                monero_tx_hash=monero_tx_hash
            )

            logger.info(
                f"Successfully sent {burn_event.amount} XMR for withdrawal {burn_event.tx_hash[:16]}... "
                f"in tx {monero_tx_hash[:16]}..."
            )
        except NotImplementedError:
            logger.warning(
                f"Withdrawal sending not yet implemented for {burn_event.tx_hash[:16]}... "
                f"(requires wallet RPC with spend key)"
            )
            # Don't mark as processed so we can retry when implemented
        except Exception as e:
            logger.error(
                f"Failed to send XMR for withdrawal {burn_event.tx_hash[:16]}...: {e}",
                exc_info=True
            )

    async def run(self) -> None:
        """Run the bridge (blocking)."""
        await self.start()

        try:
            # Deposit monitoring is handled by the MoneroDepositMonitor
            # We just need to run withdrawal monitoring
            await self.monitor_withdrawals()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()
