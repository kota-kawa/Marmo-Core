from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging

from src.database import get_db
from src.config import validate_wallet_address, validate_tx_hash
from src.models import Agent, Campaign, Donation, UserType
from src.schemas import CampaignCreate, CampaignResponse, DonationCreate, DonationResponse
from src.auth import verify_agent_key, verify_admin_key
from src.services.privy import get_privy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    is_genesis: bool = Depends(verify_admin_key),
) -> Campaign:
    """Create a new fundraising campaign.

    Rate limiting: Users can only have ONE active campaign at a time.

    For non-Genesis agents:
    - Must be ERC-8004 registered
    - Must not have existing active campaign
    - Can use Privy wallet or provide own wallet
    """
    try:
        # Verify agent exists
        result = await db.execute(select(Agent).where(Agent.id == campaign_data.agent_id))
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {campaign_data.agent_id} not found",
            )

        # Check if Genesis agent or regular agent
        if not is_genesis:
            # Non-Genesis agents must be ERC-8004 verified
            if not agent.is_erc8004_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Agent must be ERC-8004 registered to create campaigns. "
                    "Register your agent first.",
                )

        # RATE LIMITING: Check if agent already has an active campaign
        # Check by agent_id for all campaigns
        existing_agent_campaign = await db.execute(
            select(Campaign).where(
                Campaign.agent_id == str(campaign_data.agent_id), Campaign.status == "active"
            )
        )
        if existing_agent_campaign.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active campaign. Complete it before creating a new one.",
            )

        # Also check by Twitter handle for Twitter-based campaigns
        if campaign_data.source_message and campaign_data.source_message.author_handle:
            existing_campaign = await db.execute(
                select(Campaign).where(
                    Campaign.source_author_handle == campaign_data.source_message.author_handle,
                    Campaign.status == "active",
                )
            )
            if existing_campaign.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You already have an active campaign. Complete it before creating a new one.",
                )

        # Determine receiving wallet address
        receiving_address = None
        if campaign_data.use_privy_wallet:
            # Use or create Privy wallet for this agent
            privy_service = get_privy_service()
            privy_wallet = await privy_service.get_or_create_wallet(
                db=db, entity_id=str(campaign_data.agent_id), user_type=UserType.AGENT
            )
            receiving_address = privy_wallet.address
        elif campaign_data.wallet_address:
            # Use provided wallet address
            if not validate_wallet_address(campaign_data.wallet_address):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid wallet address format",
                )
            receiving_address = campaign_data.wallet_address
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide wallet_address or set use_privy_wallet=true",
            )

        # Extract source message fields if provided
        source_fields = {}
        if campaign_data.source_message:
            source_fields = {
                "source_platform": campaign_data.source_message.platform,
                "source_author_handle": campaign_data.source_message.author_handle,
                "source_author_name": campaign_data.source_message.author_name,
                "source_author_avatar": campaign_data.source_message.author_avatar,
                "source_content": campaign_data.source_message.content,
                "source_url": campaign_data.source_message.url,
                "source_timestamp": campaign_data.source_message.timestamp,
            }

        campaign = Campaign(
            agent_id=campaign_data.agent_id,
            title=campaign_data.title,
            description=campaign_data.description,
            goal=campaign_data.goal,
            deadline=campaign_data.deadline,
            metadata_uri=campaign_data.metadata_uri,
            treasury_address=receiving_address,
            **source_fields,
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)

        logger.info(
            f"Created campaign {campaign.id} for agent {campaign_data.agent_id} with treasury {receiving_address}"
        )
        return campaign

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create campaign: {str(e)}",
        )


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status_filter: str = Query(None, description="Filter by status (active, completed, cancelled)"),
    db: AsyncSession = Depends(get_db),
) -> List[Campaign]:
    """List all campaigns with optional filtering."""
    try:
        # Build query with eager loading for relationships
        query = (
            select(Campaign)
            .options(selectinload(Campaign.donations))
            .order_by(Campaign.created_at.desc())
        )

        # Apply status filter if provided
        if status_filter:
            query = query.where(Campaign.status == status_filter)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        campaigns = result.scalars().all()
        return list(campaigns)

    except Exception as e:
        logger.error(f"Error listing campaigns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve campaigns"
        )


@router.get("/stats", response_model=dict)
async def get_campaign_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get aggregate statistics for all campaigns."""
    try:
        # Total campaigns
        total_result = await db.execute(select(func.count(Campaign.id)))
        total = total_result.scalar()

        # Active campaigns
        active_result = await db.execute(
            select(func.count(Campaign.id)).where(Campaign.status == "active")
        )
        active = active_result.scalar()

        # Total raised
        raised_result = await db.execute(select(func.sum(Campaign.raised)))
        total_raised = raised_result.scalar() or 0.0

        return {
            "total_campaigns": total,
            "active_campaigns": active,
            "total_raised": float(total_raised),
        }

    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve campaign statistics",
        )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    """Get a specific campaign by ID."""
    try:
        result = await db.execute(
            select(Campaign)
            .options(selectinload(Campaign.donations))
            .where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found",
            )

        return campaign

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign {campaign_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve campaign"
        )


@router.post(
    "/{campaign_id}/donate", response_model=DonationResponse, status_code=status.HTTP_201_CREATED
)
async def donate_to_campaign(
    campaign_id: UUID,
    donation_data: DonationCreate,
    db: AsyncSession = Depends(get_db),
) -> Donation:
    """Create a donation for a campaign."""
    try:
        # Verify campaign exists
        result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = result.scalar_one_or_none()

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found",
            )

        # Validate wallet address format (0x + 40 hex chars)
        if not validate_wallet_address(donation_data.donor_address):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid donor wallet address format (expected 0x + 40 hex characters)",
            )

        # Validate tx_hash format (0x + 64 hex chars)
        if donation_data.tx_hash and not validate_tx_hash(donation_data.tx_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction hash format (expected 0x + 64 hex characters)",
            )

        # Validate amount
        if donation_data.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Donation amount must be greater than 0",
            )

        # Create donation
        donation = Donation(
            campaign_id=campaign_id,
            donor_address=donation_data.donor_address,
            amount=donation_data.amount,
            token_type=donation_data.token_type,
            tx_hash=donation_data.tx_hash,
        )
        db.add(donation)

        # Update campaign raised amount
        campaign.raised += donation_data.amount

        await db.commit()
        await db.refresh(donation)

        logger.info(
            f"Created donation {donation.id} for campaign {campaign_id}: "
            f"{donation_data.amount} {donation_data.token_type}"
        )

        return donation

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error creating donation: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process donation"
        )


@router.get("/{campaign_id}/treasury")
async def get_campaign_treasury(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get treasury address for a campaign."""
    try:
        result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = result.scalar_one_or_none()

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found",
            )

        if not campaign.treasury_address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Treasury not found for this campaign",
            )

        return {
            "treasuryAddress": campaign.treasury_address,
            "campaignId": str(campaign_id),
            "status": campaign.status,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting treasury for campaign {campaign_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve treasury address",
        )
