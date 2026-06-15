"""Stats API endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Agent, Campaign, Donation, Wallet


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_platform_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """Get platform-wide statistics."""
    # Total campaigns
    campaigns_result = await db.execute(select(func.count(Campaign.id)))
    total_campaigns = campaigns_result.scalar() or 0

    # Active campaigns
    active_result = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.status == "active")
    )
    active_campaigns = active_result.scalar() or 0

    # Total raised
    raised_result = await db.execute(select(func.sum(Campaign.raised)))
    total_raised = raised_result.scalar() or 0.0

    # Total agents
    agents_result = await db.execute(
        select(func.count(Agent.id)).where(Agent.is_active == True)
    )
    total_agents = agents_result.scalar() or 0

    # Total unique donors (distinct donor addresses)
    donors_result = await db.execute(
        select(func.count(func.distinct(Donation.donor_address)))
    )
    total_donors = donors_result.scalar() or 0

    # Total donations count
    donations_result = await db.execute(select(func.count(Donation.id)))
    total_donations = donations_result.scalar() or 0

    # Average donation amount
    avg_donation_result = await db.execute(select(func.avg(Donation.amount)))
    avg_donation = avg_donation_result.scalar() or 0.0

    # Top campaign (highest raised)
    top_campaign_result = await db.execute(
        select(Campaign).order_by(Campaign.raised.desc()).limit(1)
    )
    top_campaign = top_campaign_result.scalar_one_or_none()

    return {
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "total_raised": round(float(total_raised), 2),
        "total_agents": total_agents,
        "total_donors": total_donors,
        "total_donations": total_donations,
        "average_donation": round(float(avg_donation), 2),
        "top_campaign": {
            "id": str(top_campaign.id),
            "title": top_campaign.title,
            "raised": top_campaign.raised,
        } if top_campaign else None,
    }
