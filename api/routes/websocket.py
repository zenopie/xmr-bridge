"""WebSocket endpoint for real-time updates."""

import logging
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates.

    Frontend connects to receive live updates on deposits/withdrawals.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle pings
            data = await websocket.receive_text()

            # Echo back for heartbeat
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Helper functions to broadcast updates
async def broadcast_deposit_update(tx_hash: str, confirmations: int):
    """Broadcast deposit confirmation update to all connected clients."""
    await manager.broadcast({
        "type": "deposit_update",
        "tx_hash": tx_hash,
        "confirmations": confirmations,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


async def broadcast_deposit_completed(tx_hash: str, secret_tx_hash: str):
    """Broadcast deposit completion to all connected clients."""
    await manager.broadcast({
        "type": "deposit_completed",
        "monero_tx_hash": tx_hash,
        "secret_tx_hash": secret_tx_hash,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


async def broadcast_withdrawal_update(secret_tx_hash: str, status: str):
    """Broadcast withdrawal status update to all connected clients."""
    await manager.broadcast({
        "type": "withdrawal_update",
        "secret_tx_hash": secret_tx_hash,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
