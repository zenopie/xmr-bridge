"""Configuration management for XMR Bridge."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import toml

from core.errors import ConfigurationError
from monero.node import MoneroNetwork

logger = logging.getLogger(__name__)


@dataclass
class BridgeConfig:
    """Main bridge configuration."""

    # Operator identity (mnemonic derives the Secret Network address which is the participant ID)
    operator_mnemonic: str
    operator_keyfile: Optional[str]  # Alternative to mnemonic - encrypted key export

    # Contract addresses
    bridge_contract_address: str

    # Monero settings
    monero_rpc_url: str
    monero_rpc_user: Optional[str]
    monero_rpc_password: Optional[str]
    monero_network: MoneroNetwork

    # Secret Network settings
    secret_network_rpc: str
    secret_network_chain_id: str

    # Bridge settings
    min_confirmations: int

    # P2P network settings
    listen_address: str
    public_endpoint: str  # Public P2P endpoint for other nodes to connect

    @classmethod
    def from_file(cls, config_path: Path) -> "BridgeConfig":
        """Load configuration from TOML file.

        Args:
            config_path: Path to configuration file

        Returns:
            BridgeConfig instance

        Raises:
            ConfigurationError: If config is invalid
        """
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        logger.info(f"Loading configuration from {config_path}")

        try:
            with open(config_path, "r") as f:
                config_data = toml.load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to parse configuration file: {e}")

        try:
            # Parse Monero network
            network_str = config_data.get("monero_network", "mainnet")
            monero_network = MoneroNetwork(network_str)

            return cls(
                # Operator identity
                operator_mnemonic=config_data.get("operator_mnemonic", ""),
                operator_keyfile=config_data.get("operator_keyfile"),
                # Contract addresses
                bridge_contract_address=config_data["bridge_contract_address"],
                # Monero settings
                monero_rpc_url=config_data["monero_rpc_url"],
                monero_rpc_user=config_data.get("monero_rpc_user"),
                monero_rpc_password=config_data.get("monero_rpc_password"),
                monero_network=monero_network,
                # Secret Network settings
                secret_network_rpc=config_data["secret_network_rpc"],
                secret_network_chain_id=config_data["secret_network_chain_id"],
                # Bridge settings
                min_confirmations=config_data.get("min_confirmations", 10),
                # P2P network settings
                listen_address=config_data["listen_address"],
                public_endpoint=config_data["public_endpoint"],
            )
        except KeyError as e:
            raise ConfigurationError(f"Missing required configuration key: {e}")
        except Exception as e:
            raise ConfigurationError(f"Invalid configuration: {e}")

    def validate(self) -> None:
        """Validate configuration.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Must have either mnemonic or keyfile
        if not self.operator_mnemonic and not self.operator_keyfile:
            raise ConfigurationError(
                "Must provide either operator_mnemonic or operator_keyfile"
            )

        if self.min_confirmations < 1:
            raise ConfigurationError("min_confirmations must be at least 1")

        if not self.bridge_contract_address:
            raise ConfigurationError("bridge_contract_address is required")

        logger.info("Configuration validated successfully")
