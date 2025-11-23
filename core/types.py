"""Core types for XMR Bridge."""

from dataclasses import dataclass
from typing import NewType, Dict
from enum import Enum

# Type aliases
ParticipantAddress = NewType("ParticipantAddress", str)  # Secret Network address (e.g., "secret1abc...")
SignatureShare = NewType("SignatureShare", bytes)


@dataclass
class Deposit:
    """Represents a Monero deposit."""
    tx_hash: str
    amount: int  # Amount in atomic units (piconeros)
    height: int
    confirmations: int
    recipient_address: str


@dataclass
class Withdrawal:
    """Represents a Monero withdrawal request."""
    destination_address: str
    amount: int  # Amount in atomic units (piconeros)
    request_id: str
    requester: str  # Secret Network address


class BridgeStatus(Enum):
    """Bridge operational status."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class ParticipantInfo:
    """Information about a bridge participant from the contract."""
    address: str  # Secret Network address (the participant ID)
    frost_public_key: bytes
    p2p_endpoint: str
    stake: int  # Staked amount in uscrt
    joined_at: int
    is_active: bool


@dataclass
class BridgeState:
    """Bridge state from the coordination contract."""
    threshold: int
    min_stake: int
    participants: Dict[str, ParticipantInfo]  # address -> info
    monero_address: str
    total_locked: int
