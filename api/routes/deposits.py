"""Deposit-related API endpoints."""

import logging
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from api.models import (
    DepositAddressRequest,
    DepositAddressResponse,
    DepositStatus
)
from api.dependencies import get_bridge
from bridge import SimpleBridge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["deposits"])


@router.post("/deposit-address", response_model=DepositAddressResponse)
async def generate_deposit_address(
    request: DepositAddressRequest,
    bridge: SimpleBridge = Depends(get_bridge)
):
    """Generate a Monero deposit address for a Secret Network address.

    Frontend calls this when user wants to deposit XMR.
    """
    try:
        monero_address = await bridge.generate_deposit_address(request.secret_address)

        return DepositAddressResponse(
            secret_address=request.secret_address,
            monero_address=monero_address,
            created_at=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to generate deposit address: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deposits/{secret_address}", response_model=List[DepositStatus])
async def get_deposits(
    secret_address: str,
    bridge: SimpleBridge = Depends(get_bridge)
):
    """Get all deposits for a Secret Network address.

    Frontend calls this to show user's deposit history and pending deposits.
    """
    if not bridge.db:
        raise HTTPException(status_code=503, detail="Database not initialized")

    try:
        deposits = []

        # Get subaddress mapping
        mapping = await bridge.db.get_subaddress_for_secret_address(secret_address)
        if mapping:
            # TODO: Query from database processed_deposits table
            # For now, return empty list
            pass

        return deposits
    except Exception as e:
        logger.error(f"Failed to get deposits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deposit/{tx_hash}", response_model=DepositStatus)
async def get_deposit_status(
    tx_hash: str,
    bridge: SimpleBridge = Depends(get_bridge)
):
    """Get status of a specific deposit transaction.

    Frontend polls this to show confirmation progress.
    """
    if not bridge.db:
        raise HTTPException(status_code=503, detail="Database not initialized")

    try:
        # Check if deposit is processed
        is_processed = await bridge.db.is_deposit_processed(tx_hash)

        if is_processed:
            # TODO: Get full deposit info from database
            return DepositStatus(
                tx_hash=tx_hash,
                amount=0,  # TODO: Get from DB
                confirmations=10,
                required_confirmations=bridge.config.min_confirmations,
                status="completed",
                monero_address="",  # TODO
                secret_address="",  # TODO
                block_height=0,  # TODO
            )
        else:
            # Check Monero blockchain for this tx
            # TODO: Query Monero RPC for tx status
            raise HTTPException(status_code=404, detail="Deposit not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deposit status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
