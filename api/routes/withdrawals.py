"""Withdrawal-related API endpoints."""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from api.models import WithdrawalStatus, TransactionHistory
from api.dependencies import get_bridge
from api.routes.deposits import get_deposits
from bridge import SimpleBridge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["withdrawals"])


@router.get("/withdrawals/{secret_address}", response_model=List[WithdrawalStatus])
async def get_withdrawals(
    secret_address: str,
    bridge: SimpleBridge = Depends(get_bridge)
):
    """Get withdrawal history for a Secret Network address.

    Frontend calls this to show user's withdrawal history.
    """
    if not bridge.db:
        raise HTTPException(status_code=503, detail="Database not initialized")

    try:
        # TODO: Query withdrawals from database processed_withdrawals table
        withdrawals = []
        return withdrawals
    except Exception as e:
        logger.error(f"Failed to get withdrawals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{secret_address}", response_model=TransactionHistory)
async def get_transaction_history(
    secret_address: str,
    bridge: SimpleBridge = Depends(get_bridge)
):
    """Get complete transaction history for a Secret Network address.

    Frontend calls this to show user's dashboard.
    """
    try:
        deposits = await get_deposits(secret_address, bridge)
        withdrawals = await get_withdrawals(secret_address, bridge)

        total_deposited = sum(d.amount for d in deposits if d.status == "completed")
        total_withdrawn = sum(w.amount for w in withdrawals if w.status == "completed")

        return TransactionHistory(
            secret_address=secret_address,
            deposits=deposits,
            withdrawals=withdrawals,
            total_deposited=total_deposited,
            total_withdrawn=total_withdrawn
        )
    except Exception as e:
        logger.error(f"Failed to get transaction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
