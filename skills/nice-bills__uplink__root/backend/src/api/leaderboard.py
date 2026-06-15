"""
Donation leaderboard API endpoints.
Shows top donors by total amount donated.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.database import get_db
from src.models import Donation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/donors")
async def get_top_donors(
    limit: int = Query(50, ge=1, le=1000, description="Number of top donors to return"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get top donors ranked by total donation amount.

    Returns a list of donors with their total donated amount,
    number of donations, and ranking.
    """
    try:
        # Query to aggregate donations by donor address
        query = (
            select(
                Donation.donor_address,
                func.sum(Donation.amount).label("total_donated"),
                func.count(Donation.id).label("donation_count"),
                func.max(Donation.created_at).label("last_donation_at"),
            )
            .group_by(Donation.donor_address)
            .order_by(desc("total_donated"))
            .limit(limit)
        )

        result = await db.execute(query)
        rows = result.all()

        # Format response
        donors = []
        for rank, row in enumerate(rows, 1):
            donors.append(
                {
                    "rank": rank,
                    "donor_address": row.donor_address,
                    "total_donated": float(row.total_donated),
                    "donation_count": row.donation_count,
                    "last_donation_at": row.last_donation_at.isoformat()
                    if row.last_donation_at
                    else None,
                }
            )

        return {
            "donors": donors,
            "total": len(donors),
            "generated_at": "2026-02-14T00:00:00Z",  # Will be updated dynamically
        }

    except Exception as e:
        logger.error(f"Error getting top donors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve donor leaderboard",
        )


@router.get("/donors/{donor_address}")
async def get_donor_details(
    donor_address: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get detailed donation history for a specific donor.

    Returns total donated, donation count, and list of individual donations.
    """
    try:
        # Get donor summary
        summary_query = select(
            func.sum(Donation.amount).label("total_donated"),
            func.count(Donation.id).label("donation_count"),
            func.min(Donation.created_at).label("first_donation_at"),
            func.max(Donation.created_at).label("last_donation_at"),
        ).where(Donation.donor_address == donor_address)

        summary_result = await db.execute(summary_query)
        summary = summary_result.one()

        if not summary or summary.total_donated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")

        # Get individual donations
        donations_query = (
            select(Donation)
            .where(Donation.donor_address == donor_address)
            .order_by(desc(Donation.created_at))
        )

        donations_result = await db.execute(donations_query)
        donations = donations_result.scalars().all()

        return {
            "donor_address": donor_address,
            "total_donated": float(summary.total_donated),
            "donation_count": summary.donation_count,
            "first_donation_at": summary.first_donation_at.isoformat()
            if summary.first_donation_at
            else None,
            "last_donation_at": summary.last_donation_at.isoformat()
            if summary.last_donation_at
            else None,
            "donations": [
                {
                    "id": str(d.id),
                    "campaign_id": str(d.campaign_id),
                    "amount": float(d.amount),
                    "token_type": d.token_type,
                    "tx_hash": d.tx_hash,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in donations
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting donor details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve donor details",
        )


@router.get("/campaigns/top")
async def get_top_campaigns(
    limit: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get top campaigns by amount raised.

    This complements the reputation-based leaderboard.
    """
    from src.models import Campaign

    try:
        query = (
            select(Campaign)
            .where(Campaign.status == "active")
            .order_by(desc(Campaign.raised))
            .limit(limit)
        )

        result = await db.execute(query)
        campaigns = result.scalars().all()

        return {
            "campaigns": [
                {
                    "id": str(c.id),
                    "title": c.title,
                    "raised": float(c.raised),
                    "goal": float(c.goal) if c.goal else None,
                    "progress_percentage": round((c.raised / c.goal * 100), 2) if c.goal else None,
                    "status": c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in campaigns
            ],
            "total": len(campaigns),
        }

    except Exception as e:
        logger.error(f"Error getting top campaigns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top campaigns",
        )
