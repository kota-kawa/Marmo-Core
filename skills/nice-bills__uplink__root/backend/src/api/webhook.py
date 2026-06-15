"""
Webhook API - Handle campaign creation from OpenClaw/Nanobot agents.

This endpoint receives requests from your AI agent when it detects
social media mentions (Twitter/Moltbook) that should create campaigns.
"""

import hmac
import hashlib
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.database import get_db
from src.models import Agent, Campaign, Wallet
from src.config import get_settings

router = APIRouter(prefix="/webhook", tags=["Webhook"])
settings = get_settings()

# Rate limiter for webhook - 10 requests per minute
limiter = Limiter(key_func=get_remote_address)


class SourceInfo(BaseModel):
    """Source information from the social post."""
    platform: str = Field(..., description="twitter or moltbook")
    author_handle: str = Field(..., description="@username")
    author_name: str | None = Field(None, description="Display name")
    author_avatar: str | None = Field(None, description="Avatar URL")
    content: str = Field(..., description="Post content")
    url: str | None = Field(None, description="URL to original post")
    timestamp: datetime | None = Field(None, description="Post timestamp")


class CreateCampaignWebhookRequest(BaseModel):
    """Request body for campaign creation webhook."""
    source: SourceInfo
    goal_amount: float | None = Field(None, description="Funding goal in USD")
    title: str = Field(..., description="Campaign title")
    description: str | None = Field(None, description="Campaign description")
    agent_address: str | None = Field(None, description="Agent wallet address (optional)")


class CreateCampaignWebhookResponse(BaseModel):
    """Response for successful campaign creation."""
    success: bool
    campaign_id: str
    message: str
    creator_wallet: str | None = None
    is_new_wallet: bool = False


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """Verify HMAC signature of webhook payload."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post(
    "/create-campaign",
    response_model=CreateCampaignWebhookResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_campaign_webhook(
    request: Request,
    data: CreateCampaignWebhookRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_webhook_signature: Annotated[str | None, Header()] = None,
) -> CreateCampaignWebhookResponse:
    """
    Create a campaign from an OpenClaw/Nanobot agent webhook.
    
    This endpoint is called by your AI agent when it detects a social
    media mention (Twitter/Moltbook) that should create a campaign.
    
    The agent parses the post content to extract:
    - Goal amount (if mentioned)
    - Campaign title/description
    - Creator information
    
    Security: Requires X-Webhook-Signature header with HMAC signature.
    """
    # Verify signature if webhook secret is configured
    webhook_secret = getattr(settings, "WEBHOOK_SECRET", None)
    if webhook_secret:
        if not x_webhook_signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature"
            )
        
        body = await request.body()
        if not verify_webhook_signature(body, x_webhook_signature, webhook_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    
    # Find or create agent for the platform
    # For now, use a default agent. Later: create per-creator agents
    from sqlalchemy import select
    
    # Try to find agent by address if provided
    agent = None
    if data.agent_address:
        result = await db.execute(
            select(Agent).where(Agent.address == data.agent_address)
        )
        agent = result.scalar_one_or_none()
    
    # If no agent found, use first active agent (platform agent)
    if not agent:
        result = await db.execute(
            select(Agent).where(Agent.is_active == True).limit(1)
        )
        agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active agent found to create campaign"
        )
    
    # Check if creator already has a wallet
    creator_wallet = None
    is_new_wallet = False
    
    result = await db.execute(
        select(Wallet).where(
            Wallet.twitter_handle == data.source.author_handle.replace("@", "")
        )
    )
    creator_wallet = result.scalar_one_or_none()
    
    # TODO: If no wallet, create via Privy in a separate service
    # For now, we just note if one exists
    
    # Create the campaign
    campaign = Campaign(
        agent_id=agent.id,
        title=data.title,
        description=data.description,
        goal=data.goal_amount,
        status="active",
        # Source fields
        source_platform=data.source.platform,
        source_author_handle=data.source.author_handle.replace("@", ""),
        source_author_name=data.source.author_name,
        source_author_avatar=data.source.author_avatar,
        source_content=data.source.content,
        source_url=data.source.url,
        source_timestamp=data.source.timestamp,
    )
    
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    
    return CreateCampaignWebhookResponse(
        success=True,
        campaign_id=str(campaign.id),
        message=f"Campaign '{data.title}' created successfully",
        creator_wallet=creator_wallet.address if creator_wallet else None,
        is_new_wallet=is_new_wallet,
    )
