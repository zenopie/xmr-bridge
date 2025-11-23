"""Core types, traits, and errors for XMR Bridge."""

from core.errors import BridgeError, MoneroError, FrostError, NetworkError, SecretNetworkError
from core.types import (
    ParticipantAddress,
    SignatureShare,
    Deposit,
    Withdrawal,
    ParticipantInfo,
    BridgeState,
    BridgeStatus,
)

__all__ = [
    "BridgeError",
    "MoneroError",
    "FrostError",
    "NetworkError",
    "SecretNetworkError",
    "ParticipantAddress",
    "SignatureShare",
    "Deposit",
    "Withdrawal",
    "ParticipantInfo",
    "BridgeState",
    "BridgeStatus",
]
