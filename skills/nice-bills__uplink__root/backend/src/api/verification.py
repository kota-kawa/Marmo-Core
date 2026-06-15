"""
Campaign Verification API - Request and process verification
"""

import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Campaign
from src.schemas import VerificationRequest, VerificationResponse
from src.config import get_settings

router = APIRouter(prefix="/verification", tags=["verification"])


def _verify_admin_key(provided_key: str) -> None:
    """Verify admin key using constant-time comparison to prevent timing attacks."""
    settings = get_settings()
    if not hmac.compare_digest(provided_key, settings.ADMIN_KEY):
        raise HTTPException(status_code=403, detail="Invalid admin key")


@router.post("/request", response_model=VerificationResponse)
async def request_verification(
    data: VerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> VerificationResponse:
    """Submit a campaign for verification review."""
    campaign = await db.get(Campaign, data.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.verification_status == "verified":
        return VerificationResponse(
            campaign_id=campaign.id,
            is_verified=True,
            verification_status="verified",
            message="Campaign is already verified",
        )

    campaign.verification_status = "pending"
    await db.commit()

    return VerificationResponse(
        campaign_id=campaign.id,
        is_verified=False,
        verification_status="pending",
        message="Verification request submitted. Review typically takes 24-48 hours.",
    )


@router.post("/approve/{campaign_id}", response_model=VerificationResponse)
async def approve_verification(
    campaign_id: UUID,
    x_admin_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> VerificationResponse:
    """Admin: Approve campaign verification."""
    _verify_admin_key(x_admin_key)

    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.is_verified = True
    campaign.verification_status = "verified"
    await db.commit()

    return VerificationResponse(
        campaign_id=campaign.id,
        is_verified=True,
        verification_status="verified",
        message="Campaign verified successfully",
    )


@router.post("/reject/{campaign_id}", response_model=VerificationResponse)
async def reject_verification(
    campaign_id: UUID,
    x_admin_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> VerificationResponse:
    """Admin: Reject campaign verification."""
    _verify_admin_key(x_admin_key)

    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.is_verified = False
    campaign.verification_status = "rejected"
    await db.commit()

    return VerificationResponse(
        campaign_id=campaign.id,
        is_verified=False,
        verification_status="rejected",
        message="Campaign verification rejected",
    )
