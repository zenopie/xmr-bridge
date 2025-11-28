"""Secret Network client for sXMR token operations."""

import asyncio
import logging
import base64
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import aiohttp

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
        self.wallet = None
        self.address: Optional[str] = None
        self.private_key: Optional[bytes] = None
        self.public_key: Optional[bytes] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.account_number: int = 0
        self.sequence: int = 0

        logger.info(f"Initialized Secret Network client for contract {contract_address[:16]}...")

    async def start(self) -> None:
        """Start the Secret Network client."""
        try:
            # Initialize HTTP session
            self.session = aiohttp.ClientSession()

            # Derive address and keys from mnemonic
            from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
            from hashlib import sha256
            import bech32

            # Generate seed from mnemonic
            seed_bytes = Bip39SeedGenerator(self.mnemonic).Generate()

            # Derive Secret Network key (using Cosmos/Atom coin type 118)
            bip44_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.COSMOS)
            bip44_acc_ctx = bip44_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)

            # Get keys
            self.private_key = bip44_acc_ctx.PrivateKey().Raw().ToBytes()
            self.public_key = bip44_acc_ctx.PublicKey().RawCompressed().ToBytes()

            # Hash public key and encode to bech32
            s = sha256(self.public_key).digest()
            from hashlib import new as new_hash
            h = new_hash('ripemd160', s).digest()

            # Convert to bech32 with 'secret' prefix
            words = bech32.convertbits(h, 8, 5)
            self.address = bech32.bech32_encode('secret', words)

            # Fetch account number and sequence
            await self._update_account_info()

            logger.info(f"Secret Network client started with address {self.address}")

        except Exception as e:
            logger.error(f"Failed to start Secret Network client: {e}")
            # Fallback to placeholder
            self.address = "secret1_placeholder"
            self.session = aiohttp.ClientSession()

    async def _update_account_info(self) -> None:
        """Update account number and sequence from chain."""
        if not self.session or not self.address:
            return

        try:
            url = f"{self.rpc_url}/cosmos/auth/v1beta1/accounts/{self.address}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    account = data.get("account", {})
                    self.account_number = int(account.get("account_number", 0))
                    self.sequence = int(account.get("sequence", 0))
                    logger.debug(f"Account info: number={self.account_number}, sequence={self.sequence}")
        except Exception as e:
            logger.warning(f"Could not fetch account info: {e}")

    async def stop(self) -> None:
        """Stop the Secret Network client."""
        if self.session:
            await self.session.close()
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

        # Prepare mint message
        msg = {
            "mint": {
                "recipient": recipient,
                "amount": str(amount)
            }
        }

        try:
            # Execute the contract transaction
            tx_hash = await self._execute_contract(msg, memo=memo)
            logger.info(f"Minted {amount} sXMR in tx {tx_hash[:16]}...")
            return tx_hash
        except NotImplementedError:
            # For testing, return placeholder
            tx_hash = f"secret_mint_tx_{recipient[:8]}_{amount}"
            logger.warning(f"Mint not fully implemented, returning placeholder: {tx_hash}")
            return tx_hash

    async def query_balance(self, address: str) -> int:
        """Query sXMR balance for an address.

        Args:
            address: Secret Network address

        Returns:
            Balance in atomic units
        """
        query = {
            "balance": {
                "address": address
            }
        }

        # TODO: Query the contract
        # result = await self._query_contract(query)
        # return int(result.get("balance", {}).get("amount", "0"))

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
        # TODO: Implement event monitoring
        # This involves:
        # 1. Querying blockchain for transactions to the contract
        # 2. Filtering for burn transactions
        # 3. Parsing the burn parameters (amount, monero_address)
        # 4. Creating BurnEvent objects

        logger.debug(f"Checking for burn events from height {start_height}")
        return []

    async def _execute_contract(
        self,
        msg: Dict[str, Any],
        funds: List[Dict[str, str]] = None,
        memo: str = ""
    ) -> str:
        """Execute a contract message.

        Args:
            msg: Contract message
            funds: Funds to send with transaction
            memo: Transaction memo

        Returns:
            Transaction hash
        """
        if not self.private_key or not self.address:
            raise RuntimeError("Wallet not initialized")

        try:
            # Update account info to get latest sequence
            await self._update_account_info()

            # Build and sign transaction
            tx_bytes = await self._build_and_sign_tx(msg, funds or [], memo)

            # Broadcast transaction
            tx_hash = await self._broadcast_tx(tx_bytes)

            # Increment sequence for next transaction
            self.sequence += 1

            return tx_hash

        except Exception as e:
            logger.error(f"Contract execution failed: {e}")
            raise

    async def _build_and_sign_tx(
        self,
        msg: Dict[str, Any],
        funds: List[Dict[str, str]],
        memo: str
    ) -> bytes:
        """Build and sign a transaction.

        Args:
            msg: Contract message
            funds: Funds to send
            memo: Transaction memo

        Returns:
            Signed transaction bytes
        """
        from ecdsa import SigningKey, SECP256k1
        from ecdsa.util import sigencode_string_canonize
        from hashlib import sha256

        # Create signing key from private key
        signing_key = SigningKey.from_string(self.private_key, curve=SECP256k1)

        # Build execute contract message
        execute_msg = {
            "@type": "/secret.compute.v1beta1.MsgExecuteContract",
            "sender": self.address,
            "contract": self.contract_address,
            "msg": base64.b64encode(json.dumps(msg).encode()).decode(),
            "sent_funds": funds
        }

        # Build transaction body
        tx_body = {
            "messages": [execute_msg],
            "memo": memo,
            "timeout_height": "0",
            "extension_options": [],
            "non_critical_extension_options": []
        }

        # Build auth info (fee and signer info)
        auth_info = {
            "signer_infos": [{
                "public_key": {
                    "@type": "/cosmos.crypto.secp256k1.PubKey",
                    "key": base64.b64encode(self.public_key).decode()
                },
                "mode_info": {
                    "single": {"mode": "SIGN_MODE_DIRECT"}
                },
                "sequence": str(self.sequence)
            }],
            "fee": {
                "amount": [{"denom": "uscrt", "amount": "200000"}],
                "gas_limit": "200000",
                "payer": "",
                "granter": ""
            }
        }

        # Build sign doc
        sign_doc = {
            "body_bytes": json.dumps(tx_body, separators=(',', ':')).encode(),
            "auth_info_bytes": json.dumps(auth_info, separators=(',', ':')).encode(),
            "chain_id": self.chain_id,
            "account_number": str(self.account_number)
        }

        # Create signature
        sign_bytes = json.dumps(sign_doc, separators=(',', ':')).encode()
        signature_hash = sha256(sign_bytes).digest()
        signature = signing_key.sign_digest(signature_hash, sigencode=sigencode_string_canonize)

        # Build final transaction
        tx = {
            "body": tx_body,
            "auth_info": auth_info,
            "signatures": [base64.b64encode(signature).decode()]
        }

        return json.dumps(tx).encode()

    async def _broadcast_tx(self, tx_bytes: bytes) -> str:
        """Broadcast a signed transaction.

        Args:
            tx_bytes: Signed transaction bytes

        Returns:
            Transaction hash
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        # Encode transaction for broadcast
        tx_b64 = base64.b64encode(tx_bytes).decode()

        payload = {
            "tx_bytes": tx_b64,
            "mode": "BROADCAST_MODE_SYNC"
        }

        url = f"{self.rpc_url}/cosmos/tx/v1beta1/txs"
        async with self.session.post(url, json=payload) as response:
            data = await response.json()

            if response.status != 200:
                raise Exception(f"Broadcast failed: {data}")

            tx_response = data.get("tx_response", {})
            if tx_response.get("code", 0) != 0:
                raise Exception(f"Transaction failed: {tx_response.get('raw_log', 'Unknown error')}")

            tx_hash = tx_response.get("txhash")
            if not tx_hash:
                raise Exception("No transaction hash returned")

            return tx_hash

    async def _query_contract(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the contract.

        Args:
            query: Contract query

        Returns:
            Query result
        """
        if not self.session:
            return {}

        try:
            # Encode query as base64
            query_bytes = json.dumps(query).encode()
            query_b64 = base64.b64encode(query_bytes).decode()

            # Query via LCD API
            url = f"{self.rpc_url}/wasm/contract/{self.contract_address}/smart/{query_b64}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    logger.error(f"Contract query failed: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error querying contract: {e}")
            return {}

    async def get_latest_block_height(self) -> int:
        """Get the latest block height.

        Returns:
            Block height
        """
        if not self.session:
            return 0

        try:
            # Query latest block via LCD API
            url = f"{self.rpc_url}/cosmos/base/tendermint/v1beta1/blocks/latest"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    height = data.get("block", {}).get("header", {}).get("height", "0")
                    return int(height)
                else:
                    logger.error(f"Failed to get block height: {response.status}")
                    return 0
        except Exception as e:
            logger.error(f"Error getting block height: {e}")
            return 0
