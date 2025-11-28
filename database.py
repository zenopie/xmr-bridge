"""Database management for the bridge."""

import sqlite3
import logging
from typing import Optional, List, Tuple
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class BridgeDatabase:
    """SQLite database for bridge state management."""

    def __init__(self, db_path: str = "bridge.db"):
        """Initialize the database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        logger.info(f"Initialized database at {db_path}")

    async def start(self) -> None:
        """Initialize database connection and create tables."""
        # Run blocking DB operations in executor
        await asyncio.get_event_loop().run_in_executor(None, self._init_db)
        logger.info("Database started")

    def _init_db(self) -> None:
        """Internal: Initialize database connection and schema."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Create tables
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS subaddress_mappings (
                account INTEGER NOT NULL,
                subaddress_index INTEGER NOT NULL,
                subaddress TEXT NOT NULL,
                secret_address TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (account, subaddress_index)
            );

            CREATE INDEX IF NOT EXISTS idx_subaddress
                ON subaddress_mappings(subaddress);
            CREATE INDEX IF NOT EXISTS idx_secret_address
                ON subaddress_mappings(secret_address);

            CREATE TABLE IF NOT EXISTS processed_deposits (
                tx_hash TEXT PRIMARY KEY,
                amount INTEGER NOT NULL,
                subaddress TEXT NOT NULL,
                secret_address TEXT NOT NULL,
                secret_tx_hash TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS processed_withdrawals (
                secret_tx_hash TEXT PRIMARY KEY,
                amount INTEGER NOT NULL,
                monero_address TEXT NOT NULL,
                monero_tx_hash TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bridge_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    async def stop(self) -> None:
        """Close database connection."""
        if self.conn:
            await asyncio.get_event_loop().run_in_executor(None, self.conn.close)
        logger.info("Database stopped")

    async def save_subaddress_mapping(
        self,
        account: int,
        index: int,
        subaddress: str,
        secret_address: str
    ) -> None:
        """Save a subaddress mapping.

        Args:
            account: Subaddress account
            index: Subaddress index
            subaddress: Monero subaddress
            secret_address: Secret Network address
        """
        def _save():
            self.conn.execute(
                """INSERT OR REPLACE INTO subaddress_mappings
                   (account, subaddress_index, subaddress, secret_address)
                   VALUES (?, ?, ?, ?)""",
                (account, index, subaddress, secret_address)
            )
            self.conn.commit()

        await asyncio.get_event_loop().run_in_executor(None, _save)
        logger.debug(f"Saved mapping: subaddress {index} -> {secret_address[:16]}...")

    async def get_secret_address_for_subaddress(
        self,
        account: int,
        index: int
    ) -> Optional[str]:
        """Get Secret Network address for a subaddress.

        Args:
            account: Subaddress account
            index: Subaddress index

        Returns:
            Secret Network address or None
        """
        def _get():
            cursor = self.conn.execute(
                """SELECT secret_address FROM subaddress_mappings
                   WHERE account = ? AND subaddress_index = ?""",
                (account, index)
            )
            row = cursor.fetchone()
            return row["secret_address"] if row else None

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def get_subaddress_for_secret_address(
        self,
        secret_address: str
    ) -> Optional[Tuple[int, int, str]]:
        """Get subaddress info for a Secret Network address.

        Args:
            secret_address: Secret Network address

        Returns:
            Tuple of (account, index, subaddress) or None
        """
        def _get():
            cursor = self.conn.execute(
                """SELECT account, subaddress_index, subaddress
                   FROM subaddress_mappings
                   WHERE secret_address = ?""",
                (secret_address,)
            )
            row = cursor.fetchone()
            if row:
                return (row["account"], row["subaddress_index"], row["subaddress"])
            return None

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def get_next_subaddress_index(self, account: int = 0) -> int:
        """Get the next available subaddress index.

        Args:
            account: Account number

        Returns:
            Next available index
        """
        def _get():
            cursor = self.conn.execute(
                """SELECT MAX(subaddress_index) as max_index
                   FROM subaddress_mappings
                   WHERE account = ?""",
                (account,)
            )
            row = cursor.fetchone()
            max_index = row["max_index"] if row["max_index"] is not None else 0
            return max_index + 1

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def is_deposit_processed(self, tx_hash: str) -> bool:
        """Check if a deposit has been processed.

        Args:
            tx_hash: Monero transaction hash

        Returns:
            True if processed
        """
        def _check():
            cursor = self.conn.execute(
                "SELECT 1 FROM processed_deposits WHERE tx_hash = ?",
                (tx_hash,)
            )
            return cursor.fetchone() is not None

        return await asyncio.get_event_loop().run_in_executor(None, _check)

    async def mark_deposit_processed(
        self,
        tx_hash: str,
        amount: int,
        subaddress: str,
        secret_address: str,
        secret_tx_hash: str
    ) -> None:
        """Mark a deposit as processed.

        Args:
            tx_hash: Monero transaction hash
            amount: Amount in atomic units
            subaddress: Receiving subaddress
            secret_address: Recipient Secret address
            secret_tx_hash: Secret Network transaction hash
        """
        def _save():
            self.conn.execute(
                """INSERT OR REPLACE INTO processed_deposits
                   (tx_hash, amount, subaddress, secret_address, secret_tx_hash)
                   VALUES (?, ?, ?, ?, ?)""",
                (tx_hash, amount, subaddress, secret_address, secret_tx_hash)
            )
            self.conn.commit()

        await asyncio.get_event_loop().run_in_executor(None, _save)

    async def is_withdrawal_processed(self, secret_tx_hash: str) -> bool:
        """Check if a withdrawal has been processed.

        Args:
            secret_tx_hash: Secret Network transaction hash

        Returns:
            True if processed
        """
        def _check():
            cursor = self.conn.execute(
                "SELECT 1 FROM processed_withdrawals WHERE secret_tx_hash = ?",
                (secret_tx_hash,)
            )
            return cursor.fetchone() is not None

        return await asyncio.get_event_loop().run_in_executor(None, _check)

    async def mark_withdrawal_processed(
        self,
        secret_tx_hash: str,
        amount: int,
        monero_address: str,
        monero_tx_hash: str
    ) -> None:
        """Mark a withdrawal as processed.

        Args:
            secret_tx_hash: Secret Network transaction hash
            amount: Amount in atomic units
            monero_address: Destination Monero address
            monero_tx_hash: Monero transaction hash
        """
        def _save():
            self.conn.execute(
                """INSERT OR REPLACE INTO processed_withdrawals
                   (secret_tx_hash, amount, monero_address, monero_tx_hash)
                   VALUES (?, ?, ?, ?)""",
                (secret_tx_hash, amount, monero_address, monero_tx_hash)
            )
            self.conn.commit()

        await asyncio.get_event_loop().run_in_executor(None, _save)

    async def get_state(self, key: str) -> Optional[str]:
        """Get a state value.

        Args:
            key: State key

        Returns:
            State value or None
        """
        def _get():
            cursor = self.conn.execute(
                "SELECT value FROM bridge_state WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row["value"] if row else None

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def set_state(self, key: str, value: str) -> None:
        """Set a state value.

        Args:
            key: State key
            value: State value
        """
        def _set():
            self.conn.execute(
                """INSERT OR REPLACE INTO bridge_state (key, value, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (key, value)
            )
            self.conn.commit()

        await asyncio.get_event_loop().run_in_executor(None, _set)
