"""Main bridge orchestrator."""

import asyncio
import logging
from typing import Optional

from config import BridgeConfig
from core.types import BridgeStatus
from monero.node import MoneroNode, MoneroNodeConfig
from monero.deposit_monitor import MoneroDepositMonitor
from monero.withdrawal import MoneroWithdrawalManager
from frost.coordinator import FrostCoordinator
from frost.participant import FrostParticipant
from network.p2p import P2PNetwork, P2PConfig
from secret.client import SecretNetworkClient, SecretNetworkConfig

logger = logging.getLogger(__name__)


class XMRBridge:
    """Main bridge orchestrator.

    Coordinates all bridge components: Monero node, FROST signatures,
    P2P networking, and Secret Network integration.
    """

    def __init__(self, config: BridgeConfig):
        """Initialize the bridge.

        Args:
            config: Bridge configuration
        """
        self.config = config
        self.status = BridgeStatus.INITIALIZING

        # Initialize Monero node
        monero_config = MoneroNodeConfig(
            rpc_url=config.monero_rpc_url,
            rpc_user=config.monero_rpc_user,
            rpc_password=config.monero_rpc_password,
            network=config.monero_network,
        )
        self.monero_node = MoneroNode(monero_config)

        # Initialize FROST
        self.frost_participant = FrostParticipant(config.participant_id)
        self.frost_coordinator: Optional[FrostCoordinator] = None
        if config.participant_id == 1:  # First participant acts as coordinator
            self.frost_coordinator = FrostCoordinator(
                threshold=config.threshold,
                total_participants=config.total_participants,
            )

        # Initialize P2P network
        p2p_config = P2PConfig(
            listen_address=config.listen_address,
            peer_addresses=config.peer_addresses,
            participant_id=config.participant_id,
        )
        self.p2p_network = P2PNetwork(p2p_config)

        # Initialize Secret Network client
        secret_config = SecretNetworkConfig(
            rpc_url=config.secret_network_rpc,
            chain_id=config.secret_network_chain_id,
            wallet_address=config.secret_wallet_address,
        )
        self.secret_client = SecretNetworkClient(secret_config)

        # Initialize monitors/managers
        self.deposit_monitor: Optional[MoneroDepositMonitor] = None
        self.withdrawal_manager = MoneroWithdrawalManager(self.monero_node)

        logger.info(f"Initialized XMR Bridge (Participant {config.participant_id})")

    async def start(self) -> None:
        """Start the bridge."""
        logger.info("Starting XMR Bridge...")

        try:
            # Start Monero node connection
            await self.monero_node.start()

            # Wait for sync
            logger.info("Waiting for blockchain sync...")
            while not await self.monero_node.is_synchronized():
                logger.info("Blockchain not synced yet, waiting...")
                await asyncio.sleep(30)
            logger.info("Blockchain synced")

            # Start P2P network
            await self.p2p_network.start()

            # Connect to Secret Network
            await self.secret_client.connect()

            # Run DKG if coordinator
            if self.frost_coordinator:
                logger.info("Running DKG as coordinator...")
                # TODO: Implement DKG coordination

            # Start deposit monitoring
            self.deposit_monitor = MoneroDepositMonitor(
                node=self.monero_node,
                min_confirmations=self.config.min_confirmations,
                callback=self._handle_deposit,
            )
            await self.deposit_monitor.start()

            self.status = BridgeStatus.RUNNING
            logger.info("XMR Bridge started successfully")

        except Exception as e:
            self.status = BridgeStatus.ERROR
            logger.error(f"Failed to start bridge: {e}")
            raise

    async def stop(self) -> None:
        """Stop the bridge."""
        logger.info("Stopping XMR Bridge...")

        # Stop deposit monitoring
        if self.deposit_monitor:
            await self.deposit_monitor.stop()

        # Disconnect from Secret Network
        await self.secret_client.disconnect()

        # Stop P2P network
        await self.p2p_network.stop()

        # Stop Monero node
        await self.monero_node.stop()

        self.status = BridgeStatus.PAUSED
        logger.info("XMR Bridge stopped")

    async def _handle_deposit(self, deposit) -> None:
        """Handle a detected deposit.

        Args:
            deposit: Deposit information
        """
        logger.info(f"Processing deposit: {deposit.tx_hash}")

        # TODO: Coordinate with other participants via P2P
        # TODO: Generate deposit proof using FROST
        # TODO: Submit to Secret Network to mint tokens

    async def run(self) -> None:
        """Run the bridge (blocking)."""
        await self.start()

        try:
            # Keep running
            while self.status == BridgeStatus.RUNNING:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()
