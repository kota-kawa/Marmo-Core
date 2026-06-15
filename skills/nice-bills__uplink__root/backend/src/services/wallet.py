"""Wallet service for generating and managing Ethereum wallets."""

from datetime import datetime
from uuid import UUID

from cryptography.fernet import Fernet
from eth_account import Account
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from src.config import get_settings
from src.models import Wallet

settings = get_settings()


def get_fernet() -> Fernet:
    """Get Fernet instance with encryption key."""
    key = settings.ENCRYPTION_KEY
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable not set")
    # Fernet key must be 32 bytes, base64-encoded
    # If user provides raw key, encode it properly
    if len(key) == 44:  # Already base64-encoded Fernet key
        return Fernet(key.encode())
    # Generate a proper Fernet key from provided key material
    import base64
    import hashlib

    key_bytes = hashlib.sha256(key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def generate_wallet() -> tuple[str, str]:
    """Generate a new Ethereum wallet.

    Returns:
        tuple: (address, private_key)
    """
    account = Account.create()
    return account.address, account.key.hex()


def encrypt_private_key(private_key: str) -> str:
    """Encrypt a private key using Fernet.

    Args:
        private_key: The private key to encrypt (hex string with 0x prefix)

    Returns:
        Encrypted private key as string
    """
    fernet = get_fernet()
    encrypted = fernet.encrypt(private_key.encode())
    return encrypted.decode()


def decrypt_private_key(encrypted_key: str) -> str:
    """Decrypt an encrypted private key.

    Args:
        encrypted_key: The encrypted private key

    Returns:
        Decrypted private key (hex string with 0x prefix)
    """
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_key.encode())
    return decrypted.decode()


def is_valid_address(address: str) -> bool:
    """Validate an Ethereum address.

    Args:
        address: The address to validate

    Returns:
        True if valid, False otherwise
    """
    return Web3.is_address(address)


class WalletService:
    """Service for wallet operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_wallet(
        self,
        user_id: str | None = None,
        twitter_handle: str | None = None,
    ) -> Wallet:
        """Create a new wallet for a user.

        Args:
            user_id: Optional user identifier
            twitter_handle: Optional Twitter handle

        Returns:
            The created Wallet model instance
        """
        address, private_key = generate_wallet()
        encrypted_key = encrypt_private_key(private_key)

        wallet = Wallet(
            user_id=user_id,
            twitter_handle=twitter_handle.lower() if twitter_handle else None,
            address=address.lower(),
            encrypted_private_key=encrypted_key,
        )

        self.db.add(wallet)
        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet

    async def get_wallet_by_id(self, wallet_id: UUID) -> Wallet | None:
        """Get wallet by ID.

        Args:
            wallet_id: The wallet UUID

        Returns:
            Wallet if found, None otherwise
        """
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        return result.scalar_one_or_none()

    async def get_wallet_by_address(self, address: str) -> Wallet | None:
        """Get wallet by Ethereum address.

        Args:
            address: The Ethereum address

        Returns:
            Wallet if found, None otherwise
        """
        result = await self.db.execute(select(Wallet).where(Wallet.address == address.lower()))
        return result.scalar_one_or_none()

    async def get_wallet_by_user_id(self, user_id: str) -> Wallet | None:
        """Get wallet by user ID.

        Args:
            user_id: The user identifier

        Returns:
            Wallet if found, None otherwise
        """
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_wallet_by_twitter_handle(self, twitter_handle: str) -> Wallet | None:
        """Get wallet by Twitter handle.

        Args:
            twitter_handle: The Twitter handle

        Returns:
            Wallet if found, None otherwise
        """
        result = await self.db.execute(
            select(Wallet).where(Wallet.twitter_handle == twitter_handle.lower())
        )
        return result.scalar_one_or_none()

    async def export_wallet(self, wallet_id: UUID) -> dict | None:
        """Export wallet with decrypted private key.

        Args:
            wallet_id: The wallet UUID

        Returns:
            Dictionary with wallet details and private key, or None if not found
        """
        wallet = await self.get_wallet_by_id(wallet_id)
        if not wallet:
            return None

        private_key = decrypt_private_key(wallet.encrypted_private_key)

        return {
            "id": wallet.id,
            "address": wallet.address,
            "private_key": private_key,
            "user_id": wallet.user_id,
            "twitter_handle": wallet.twitter_handle,
            "created_at": wallet.created_at,
        }

    async def list_wallets(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Wallet]:
        """List all wallets.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of wallets
        """
        result = await self.db.execute(select(Wallet).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def delete_wallet(self, wallet_id: UUID) -> bool:
        """Delete a wallet.

        Args:
            wallet_id: The wallet UUID

        Returns:
            True if deleted, False if not found
        """
        wallet = await self.get_wallet_by_id(wallet_id)
        if not wallet:
            return False

        await self.db.delete(wallet)
        await self.db.commit()
        return True
