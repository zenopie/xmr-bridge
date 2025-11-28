"""Shared dependencies for API routes."""

from typing import Optional
from fastapi import HTTPException
from bridge import SimpleBridge

# Global bridge instance
_bridge: Optional[SimpleBridge] = None


def set_bridge(bridge: SimpleBridge) -> None:
    """Set the global bridge instance."""
    global _bridge
    _bridge = bridge


def get_bridge() -> SimpleBridge:
    """Get the bridge instance dependency."""
    if not _bridge:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    return _bridge
