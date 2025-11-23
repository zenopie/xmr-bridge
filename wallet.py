"""Wallet management for Secret Network using Secret SDK."""

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip44Coins
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_string_canonize
import bech32

from core.errors import ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class Wallet:
    """Secret Network wallet."""
    address: str  # The participant ID (e.g., "secret1abc...")
    mnemonic: str
    private_key: bytes
    public_key: bytes
    signing_key: SigningKey


def load_wallet_from_mnemonic(mnemonic: str) -> Wallet:
    """Load wallet from mnemonic phrase using BIP39/BIP44.

    Args:
        mnemonic: 12 or 24-word mnemonic phrase

    Returns:
        Wallet instance

    Raises:
        ConfigurationError: If mnemonic is invalid
    """
    if not mnemonic or not mnemonic.strip():
        raise ConfigurationError("Mnemonic cannot be empty")

    mnemonic = mnemonic.strip()

    # Validate mnemonic
    if not Bip39MnemonicValidator().IsValid(mnemonic):
        raise ConfigurationError("Invalid mnemonic phrase")

    logger.info("Loading wallet from mnemonic")

    # Generate seed from mnemonic
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()

    # Derive keys using BIP44 for Cosmos chains
    # Path: m/44'/529'/0'/0/0 (529 is the coin type for Secret Network)
    bip44_mnemonic = Bip44.FromSeed(seed_bytes, Bip44Coins.COSMOS)
    bip44_account = bip44_mnemonic.Purpose().Coin().Account(0).Change(0).AddressIndex(0)

    # Get private key (32 bytes)
    private_key_bytes = bip44_account.PrivateKey().Raw().ToBytes()

    # Create signing key from private key (secp256k1)
    signing_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)

    # Get public key (compressed, 33 bytes)
    verifying_key = signing_key.get_verifying_key()
    public_key_bytes = verifying_key.to_string("compressed")

    # Derive Secret Network address from public key
    # 1. SHA256 hash of public key
    sha256_hash = hashlib.sha256(public_key_bytes).digest()

    # 2. RIPEMD160 hash of SHA256 hash
    import hashlib
    h = hashlib.new('ripemd160')
    h.update(sha256_hash)
    ripemd_hash = h.digest()

    # 3. Encode with Bech32 using 'secret' prefix
    address = bech32.bech32_encode('secret', bech32.convertbits(ripemd_hash, 8, 5))

    logger.info(f"Loaded wallet with address: {address}")

    return Wallet(
        address=address,
        mnemonic=mnemonic,
        private_key=private_key_bytes,
        public_key=public_key_bytes,
        signing_key=signing_key
    )


def load_wallet_from_keyfile(keyfile_path: str) -> Wallet:
    """Load wallet from encrypted keyfile.

    Args:
        keyfile_path: Path to encrypted key file

    Returns:
        Wallet instance

    Raises:
        ConfigurationError: If keyfile is invalid or cannot be decrypted
    """
    logger.info(f"Loading wallet from keyfile: {keyfile_path}")

    # TODO: Implement keyfile loading
    # - Read encrypted keyfile (JSON format)
    # - Prompt for password
    # - Decrypt and parse keys
    # - Derive address

    raise NotImplementedError("Keyfile loading not yet implemented")


def load_wallet(mnemonic: Optional[str] = None, keyfile: Optional[str] = None) -> Wallet:
    """Load wallet from mnemonic or keyfile.

    Args:
        mnemonic: Optional mnemonic phrase
        keyfile: Optional path to keyfile

    Returns:
        Wallet instance

    Raises:
        ConfigurationError: If neither mnemonic nor keyfile is provided
    """
    if mnemonic:
        return load_wallet_from_mnemonic(mnemonic)
    elif keyfile:
        return load_wallet_from_keyfile(keyfile)
    else:
        raise ConfigurationError("Must provide either mnemonic or keyfile")


def generate_frost_keypair(wallet: Wallet) -> tuple[bytes, bytes]:
    """Generate FROST keypair for threshold signatures.

    Args:
        wallet: Wallet instance

    Returns:
        Tuple of (private_key, public_key) for FROST
    """
    logger.info("Generating FROST keypair")

    # TODO: Implement proper FROST key generation
    # This should derive a separate key for FROST signatures
    # (different from the wallet signing key)

    # Placeholder: derive from wallet private key
    frost_seed = hashlib.sha256(wallet.private_key + b"frost").digest()
    frost_private_key = frost_seed[:32]
    frost_public_key = hashlib.sha256(frost_private_key).digest()

    logger.info("Generated FROST keypair")

    return (frost_private_key, frost_public_key)


def sign_transaction(wallet: Wallet, message: bytes) -> bytes:
    """Sign a transaction with the wallet's private key.

    Args:
        wallet: Wallet instance
        message: Message bytes to sign

    Returns:
        Signature bytes
    """
    signature = wallet.signing_key.sign_digest_deterministic(
        message,
        hashfunc=hashlib.sha256,
        sigencode=sigencode_string_canonize
    )
    return signature
