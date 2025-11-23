"""Error types for XMR Bridge."""


class BridgeError(Exception):
    """Base exception for all bridge errors."""
    pass


class MoneroError(BridgeError):
    """Errors related to Monero operations."""
    pass


class FrostError(BridgeError):
    """Errors related to FROST threshold signatures."""
    pass


class NetworkError(BridgeError):
    """Errors related to P2P networking."""
    pass


class SecretNetworkError(BridgeError):
    """Errors related to Secret Network operations."""
    pass


class ConfigurationError(BridgeError):
    """Errors related to configuration."""
    pass


class RPCError(MoneroError):
    """Errors from RPC calls."""
    def __init__(self, message: str, method: str = "", details: str = ""):
        self.method = method
        self.details = details
        super().__init__(f"RPC Error [{method}]: {message} - {details}")
