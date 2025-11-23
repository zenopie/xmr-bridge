"""Monerod RPC client for blockchain operations."""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

import aiohttp

from core.errors import MoneroError, RPCError

logger = logging.getLogger(__name__)


class MoneroNetwork(Enum):
    """Monero network types."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    STAGENET = "stagenet"


@dataclass
class MoneroNodeConfig:
    """Configuration for Monerod RPC connection."""
    rpc_url: str
    rpc_user: Optional[str] = None
    rpc_password: Optional[str] = None
    network: MoneroNetwork = MoneroNetwork.MAINNET


class MoneroNode:
    """Manages connection to a Monerod node via RPC.

    This connects to an external monerod instance that can also be used for mining.
    """

    def __init__(self, config: MoneroNodeConfig):
        """Create a new Monerod RPC client.

        Args:
            config: Configuration for the monerod connection
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._is_running = False
        logger.info(f"Initializing Monerod RPC client at {config.rpc_url}")

    @classmethod
    def new_simple(cls, rpc_url: str) -> "MoneroNode":
        """Create with simple configuration.

        Args:
            rpc_url: URL of the monerod RPC endpoint

        Returns:
            MoneroNode instance
        """
        config = MoneroNodeConfig(
            rpc_url=rpc_url,
            network=MoneroNetwork.MAINNET
        )
        return cls(config)

    async def start(self) -> None:
        """Connect to the Monerod node."""
        if self._is_running:
            logger.info("Already connected to monerod")
            return

        logger.info(f"Connecting to monerod at {self.config.rpc_url}")

        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=30)
        auth = None
        if self.config.rpc_user and self.config.rpc_password:
            auth = aiohttp.BasicAuth(
                self.config.rpc_user,
                self.config.rpc_password
            )

        self._session = aiohttp.ClientSession(timeout=timeout, auth=auth)

        # Test connection by getting blockchain height
        try:
            await self.get_block_height()
        except Exception as e:
            await self._session.close()
            self._session = None
            raise MoneroError(f"Failed to connect to monerod - is it running? {e}")

        self._is_running = True
        logger.info("Connected to monerod successfully")

    async def stop(self) -> None:
        """Disconnect from the Monerod node."""
        if not self._is_running:
            logger.info("Not connected to monerod")
            return

        logger.info("Disconnecting from monerod...")

        if self._session:
            await self._session.close()
            self._session = None

        self._is_running = False
        logger.info("Disconnected from monerod")

    def is_running(self) -> bool:
        """Check if the node connection is active."""
        return self._is_running

    async def _rpc_call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make an RPC call to monerod.

        Args:
            method: RPC method name
            params: Optional parameters for the RPC call

        Returns:
            The result from the RPC response

        Raises:
            MoneroError: If the session is not initialized
            RPCError: If the RPC call returns an error
        """
        if not self._session:
            raise MoneroError("Session not initialized - call start() first")

        request_body = {
            "jsonrpc": "2.0",
            "id": "0",
            "method": method,
        }

        if params is not None:
            request_body["params"] = params

        try:
            async with self._session.post(
                self.config.rpc_url,
                json=request_body
            ) as response:
                response_data = await response.json()
        except Exception as e:
            raise MoneroError(f"Failed to send RPC request: {e}")

        if "error" in response_data and response_data["error"]:
            error = response_data["error"]
            raise RPCError(
                str(error),
                method=method,
                details=str(error)
            )

        if "result" not in response_data:
            raise RPCError(
                "Missing result in RPC response",
                method=method
            )

        return response_data["result"]

    async def get_block_height(self) -> int:
        """Get current blockchain height.

        Returns:
            Current blockchain height
        """
        result = await self._rpc_call("get_block_count", {})
        return result.get("height", 0)

    async def get_block(self, height: int) -> Dict[str, Any]:
        """Get block by height.

        Args:
            height: Block height to retrieve

        Returns:
            Block data as dictionary
        """
        result = await self._rpc_call("get_block", {"height": height})
        return result

    async def is_synchronized(self) -> bool:
        """Check if blockchain is synced.

        Returns:
            True if synced, False otherwise
        """
        try:
            result = await self._rpc_call("sync_info", {})
            sync_info = result.get("sync_info", {})

            height = sync_info.get("height", 0)
            target_height = sync_info.get("target_height", 0)

            # Consider synced if within 2 blocks of target
            diff = target_height - height
            return diff <= 2
        except Exception as e:
            logger.warning(f"Failed to get sync info: {e}")
            return False

    async def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction by hash.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction data
        """
        result = await self._rpc_call(
            "get_transactions",
            {"txs_hashes": [tx_hash], "decode_as_json": True}
        )
        return result

    async def get_transaction_pool(self) -> Dict[str, Any]:
        """Get current transaction pool.

        Returns:
            Transaction pool data
        """
        result = await self._rpc_call("get_transaction_pool", {})
        return result

    async def __aenter__(self) -> "MoneroNode":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()
