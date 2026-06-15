"""
Campaign Updates API - Milestones & progress posts
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Campaign, CampaignUpdate
from src.schemas import CampaignUpdateCreate, CampaignUpdateResponse
from src.auth import verify_agent_key

router = APIRouter(prefix="/campaigns", tags=["campaign-updates"])


@router.get("/{campaign_id}/updates", response_model=list[CampaignUpdateResponse])
async def list_updates(
    campaign_id: UUID,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[CampaignUpdateResponse]:
    """List all updates for a campaign."""
    result = await db.execute(
        select(CampaignUpdate)
        .where(CampaignUpdate.campaign_id == campaign_id)
        .order_by(CampaignUpdate.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [CampaignUpdateResponse.model_validate(u) for u in result.scalars().all()]


@router.post(
    "/{campaign_id}/updates",
    response_model=CampaignUpdateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_update(
    campaign_id: UUID,
    data: CampaignUpdateCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_agent_key),
) -> CampaignUpdateResponse:
    """Post a new update or milestone for a campaign."""
    # Verify campaign exists
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update = CampaignUpdate(
        campaign_id=campaign_id,
        title=data.title,
        content=data.content,
        is_milestone=data.is_milestone,
        milestone_percentage=data.milestone_percentage,
    )
    db.add(update)
    await db.commit()
    await db.refresh(update)

    return CampaignUpdateResponse.model_validate(update)
