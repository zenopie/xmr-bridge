"""Secret Network client for sXMR token operations using secret-sdk."""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from secret_sdk.client.lcd import LCDClient
from secret_sdk.key.mnemonic import MnemonicKey
from secret_sdk.core.tx import Tx
from secret_sdk.core.wasm import MsgExecuteContract

logger = logging.getLogger(__name__)


@dataclass
class BurnEvent:
    """Represents an sXMR burn event."""
    tx_hash: str
    amount: int  # in atomic units
    monero_address: str
    secret_address: str
    block_height: int


class SecretNetworkClient:
    """Client for interacting with Secret Network and sXMR contract."""

    def __init__(
        self,
        mnemonic: str,
        contract_address: str,
        contract_hash: str,
        rpc_url: str = "https://lcd.mainnet.secretsaturn.net",
        chain_id: str = "secret-4"
    ):
        """Initialize the Secret Network client.

        Args:
            mnemonic: Wallet mnemonic (24 words)
            contract_address: sXMR contract address
            contract_hash: sXMR contract code hash
            rpc_url: Secret Network LCD/RPC endpoint
            chain_id: Chain ID
        """
        self.mnemonic = mnemonic
        self.contract_address = contract_address
        self.contract_hash = contract_hash
        self.rpc_url = rpc_url
        self.chain_id = chain_id

        # Will be initialized on start
        self.client: Optional[LCDClient] = None
        self.wallet = None
        self.address: Optional[str] = None

        logger.info(f"Initialized Secret Network client for contract {contract_address[:16]}...")

    async def start(self) -> None:
        """Start the Secret Network client."""
        try:
            # Create LCD client
            self.client = LCDClient(
                url=self.rpc_url,
                chain_id=self.chain_id
            )

            # Create wallet from mnemonic
            key = MnemonicKey(mnemonic=self.mnemonic)
            self.wallet = self.client.wallet(key)
            self.address = self.wallet.key.acc_address

            logger.info(f"Secret Network client started with address {self.address}")

        except Exception as e:
            logger.error(f"Failed to start Secret Network client: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Secret Network client."""
        logger.info("Secret Network client stopped")

    async def mint(self, recipient: str, amount: int, memo: str = "") -> str:
        """Mint sXMR tokens to a recipient.

        Args:
            recipient: Secret Network address to mint to
            amount: Amount in atomic units
            memo: Transaction memo

        Returns:
            Transaction hash
        """
        logger.info(f"Minting {amount} sXMR to {recipient[:16]}...")

        if not self.wallet or not self.client:
            raise RuntimeError("Client not initialized - call start() first")

        # Prepare mint message
        execute_msg = {
            "mint": {
                "recipient": recipient,
                "amount": str(amount)
            }
        }

        try:
            # Create execute contract message
            msg = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.contract_address,
                msg=execute_msg,
                code_hash=self.contract_hash,
                encryption_utils=self.client.encrypt_utils
            )

            # Create and broadcast transaction
            tx = self.wallet.create_and_broadcast_tx(
                msg_list=[msg],
                gas=200_000,
                memo=memo
            )

            # Wait for transaction to be included in a block
            tx_result = await self._wait_for_tx(tx.txhash)

            if tx_result.get("code", 0) != 0:
                raise Exception(f"Mint transaction failed: {tx_result.get('raw_log', 'Unknown error')}")

            logger.info(f"Minted {amount} sXMR in tx {tx.txhash[:16]}...")
            return tx.txhash

        except Exception as e:
            logger.error(f"Failed to mint sXMR: {e}")
            raise

    async def query_balance(self, address: str) -> int:
        """Query sXMR balance for an address.

        Args:
            address: Secret Network address

        Returns:
            Balance in atomic units
        """
        if not self.client:
            raise RuntimeError("Client not initialized")

        try:
            # Create balance query
            query = {
                "balance": {
                    "address": address
                }
            }

            # Query the contract
            result = await self._query_contract(query)
            balance = result.get("balance", {}).get("amount", "0")

            return int(balance)

        except Exception as e:
            logger.error(f"Failed to query balance: {e}")
            return 0

    async def monitor_burn_events(
        self,
        start_height: int = 0,
        poll_interval: int = 60
    ) -> List[BurnEvent]:
        """Monitor for burn events in the sXMR contract.

        Args:
            start_height: Block height to start monitoring from
            poll_interval: Seconds between checks

        Returns:
            List of burn events
        """
        if not self.client:
            return []

        try:
            # Get current block height
            current_height = await self.get_latest_block_height()

            # Query transactions to the contract between start_height and current_height
            # This would involve querying the LCD API for transactions
            # and filtering for burn events

            # TODO: Implement proper event monitoring
            # For now, return empty list
            logger.debug(f"Checking for burn events from height {start_height} to {current_height}")
            return []

        except Exception as e:
            logger.error(f"Error monitoring burn events: {e}")
            return []

    async def _query_contract(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the contract.

        Args:
            query: Contract query

        Returns:
            Query result
        """
        if not self.client:
            raise RuntimeError("Client not initialized")

        try:
            # Use secret-sdk to query the contract
            result = self.client.wasm.contract_query(
                contract_address=self.contract_address,
                query=query,
                code_hash=self.contract_hash
            )
            return result

        except Exception as e:
            logger.error(f"Error querying contract: {e}")
            return {}

    async def _wait_for_tx(self, tx_hash: str, timeout: int = 60) -> Dict[str, Any]:
        """Wait for a transaction to be included in a block.

        Args:
            tx_hash: Transaction hash
            timeout: Maximum time to wait in seconds

        Returns:
            Transaction result
        """
        if not self.client:
            raise RuntimeError("Client not initialized")

        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Query transaction
                tx_info = self.client.tx.tx_info(tx_hash)
                if tx_info:
                    return tx_info
            except Exception:
                # Transaction not found yet
                pass

            # Wait before retrying
            await asyncio.sleep(2)

        raise TimeoutError(f"Transaction {tx_hash} not found within {timeout} seconds")

    async def get_latest_block_height(self) -> int:
        """Get the latest block height.

        Returns:
            Block height
        """
        if not self.client:
            return 0

        try:
            # Get latest block info
            block_info = self.client.tendermint.block_info()
            height = block_info.get("block", {}).get("header", {}).get("height", "0")
            return int(height)

        except Exception as e:
            logger.error(f"Error getting block height: {e}")
            return 0
