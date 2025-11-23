"""FROST participant implementation."""

import logging
from typing import Optional

from core.errors import FrostError
from core.types import ParticipantId, SignatureShare

logger = logging.getLogger(__name__)


class FrostParticipant:
    """Represents a participant in the FROST protocol.

    Each participant holds a secret share and participates in
    distributed signing operations.
    """

    def __init__(self, participant_id: ParticipantId):
        """Initialize FROST participant.

        Args:
            participant_id: Unique identifier for this participant
        """
        self.participant_id = participant_id
        self._secret_share: Optional[bytes] = None
        self._public_key: Optional[bytes] = None
        logger.info(f"Initialized FROST participant {participant_id}")

    async def participate_in_dkg(self) -> dict:
        """Participate in Distributed Key Generation.

        Returns:
            Commitment data to send to coordinator

        Raises:
            FrostError: If DKG participation fails
        """
        logger.info(f"Participant {self.participant_id} joining DKG")

        # TODO: Implement DKG participation
        # Generate polynomial coefficients
        # Create commitments
        # Compute shares for other participants

        raise NotImplementedError("DKG participation not yet implemented")

    async def create_signature_share(
        self,
        message: bytes,
        nonce_commitment: bytes
    ) -> SignatureShare:
        """Create a signature share for a message.

        Args:
            message: Message to sign
            nonce_commitment: Nonce commitment from signing round 1

        Returns:
            This participant's signature share

        Raises:
            FrostError: If share creation fails
        """
        if not self._secret_share:
            raise FrostError("Secret share not initialized - complete DKG first")

        logger.info(f"Participant {self.participant_id} creating signature share")

        # TODO: Implement signature share creation
        # Use secret share and nonce to create partial signature

        raise NotImplementedError("Signature share creation not yet implemented")

    def set_secret_share(self, share: bytes) -> None:
        """Set the secret share (from DKG).

        Args:
            share: The secret share bytes
        """
        self._secret_share = share
        logger.info(f"Secret share set for participant {self.participant_id}")

    def get_public_key(self) -> bytes:
        """Get this participant's public key.

        Returns:
            The public key

        Raises:
            FrostError: If public key not initialized
        """
        if not self._public_key:
            raise FrostError("Public key not initialized")
        return self._public_key
