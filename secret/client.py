"""Secret Network client using Secret SDK for bridge contract interaction."""

import base64
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from secret_sdk.client.lcd import LCDClient
from secret_sdk.key.mnemonic import MnemonicKey
from secret_sdk.core.wasm import MsgExecuteContract
from secret_sdk.core import Coins, Coin
from secret_sdk.exceptions import LCDResponseError

from core.errors import SecretNetworkError
from core.types import BridgeState, ParticipantInfo
from wallet import Wallet

logger = logging.getLogger(__name__)


@dataclass
class SecretNetworkConfig:
    """Configuration for Secret Network connection."""
    rpc_url: str
    chain_id: str
    contract_address: str


class SecretNetworkClient:
    """Client for interacting with Secret Network using Secret SDK.

    Handles communication with Secret Network smart contracts
    for registration, minting, and burning wrapped XMR tokens.
    """

    def __init__(self, config: SecretNetworkConfig, wallet: Wallet):
        """Initialize Secret Network client.

        Args:
            config: Secret Network configuration
            wallet: Wallet instance for signing transactions
        """
        self.config = config
        self.wallet = wallet

        # Create LCD client (Light Client Daemon)
        self.client = LCDClient(
            url=config.rpc_url,
            chain_id=config.chain_id
        )

        # Create key from wallet mnemonic
        self.key = MnemonicKey(mnemonic=wallet.mnemonic)

        # Create wallet interface
        self.sdk_wallet = self.client.wallet(self.key)

        logger.info(
            f"Initialized Secret Network client for {config.chain_id} "
            f"with address: {wallet.address}"
        )

    async def register_participant(
        self,
        frost_public_key: bytes,
        p2p_endpoint: str,
        stake_amount: int
    ) -> str:
        """Register as a bridge participant with stake.

        Args:
            frost_public_key: Public key for FROST threshold signatures
            p2p_endpoint: P2P endpoint for other participants to connect
            stake_amount: Amount to stake (in uscrt)

        Returns:
            Transaction hash

        Raises:
            SecretNetworkError: If registration fails
        """
        logger.info(
            f"Registering participant {self.wallet.address} "
            f"with stake {stake_amount} uscrt"
        )

        try:
            # Prepare execute message
            execute_msg = {
                "register_participant": {
                    "frost_public_key": base64.b64encode(frost_public_key).decode(),
                    "p2p_endpoint": p2p_endpoint,
                }
            }

            # Create execute contract message with funds (stake)
            msg = MsgExecuteContract(
                sender=self.wallet.address,
                contract=self.config.contract_address,
                msg=execute_msg,
                coins=Coins([Coin("uscrt", stake_amount)])
            )

            # Create and sign transaction
            tx = self.sdk_wallet.create_and_sign_tx(
                msgs=[msg],
                memo="Register as bridge participant"
            )

            # Broadcast transaction
            result = self.client.tx.broadcast(tx)

            if result.is_tx_error():
                raise SecretNetworkError(
                    f"Transaction failed: {result.raw_log}"
                )

            logger.info(f"Registration successful: {result.txhash}")
            return result.txhash

        except LCDResponseError as e:
            raise SecretNetworkError(f"LCD error during registration: {e}")
        except Exception as e:
            raise SecretNetworkError(f"Failed to register participant: {e}")

    async def get_bridge_state(self) -> BridgeState:
        """Get current bridge state from contract.

        Returns:
            BridgeState with threshold, participants, etc.

        Raises:
            SecretNetworkError: If query fails
        """
        logger.info("Querying bridge state from contract")

        try:
            # Query contract
            query_msg = {"get_state": {}}
            result = self.client.wasm.contract_query(
                self.config.contract_address,
                query_msg
            )

            # Parse response into BridgeState
            participants_data = result.get("participants", {})
            participants = {}

            for address, info in participants_data.items():
                participants[address] = ParticipantInfo(
                    address=address,
                    frost_public_key=base64.b64decode(info["frost_public_key"]),
                    p2p_endpoint=info["p2p_endpoint"],
                    stake=int(info["stake"]),
                    joined_at=int(info["joined_at"]),
                    is_active=info["is_active"]
                )

            bridge_state = BridgeState(
                threshold=result["threshold"],
                min_stake=result["min_stake"],
                participants=participants,
                monero_address=result["monero_address"],
                total_locked=result["total_locked"]
            )

            logger.info(
                f"Bridge state: {len(participants)} participants, "
                f"threshold {bridge_state.threshold}"
            )

            return bridge_state

        except LCDResponseError as e:
            raise SecretNetworkError(f"LCD error querying bridge state: {e}")
        except Exception as e:
            raise SecretNetworkError(f"Failed to query bridge state: {e}")

    async def get_participant_info(self, address: str) -> Optional[ParticipantInfo]:
        """Get participant information from contract.

        Args:
            address: Secret Network address of the participant

        Returns:
            ParticipantInfo if registered, None otherwise

        Raises:
            SecretNetworkError: If query fails
        """
        logger.info(f"Querying participant info for {address}")

        try:
            # Query contract
            query_msg = {"get_participant": {"address": address}}
            result = self.client.wasm.contract_query(
                self.config.contract_address,
                query_msg
            )

            if not result or result.get("participant") is None:
                logger.info(f"Participant {address} not registered")
                return None

            info = result["participant"]

            participant = ParticipantInfo(
                address=address,
                frost_public_key=base64.b64decode(info["frost_public_key"]),
                p2p_endpoint=info["p2p_endpoint"],
                stake=int(info["stake"]),
                joined_at=int(info["joined_at"]),
                is_active=info["is_active"]
            )

            logger.info(f"Found participant: {address}, stake: {participant.stake}")
            return participant

        except LCDResponseError as e:
            # Participant not found might return an error
            if "not found" in str(e).lower():
                return None
            raise SecretNetworkError(f"LCD error querying participant: {e}")
        except Exception as e:
            raise SecretNetworkError(f"Failed to query participant info: {e}")

    async def mint_wrapped_xmr(
        self,
        recipient: str,
        amount: int,
        deposit_proof: bytes
    ) -> str:
        """Mint wrapped XMR tokens.

        Args:
            recipient: Secret Network address to receive tokens
            amount: Amount to mint (in atomic units)
            deposit_proof: Proof of Monero deposit (FROST signature)

        Returns:
            Transaction hash

        Raises:
            SecretNetworkError: If minting fails
        """
        logger.info(f"Minting {amount} wrapped XMR for {recipient}")

        try:
            execute_msg = {
                "mint": {
                    "recipient": recipient,
                    "amount": str(amount),
                    "deposit_proof": base64.b64encode(deposit_proof).decode(),
                }
            }

            msg = MsgExecuteContract(
                sender=self.wallet.address,
                contract=self.config.contract_address,
                msg=execute_msg
            )

            tx = self.sdk_wallet.create_and_sign_tx(
                msgs=[msg],
                memo="Mint wrapped XMR"
            )

            result = self.client.tx.broadcast(tx)

            if result.is_tx_error():
                raise SecretNetworkError(f"Transaction failed: {result.raw_log}")

            logger.info(f"Mint successful: {result.txhash}")
            return result.txhash

        except Exception as e:
            raise SecretNetworkError(f"Failed to mint wrapped XMR: {e}")

    async def burn_wrapped_xmr(
        self,
        amount: int,
        monero_address: str
    ) -> str:
        """Burn wrapped XMR tokens (for withdrawal).

        Args:
            amount: Amount to burn (in atomic units)
            monero_address: Monero address to receive withdrawal

        Returns:
            Transaction hash

        Raises:
            SecretNetworkError: If burning fails
        """
        logger.info(f"Burning {amount} wrapped XMR for withdrawal to {monero_address}")

        try:
            execute_msg = {
                "burn": {
                    "amount": str(amount),
                    "monero_address": monero_address,
                }
            }

            msg = MsgExecuteContract(
                sender=self.wallet.address,
                contract=self.config.contract_address,
                msg=execute_msg
            )

            tx = self.sdk_wallet.create_and_sign_tx(
                msgs=[msg],
                memo="Burn wrapped XMR for withdrawal"
            )

            result = self.client.tx.broadcast(tx)

            if result.is_tx_error():
                raise SecretNetworkError(f"Transaction failed: {result.raw_log}")

            logger.info(f"Burn successful: {result.txhash}")
            return result.txhash

        except Exception as e:
            raise SecretNetworkError(f"Failed to burn wrapped XMR: {e}")

    def get_address(self) -> str:
        """Get the wallet address.

        Returns:
            Secret Network address
        """
        return self.wallet.address

    def get_balance(self, denom: str = "uscrt") -> int:
        """Get wallet balance.

        Args:
            denom: Denomination to query (default: uscrt)

        Returns:
            Balance in atomic units
        """
        try:
            coins = self.client.bank.balance(self.wallet.address)
            for coin in coins:
                if coin.denom == denom:
                    return int(coin.amount)
            return 0
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0
