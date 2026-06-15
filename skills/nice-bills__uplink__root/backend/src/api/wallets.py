"""Wallet API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas import WalletCreate, WalletExport, WalletResponse
from src.services.wallet import WalletService, is_valid_address
from src.auth import verify_admin_key, verify_agent_key

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    wallet_data: WalletCreate,
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Create a new Ethereum wallet.

    Generates a new self-custodial wallet and stores the encrypted private key.
    """
    service = WalletService(db)

    # Check if wallet already exists for this user
    if wallet_data.user_id:
        existing = await service.get_wallet_by_user_id(wallet_data.user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Wallet already exists for user_id: {wallet_data.user_id}",
            )

    if wallet_data.twitter_handle:
        existing = await service.get_wallet_by_twitter_handle(wallet_data.twitter_handle)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Wallet already exists for twitter_handle: {wallet_data.twitter_handle}",
            )

    wallet = await service.create_wallet(
        user_id=wallet_data.user_id,
        twitter_handle=wallet_data.twitter_handle,
    )

    return wallet


@router.get("", response_model=list[WalletResponse])
async def list_wallets(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[WalletResponse]:
    """List all wallets."""
    service = WalletService(db)
    wallets = await service.list_wallets(skip=skip, limit=limit)
    return wallets


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Get wallet by ID."""
    service = WalletService(db)
    wallet = await service.get_wallet_by_id(wallet_id)

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet with ID {wallet_id} not found",
        )

    return wallet


@router.get("/address/{address}", response_model=WalletResponse)
async def get_wallet_by_address(
    address: str,
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Get wallet by Ethereum address."""
    if not is_valid_address(address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Ethereum address: {address}",
        )

    service = WalletService(db)
    wallet = await service.get_wallet_by_address(address)

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet with address {address} not found",
        )

    return wallet


@router.get("/user/{user_id}", response_model=WalletResponse)
async def get_wallet_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Get wallet by user ID."""
    service = WalletService(db)
    wallet = await service.get_wallet_by_user_id(user_id)

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet for user_id {user_id} not found",
        )

    return wallet


@router.get("/twitter/{twitter_handle}", response_model=WalletResponse)
async def get_wallet_by_twitter_handle(
    twitter_handle: str,
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Get wallet by Twitter handle."""
    service = WalletService(db)
    wallet = await service.get_wallet_by_twitter_handle(twitter_handle)

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet for twitter_handle {twitter_handle} not found",
        )

    return wallet


@router.post("/{wallet_id}/export", response_model=WalletExport)
async def export_wallet(
    wallet_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
) -> WalletExport:
    """Export wallet with decrypted private key.

    WARNING: This endpoint returns the private key in plain text.
    Requires admin authentication. Use with extreme caution.
    """
    service = WalletService(db)
    wallet_data = await service.export_wallet(wallet_id)

    if not wallet_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet with ID {wallet_id} not found",
        )

    return WalletExport(**wallet_data)


@router.delete("/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wallet(
    wallet_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a wallet."""
    service = WalletService(db)
    deleted = await service.delete_wallet(wallet_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet with ID {wallet_id} not found",
        )


# ============ PRIVY WALLET ENDPOINTS ============

from src.models import UserType
from src.services.privy import get_privy_service
import logging

logger = logging.getLogger(__name__)


@router.post("/privy/{entity_type}/{entity_id}", response_model=WalletResponse)
async def get_or_create_privy_wallet(
    entity_type: UserType,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_agent_key),
) -> WalletResponse:
    """
    Get or create a Privy embedded wallet for an agent or user.

    Args:
        entity_type: "agent" or "human"
        entity_id: The agent ID or user ID

    Returns:
        Wallet details including address
    """
    try:
        privy_service = get_privy_service()

        wallet = await privy_service.get_or_create_wallet(
            db=db, entity_id=entity_id, user_type=entity_type, chain_type="ethereum"
        )

        return wallet

    except Exception as e:
        logger.error(f"Error creating Privy wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create wallet: {str(e)}",
        )


@router.get("/entity/{entity_type}/{entity_id}", response_model=WalletResponse)
async def get_wallet_by_entity(
    entity_type: UserType,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Get wallet by entity ID and type."""
    from src.models import Wallet
    from sqlalchemy import select

    try:
        result = await db.execute(
            select(Wallet).where(Wallet.entity_id == entity_id, Wallet.user_type == entity_type)
        )
        wallet = result.scalar_one_or_none()

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No wallet found for this entity"
            )

        return wallet

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve wallet"
        )
