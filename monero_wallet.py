"""Monero wallet management for the bridge."""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import aiohttp
from monero.address import Address, SubAddress
from monero.seed import Seed

from database import BridgeDatabase

logger = logging.getLogger(__name__)


@dataclass
class MoneroDeposit:
    """Represents a Monero deposit."""
    tx_hash: str
    amount: int  # in atomic units (piconeros)
    confirmations: int
    subaddress: str
    subaddress_index: Tuple[int, int]  # (account, index)
    block_height: int


class MoneroWalletManager:
    """Manages Monero wallet operations for the bridge.

    Handles subaddress generation, deposit monitoring, and transaction creation.
    """

    def __init__(
        self,
        seed: str = "",
        wallet_address: str = "",
        view_key: str = "",
        spend_key: str = "",
        rpc_url: str = "http://node.moneroworld.com:18089/json_rpc",
        wallet_rpc_url: str = "",
        wallet_rpc_user: str = "",
        wallet_rpc_password: str = "",
        network: str = "mainnet",
        db: Optional[BridgeDatabase] = None
    ):
        """Initialize the Monero wallet manager.

        Args:
            seed: Monero 25-word seed (recommended - derives all keys)
            wallet_address: Primary wallet address (if not using seed)
            view_key: Private view key (if not using seed)
            spend_key: Private spend key (optional, for withdrawals)
            rpc_url: Monero node RPC endpoint
            wallet_rpc_url: Monero wallet RPC endpoint (for withdrawals)
            wallet_rpc_user: Wallet RPC username
            wallet_rpc_password: Wallet RPC password
            network: Network type (mainnet, testnet, stagenet)
            db: Bridge database instance
        """
        self.rpc_url = rpc_url
        self.wallet_rpc_url = wallet_rpc_url
        self.wallet_rpc_user = wallet_rpc_user
        self.wallet_rpc_password = wallet_rpc_password
        self.network = network
        self.db = db

        # Derive from seed if provided
        if seed:
            from monero.seed import Seed
            monero_seed = Seed(seed)
            self.wallet_address = str(monero_seed.public_address())
            self.view_key = str(monero_seed.secret_view_key())
            self.spend_key = str(monero_seed.secret_spend_key())
            logger.info(f"Derived wallet from seed: {self.wallet_address[:8]}...")
        else:
            self.wallet_address = wallet_address
            self.view_key = view_key
            self.spend_key = spend_key
            logger.info(f"Using provided wallet address: {wallet_address[:8]}...")

        # Parse the address for subaddress derivation
        self.address = Address(self.wallet_address)

        # Session for RPC calls
        self.session: Optional[aiohttp.ClientSession] = None
        self.wallet_session: Optional[aiohttp.ClientSession] = None

        logger.info(f"Initialized Monero wallet manager for {self.wallet_address[:8]}...")

    async def start(self) -> None:
        """Start the wallet manager."""
        self.session = aiohttp.ClientSession()

        # Initialize wallet RPC session if configured
        if self.wallet_rpc_url:
            auth = None
            if self.wallet_rpc_user and self.wallet_rpc_password:
                auth = aiohttp.BasicAuth(self.wallet_rpc_user, self.wallet_rpc_password)
            self.wallet_session = aiohttp.ClientSession(auth=auth)
            logger.info("Monero wallet RPC session initialized")

        logger.info("Monero wallet manager started")

    async def stop(self) -> None:
        """Stop the wallet manager."""
        if self.session:
            await self.session.close()
        if self.wallet_session:
            await self.wallet_session.close()
        logger.info("Monero wallet manager stopped")

    async def generate_subaddress(self, user_identifier: str) -> str:
        """Generate a new subaddress for a user.

        Args:
            user_identifier: Unique identifier for the user (e.g., Secret Network address)

        Returns:
            Monero subaddress string
        """
        # Check if user already has a subaddress in database
        if self.db:
            existing = await self.db.get_subaddress_for_secret_address(user_identifier)
            if existing:
                account, index, subaddress = existing
                logger.info(f"User {user_identifier[:16]}... already has subaddress {index}")
                return subaddress

        # Get next available subaddress index
        account = 0  # Use account 0 for all subaddresses
        if self.db:
            index = await self.db.get_next_subaddress_index(account)
        else:
            index = 1

        # Generate actual Monero subaddress
        subaddress = self._derive_subaddress(account, index)

        # Store in database
        if self.db:
            await self.db.save_subaddress_mapping(
                account=account,
                index=index,
                subaddress=str(subaddress),
                secret_address=user_identifier
            )

        logger.info(f"Generated subaddress {index} ({str(subaddress)[:16]}...) for user {user_identifier[:16]}...")
        return str(subaddress)

    def _derive_subaddress(self, account: int, index: int) -> SubAddress:
        """Derive a Monero subaddress.

        Args:
            account: Account number
            index: Subaddress index

        Returns:
            SubAddress object
        """
        # Create subaddress from the primary address
        # The monero library handles the cryptographic derivation
        subaddress = self.address.with_subaddress(major=account, minor=index)
        return subaddress

    async def _rpc_call(self, method: str, params: dict = None) -> dict:
        """Make an RPC call to the Monero node.

        Args:
            method: RPC method name
            params: RPC parameters

        Returns:
            RPC response result
        """
        if not self.session:
            raise RuntimeError("Wallet manager not started")

        payload = {
            "jsonrpc": "2.0",
            "id": "0",
            "method": method,
            "params": params or {}
        }

        async with self.session.post(self.rpc_url, json=payload) as response:
            data = await response.json()
            if "error" in data:
                raise Exception(f"RPC error: {data['error']}")
            return data.get("result", {})

    async def get_transfers(self, min_height: int = 0) -> List[MoneroDeposit]:
        """Get incoming transfers to tracked subaddresses.

        Args:
            min_height: Minimum block height to check from

        Returns:
            List of deposits
        """
        try:
            # Get all incoming transfers
            # Note: This requires monero-wallet-rpc, not monerod
            # For view-only wallet, we can use get_transfers with filter_by_height
            result = await self._rpc_call("get_transfers", {
                "in": True,
                "out": False,
                "pending": False,
                "failed": False,
                "pool": False,
                "filter_by_height": True,
                "min_height": min_height
            })

            transfers = result.get("in", [])
            deposits = []

            for transfer in transfers:
                # Extract subaddress information
                subaddress_index = transfer.get("subaddr_index", {})
                major = subaddress_index.get("major", 0)
                minor = subaddress_index.get("minor", 0)

                # Skip primary address (0/0)
                if major == 0 and minor == 0:
                    continue

                deposit = MoneroDeposit(
                    tx_hash=transfer["txid"],
                    amount=transfer["amount"],
                    confirmations=transfer.get("confirmations", 0),
                    subaddress=transfer.get("address", ""),
                    subaddress_index=(major, minor),
                    block_height=transfer.get("height", 0)
                )
                deposits.append(deposit)

            logger.debug(f"Found {len(deposits)} transfers from height {min_height}")
            return deposits

        except Exception as e:
            logger.error(f"Failed to get transfers: {e}")
            return []

    async def get_block_height(self) -> int:
        """Get current blockchain height.

        Returns:
            Current block height
        """
        try:
            result = await self._rpc_call("get_block_count")
            return result.get("count", 0)
        except Exception as e:
            logger.error(f"Failed to get block height: {e}")
            return 0

    async def send_transaction(
        self,
        destination: str,
        amount: int,
        payment_id: Optional[str] = None
    ) -> str:
        """Send a Monero transaction.

        Args:
            destination: Destination Monero address
            amount: Amount in atomic units (piconeros)
            payment_id: Optional payment ID

        Returns:
            Transaction hash
        """
        if not self.wallet_rpc_url or not self.wallet_session:
            logger.error("Wallet RPC not configured - cannot send transactions")
            raise NotImplementedError("Transaction sending requires wallet RPC configuration")

        logger.info(f"Sending {amount} piconeros to {destination[:8]}...")

        try:
            # Prepare transfer request
            params = {
                "destinations": [{
                    "address": destination,
                    "amount": amount
                }],
                "account_index": 0,
                "priority": 1,  # Normal priority
                "ring_size": 16,  # Current Monero ring size
                "get_tx_key": True
            }

            # Call wallet RPC transfer method
            result = await self._wallet_rpc_call("transfer", params)

            tx_hash = result.get("tx_hash")
            if not tx_hash:
                raise Exception("No transaction hash returned")

            logger.info(f"Successfully sent {amount} piconeros in tx {tx_hash[:16]}...")
            return tx_hash

        except Exception as e:
            logger.error(f"Failed to send transaction: {e}")
            raise

    async def _wallet_rpc_call(self, method: str, params: dict = None) -> dict:
        """Make an RPC call to the Monero wallet RPC.

        Args:
            method: RPC method name
            params: RPC parameters

        Returns:
            RPC response result
        """
        if not self.wallet_session:
            raise RuntimeError("Wallet RPC session not initialized")

        payload = {
            "jsonrpc": "2.0",
            "id": "0",
            "method": method,
            "params": params or {}
        }

        async with self.wallet_session.post(self.wallet_rpc_url, json=payload) as response:
            data = await response.json()
            if "error" in data:
                raise Exception(f"Wallet RPC error: {data['error']}")
            return data.get("result", {})

    async def get_user_for_subaddress(self, account: int, index: int) -> Optional[str]:
        """Get the user identifier for a subaddress.

        Args:
            account: Subaddress account
            index: Subaddress index

        Returns:
            User identifier or None
        """
        if self.db:
            return await self.db.get_secret_address_for_subaddress(account, index)
        return None
