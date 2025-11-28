"""Pydantic models for API requests and responses."""

from typing import List, Optional
from pydantic import BaseModel


class DepositAddressRequest(BaseModel):
    """Request to generate a deposit address."""
    secret_address: str


class DepositAddressResponse(BaseModel):
    """Response with Monero deposit address."""
    secret_address: str
    monero_address: str
    created_at: str


class DepositStatus(BaseModel):
    """Deposit status information."""
    tx_hash: str
    amount: int
    confirmations: int
    required_confirmations: int
    status: str  # "pending", "confirming", "completed"
    monero_address: str
    secret_address: str
    secret_tx_hash: Optional[str] = None
    block_height: int
    processed_at: Optional[str] = None


class WithdrawalStatus(BaseModel):
    """Withdrawal status information."""
    secret_tx_hash: str
    amount: int
    monero_address: str
    monero_tx_hash: Optional[str] = None
    status: str  # "pending", "processing", "completed"
    processed_at: Optional[str] = None


class TransactionHistory(BaseModel):
    """Transaction history for a user."""
    secret_address: str
    deposits: List[DepositStatus]
    withdrawals: List[WithdrawalStatus]
    total_deposited: int
    total_withdrawn: int


class HealthResponse(BaseModel):
    """API health check response."""
    status: str
    service: str
    version: str
