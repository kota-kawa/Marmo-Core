"""
Privy Wallet Integration for Genesis Platform
Uses Privy for embedded wallet generation and management
"""

import os
from typing import Optional, Dict, Any
from privy import PrivyAPI
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Wallet as WalletModel
from sqlalchemy import select


class PrivyWalletService:
    """Service for generating and managing wallets via Privy"""

    def __init__(self):
        """Initialize Privy client with app credentials"""
        self.app_id = os.getenv("PRIVY_APP_ID")
        self.app_secret = os.getenv("PRIVY_APP_SECRET")

        if not self.app_id or not self.app_secret:
            raise ValueError("PRIVY_APP_ID and PRIVY_APP_SECRET must be set in environment")

        self.client = PrivyAPI(app_id=self.app_id, app_secret=self.app_secret)

    async def create_wallet_for_user(
        self, user_id: str, twitter_handle: Optional[str] = None, chain_type: str = "ethereum"
    ) -> Dict[str, Any]:
        """
        Create a new embedded wallet for a user via Privy

        Args:
            user_id: Unique identifier for the user
            twitter_handle: Optional Twitter handle for reference
            chain_type: "ethereum" or "solana"

        Returns:
            Dict with wallet_id, address, and other details
        """
        try:
            # Create wallet via Privy API
            wallet = self.client.wallets.create(chain_type=chain_type)

            # Store in our database for reference
            wallet_data = {
                "wallet_id": wallet.id,
                "address": wallet.address,
                "chain_type": chain_type,
                "user_id": user_id,
                "twitter_handle": twitter_handle,
                "provider": "privy",
            }

            return wallet_data

        except Exception as e:
            raise Exception(f"Failed to create Privy wallet: {str(e)}")

    async def get_or_create_wallet(
        self, user_id: str, twitter_handle: Optional[str] = None, db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get existing wallet or create new one

        Returns:
            Wallet data (existing or newly created)
        """
        if db:
            # Check if wallet exists in our database
            result = await db.execute(select(WalletModel).where(WalletModel.user_id == user_id))
            existing = result.scalar_one_or_none()

            if existing:
                return {
                    "wallet_id": existing.wallet_id,
                    "address": existing.address,
                    "chain_type": existing.chain_type,
                    "user_id": existing.user_id,
                    "twitter_handle": existing.twitter_handle,
                    "provider": "privy",
                    "exists": True,
                }

        # Create new wallet
        wallet = await self.create_wallet_for_user(user_id, twitter_handle)
        wallet["exists"] = False

        # Store in database if provided
        if db:
            new_wallet = WalletModel(
                wallet_id=wallet["wallet_id"],
                address=wallet["address"],
                chain_type=wallet["chain_type"],
                user_id=user_id,
                twitter_handle=twitter_handle,
                provider="privy",
                encrypted_private_key=None,  # Privy holds the keys
            )
            db.add(new_wallet)
            await db.commit()

        return wallet

    async def send_transaction(
        self, wallet_id: str, to_address: str, amount: str, chain: str = "base-sepolia"
    ) -> Dict[str, Any]:
        """
        Send transaction from a Privy wallet

        Args:
            wallet_id: Privy wallet ID
            to_address: Recipient address
            amount: Amount in wei (for ETH) or smallest unit
            chain: Chain to send on

        Returns:
            Transaction details
        """
        try:
            transaction = self.client.wallets.send_transaction(
                wallet_id=wallet_id, to=to_address, value=amount, chain=chain
            )

            return {
                "tx_hash": transaction.hash,
                "status": transaction.status,
                "wallet_id": wallet_id,
                "to": to_address,
                "amount": amount,
            }

        except Exception as e:
            raise Exception(f"Failed to send transaction: {str(e)}")

    async def get_wallet_balance(
        self, wallet_id: str, chain: str = "base-sepolia"
    ) -> Dict[str, Any]:
        """Get wallet balance"""
        try:
            balance = self.client.wallets.get_balance(wallet_id=wallet_id, chain=chain)

            return {
                "wallet_id": wallet_id,
                "balance": balance.amount,
                "currency": balance.currency,
                "chain": chain,
            }

        except Exception as e:
            raise Exception(f"Failed to get balance: {str(e)}")

    async def export_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """
        Export wallet (allows user to take their keys)

        Note: This requires proper authentication/authorization
        """
        try:
            # Privy allows users to export their wallets
            export_data = self.client.wallets.export(wallet_id)

            return {
                "wallet_id": wallet_id,
                "export_data": export_data,
                "message": "Wallet exported successfully. Store these keys securely!",
            }

        except Exception as e:
            raise Exception(f"Failed to export wallet: {str(e)}")


# FastAPI dependency
async def get_privy_service():
    """Dependency to get Privy service instance"""
    return PrivyWalletService()


# Example usage in Twitter bot:
"""
from src.services.privy_wallet import PrivyWalletService, get_privy_service

# In your Twitter bot handler:
privy_service = await get_privy_service()

# When user doesn't provide wallet:
wallet = await privy_service.get_or_create_wallet(
    user_id=twitter_handle,
    twitter_handle=twitter_handle,
    db=db
)

# Reply with wallet address
reply = f"Campaign created! Wallet: {wallet['address']}"

# Later, to send funds from treasury to user's wallet:
tx = await privy_service.send_transaction(
    wallet_id=treasury_wallet_id,
    to_address=wallet['address'],
    amount="1000000000000000000"  # 1 MON in wei
)
"""
