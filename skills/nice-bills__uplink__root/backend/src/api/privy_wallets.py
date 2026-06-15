"""
Privy Wallet API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.database import get_db
from src.services.privy_wallet import PrivyWalletService, get_privy_service
from src.schemas import WalletResponse, WalletCreate
from src.models import Wallet as WalletModel
from sqlalchemy import select

router = APIRouter(prefix="/wallets/privy", tags=["privy-wallets"])


@router.post("/create", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_privy_wallet(
    user_id: str,
    twitter_handle: Optional[str] = None,
    privy_service: PrivyWalletService = Depends(get_privy_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new Privy embedded wallet for a user

    This is called when a user tweets @Genesis without a wallet address
    and replies "create" or doesn't provide one.
    """
    try:
        # Check if wallet already exists
        result = await db.execute(select(WalletModel).where(WalletModel.user_id == user_id))
        existing = result.scalar_one_or_none()

        if existing:
            return WalletResponse(
                id=existing.id,
                address=existing.address,
                chain_type=existing.chain_type,
                user_id=existing.user_id,
                twitter_handle=existing.twitter_handle,
                created_at=existing.created_at,
                message="Wallet already exists",
            )

        # Create new Privy wallet
        wallet_data = await privy_service.create_wallet_for_user(
            user_id=user_id, twitter_handle=twitter_handle, chain_type="ethereum"
        )

        # Store in database
        new_wallet = WalletModel(
            wallet_id=wallet_data["wallet_id"],
            address=wallet_data["address"],
            chain_type=wallet_data["chain_type"],
            user_id=user_id,
            twitter_handle=twitter_handle,
            provider="privy",
            encrypted_private_key=None,  # Privy holds the keys
        )

        db.add(new_wallet)
        await db.commit()
        await db.refresh(new_wallet)

        return WalletResponse(
            id=new_wallet.id,
            address=new_wallet.address,
            chain_type=new_wallet.chain_type,
            user_id=new_wallet.user_id,
            twitter_handle=new_wallet.twitter_handle,
            created_at=new_wallet.created_at,
            message="Privy wallet created successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Privy wallet: {str(e)}",
        )


@router.get("/user/{user_id}", response_model=WalletResponse)
async def get_user_privy_wallet(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get a user's Privy wallet by user ID"""
    result = await db.execute(
        select(WalletModel).where(
            (WalletModel.user_id == user_id) & (WalletModel.provider == "privy")
        )
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No Privy wallet found for this user"
        )

    return WalletResponse(
        id=wallet.id,
        address=wallet.address,
        chain_type=wallet.chain_type,
        user_id=wallet.user_id,
        twitter_handle=wallet.twitter_handle,
        created_at=wallet.created_at,
    )


@router.get("/twitter/{twitter_handle}", response_model=WalletResponse)
async def get_wallet_by_twitter(twitter_handle: str, db: AsyncSession = Depends(get_db)):
    """Get wallet by Twitter handle"""
    result = await db.execute(
        select(WalletModel).where(
            (WalletModel.twitter_handle == twitter_handle) & (WalletModel.provider == "privy")
        )
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No wallet found for this Twitter handle"
        )

    return WalletResponse(
        id=wallet.id,
        address=wallet.address,
        chain_type=wallet.chain_type,
        user_id=wallet.user_id,
        twitter_handle=wallet.twitter_handle,
        created_at=wallet.created_at,
    )


@router.post("/{wallet_id}/send")
async def send_from_privy_wallet(
    wallet_id: str,
    to_address: str,
    amount: str,
    chain: str = "base-sepolia",
    privy_service: PrivyWalletService = Depends(get_privy_service),
):
    """
    Send transaction from a Privy wallet
    This is used when withdrawing funds from treasury to user's wallet
    """
    try:
        tx = await privy_service.send_transaction(
            wallet_id=wallet_id, to_address=to_address, amount=amount, chain=chain
        )

        return {
            "success": True,
            "tx_hash": tx["tx_hash"],
            "status": tx["status"],
            "message": "Transaction sent successfully",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send transaction: {str(e)}",
        )


@router.get("/{wallet_id}/balance")
async def get_privy_wallet_balance(
    wallet_id: str,
    chain: str = "base-sepolia",
    privy_service: PrivyWalletService = Depends(get_privy_service),
):
    """Get balance of a Privy wallet"""
    try:
        balance = await privy_service.get_wallet_balance(wallet_id=wallet_id, chain=chain)

        return balance

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get balance: {str(e)}",
        )
