"""P2P networking implementation."""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Callable, Any

from core.errors import NetworkError

logger = logging.getLogger(__name__)


@dataclass
class P2PConfig:
    """Configuration for P2P network."""
    listen_address: str
    peer_addresses: List[str]
    participant_id: int


class P2PNetwork:
    """Manages P2P communication between bridge participants.

    Uses a simplified networking approach. For production, consider
    using libp2p or a similar robust P2P library.
    """

    def __init__(self, config: P2PConfig):
        """Initialize P2P network.

        Args:
            config: P2P configuration
        """
        self.config = config
        self._running = False
        self._server: Optional[asyncio.Server] = None
        self._connections: List[asyncio.StreamWriter] = []
        self._message_handler: Optional[Callable[[dict], None]] = None
        logger.info(
            f"Initialized P2P network for participant {config.participant_id}"
        )

    async def start(self) -> None:
        """Start the P2P network."""
        if self._running:
            logger.warning("P2P network already running")
            return

        logger.info(f"Starting P2P network on {self.config.listen_address}")

        # Parse listen address
        # Format: /ip4/0.0.0.0/tcp/9000
        parts = self.config.listen_address.split("/")
        if len(parts) >= 5 and parts[3] == "tcp":
            host = parts[2]
            port = int(parts[4])
        else:
            raise NetworkError(f"Invalid listen address: {self.config.listen_address}")

        # Start server
        self._server = await asyncio.start_server(
            self._handle_connection,
            host,
            port
        )

        self._running = True

        # Connect to peers
        asyncio.create_task(self._connect_to_peers())

        logger.info(f"P2P network started on {host}:{port}")

    async def stop(self) -> None:
        """Stop the P2P network."""
        if not self._running:
            return

        logger.info("Stopping P2P network")
        self._running = False

        # Close all connections
        for writer in self._connections:
            writer.close()
            await writer.wait_closed()

        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        logger.info("P2P network stopped")

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all peers.

        Args:
            message: Message dictionary to broadcast
        """
        logger.debug(f"Broadcasting message to {len(self._connections)} peers")

        # TODO: Serialize message properly
        # TODO: Handle connection failures

        for writer in self._connections:
            try:
                # Simple JSON encoding (placeholder)
                data = str(message).encode() + b"\n"
                writer.write(data)
                await writer.drain()
            except Exception as e:
                logger.error(f"Failed to send to peer: {e}")

    def set_message_handler(self, handler: Callable[[dict], None]) -> None:
        """Set the callback for handling received messages.

        Args:
            handler: Function to call when message is received
        """
        self._message_handler = handler

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle an incoming connection.

        Args:
            reader: Stream reader
            writer: Stream writer
        """
        addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {addr}")

        self._connections.append(writer)

        try:
            while self._running:
                data = await reader.readline()
                if not data:
                    break

                # TODO: Parse message properly
                # TODO: Verify message authenticity
                message = eval(data.decode())  # Placeholder - use proper JSON

                if self._message_handler:
                    self._message_handler(message)

        except Exception as e:
            logger.error(f"Error handling connection from {addr}: {e}")
        finally:
            if writer in self._connections:
                self._connections.remove(writer)
            writer.close()
            await writer.wait_closed()
            logger.info(f"Connection from {addr} closed")

    async def _connect_to_peers(self) -> None:
        """Connect to configured peer addresses."""
        for peer_addr in self.config.peer_addresses:
            try:
                # Parse peer address
                # Format: /ip4/127.0.0.1/tcp/9001
                parts = peer_addr.split("/")
                if len(parts) >= 5 and parts[3] == "tcp":
                    host = parts[2]
                    port = int(parts[4])
                else:
                    logger.warning(f"Invalid peer address: {peer_addr}")
                    continue

                logger.info(f"Connecting to peer {host}:{port}")

                reader, writer = await asyncio.open_connection(host, port)
                self._connections.append(writer)

                # Start receiving messages
                asyncio.create_task(
                    self._handle_connection(reader, writer)
                )

                logger.info(f"Connected to peer {host}:{port}")

            except Exception as e:
                logger.error(f"Failed to connect to peer {peer_addr}: {e}")
