"""FROST signing coordinator."""

import logging
from typing import List, Dict, Any

from core.errors import FrostError
from core.types import ParticipantId, SignatureShare

logger = logging.getLogger(__name__)


class FrostCoordinator:
    """Coordinates FROST threshold signature protocol.

    The coordinator orchestrates the distributed key generation (DKG) and
    signing rounds among participants.
    """

    def __init__(self, threshold: int, total_participants: int):
        """Initialize FROST coordinator.

        Args:
            threshold: Minimum number of participants needed to sign
            total_participants: Total number of participants in the protocol
        """
        if threshold > total_participants:
            raise FrostError(
                f"Threshold ({threshold}) cannot exceed total participants ({total_participants})"
            )

        self.threshold = threshold
        self.total_participants = total_participants
        self._public_key: bytes = b""
        logger.info(
            f"Initialized FROST coordinator: {threshold} of {total_participants}"
        )

    async def run_dkg(self) -> bytes:
        """Run Distributed Key Generation protocol.

        Returns:
            The generated public key

        Raises:
            FrostError: If DKG fails
        """
        logger.info("Starting DKG protocol")

        # TODO: Implement FROST DKG
        # Round 1: Collect commitments from participants
        # Round 2: Generate and distribute shares
        # Aggregate to create group public key

        raise NotImplementedError("DKG not yet implemented")

    async def coordinate_signing(
        self,
        message: bytes,
        participants: List[ParticipantId]
    ) -> bytes:
        """Coordinate a signing round.

        Args:
            message: Message to sign
            participants: List of participant IDs participating in signing

        Returns:
            The final signature

        Raises:
            FrostError: If signing fails
        """
        if len(participants) < self.threshold:
            raise FrostError(
                f"Not enough participants: need {self.threshold}, got {len(participants)}"
            )

        logger.info(f"Coordinating signing with {len(participants)} participants")

        # TODO: Implement FROST signing protocol
        # Round 1: Collect commitments from participants
        # Round 2: Collect signature shares
        # Aggregate shares into final signature

        raise NotImplementedError("Signing coordination not yet implemented")

    async def aggregate_signature_shares(
        self,
        shares: Dict[ParticipantId, SignatureShare]
    ) -> bytes:
        """Aggregate signature shares into final signature.

        Args:
            shares: Map of participant IDs to their signature shares

        Returns:
            The aggregated signature
        """
        if len(shares) < self.threshold:
            raise FrostError(
                f"Not enough shares: need {self.threshold}, got {len(shares)}"
            )

        logger.info(f"Aggregating {len(shares)} signature shares")

        # TODO: Implement signature aggregation
        raise NotImplementedError("Signature aggregation not yet implemented")

    def get_public_key(self) -> bytes:
        """Get the group public key.

        Returns:
            The group public key
        """
        if not self._public_key:
            raise FrostError("Public key not initialized - run DKG first")
        return self._public_key
