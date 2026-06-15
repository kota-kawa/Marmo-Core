"""
Privy Wallet Service
Manages embedded wallets for AI agents and users
"""

import os
from typing import Optional
from uuid import UUID
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models import Wallet, UserType
from src.config import get_settings

settings = get_settings()


class PrivyService:
    """Service for managing Privy embedded wallets"""

    def __init__(self):
        self.app_id = os.getenv("PRIVY_APP_ID", "")
        self.app_secret = os.getenv("PRIVY_APP_SECRET", "")
        self.base_url = "https://auth.privy.io/api/v1"

        if not self.app_id or not self.app_secret:
            raise ValueError("PRIVY_APP_ID and PRIVY_APP_SECRET must be set")

    async def create_wallet(self, user_id: str, chain_type: str = "ethereum") -> dict:
        """
        Create a new Privy embedded wallet for a user

        Args:
            user_id: Unique identifier for the user (agent_id or user_id)
            chain_type: Blockchain type (ethereum, polygon, etc.)

        Returns:
            Wallet data including address and ID
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/wallets",
                headers={
                    "privy-app-id": self.app_id,
                    "privy-app-secret": self.app_secret,
                    "Content-Type": "application/json",
                },
                json={"user_id": user_id, "chain_type": chain_type},
            )

            if response.status_code != 201:
                raise Exception(f"Failed to create wallet: {response.text}")

            return response.json()

    async def get_or_create_wallet(
        self, db: AsyncSession, entity_id: str, user_type: UserType, chain_type: str = "ethereum"
    ) -> Wallet:
        """
        Get existing wallet or create new one via Privy

        Args:
            db: Database session
            entity_id: Agent ID or User ID
            user_type: AGENT or HUMAN
            chain_type: Blockchain type

        Returns:
            Wallet model instance
        """
        # Check if wallet already exists
        result = await db.execute(
            select(Wallet).where(Wallet.entity_id == entity_id, Wallet.user_type == user_type)
        )
        existing_wallet = result.scalar_one_or_none()

        if existing_wallet:
            return existing_wallet

        # Create new Privy wallet
        wallet_data = await self.create_wallet(
            user_id=f"{user_type.value}:{entity_id}", chain_type=chain_type
        )

        # Save to database
        new_wallet = Wallet(
            entity_id=entity_id,
            user_type=user_type,
            address=wallet_data["address"],
            wallet_provider="privy",
            wallet_id=wallet_data["id"],
            chain_type=chain_type,
            is_active=True,
        )

        db.add(new_wallet)
        await db.commit()
        await db.refresh(new_wallet)

        return new_wallet

    async def get_wallet_by_entity(
        self, db: AsyncSession, entity_id: str, user_type: UserType
    ) -> Optional[Wallet]:
        """Get wallet by entity ID and type"""
        result = await db.execute(
            select(Wallet).where(Wallet.entity_id == entity_id, Wallet.user_type == user_type)
        )
        return result.scalar_one_or_none()

    async def sign_transaction(self, wallet_id: str, transaction: dict) -> dict:
        """
        Sign a transaction using Privy wallet

        Args:
            wallet_id: Privy wallet ID
            transaction: Transaction data to sign

        Returns:
            Signed transaction data
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/wallets/{wallet_id}/rpc",
                headers={
                    "privy-app-id": self.app_id,
                    "privy-app-secret": self.app_secret,
                    "Content-Type": "application/json",
                },
                json={"method": "eth_signTransaction", "params": [transaction]},
            )

            if response.status_code != 200:
                raise Exception(f"Failed to sign transaction: {response.text}")

            return response.json()


# Singleton instance
_privy_service: Optional[PrivyService] = None


def get_privy_service() -> PrivyService:
    """Get or create Privy service singleton"""
    global _privy_service
    if _privy_service is None:
        _privy_service = PrivyService()
    return _privy_service
