"""
Withdrawal API - Time-delayed withdrawal requests with limits
"""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Campaign, WithdrawalRequest
from src.schemas import WithdrawalRequestCreate, WithdrawalRequestResponse

router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])

# Withdrawal constraints
MAX_SINGLE_WITHDRAWAL = 100_000.0  # Max per request
MAX_DAILY_WITHDRAWAL = 250_000.0   # Max per 24h per agent
DEFAULT_DELAY_HOURS = 24           # Time lock before processing
LARGE_AMOUNT_DELAY_HOURS = 72      # Extra delay for large withdrawals
LARGE_AMOUNT_THRESHOLD = 50_000.0  # What counts as "large"


@router.post("", response_model=WithdrawalRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_withdrawal(
    data: WithdrawalRequestCreate,
    db: AsyncSession = Depends(get_db),
) -> WithdrawalRequestResponse:
    """
    Request a withdrawal with time-delay.
    Large withdrawals (>50k) get a 72h delay instead of 24h.
    """
    # Validate campaign exists and has funds
    campaign = await db.get(Campaign, data.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    available = campaign.raised - campaign.withdrawn
    if data.amount > available:
        raise HTTPException(
            status_code=400,
            detail=f"Withdrawal amount ({data.amount}) exceeds available funds ({available:.2f})",
        )

    # Single withdrawal cap
    if data.amount > MAX_SINGLE_WITHDRAWAL:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum single withdrawal is {MAX_SINGLE_WITHDRAWAL:,.0f}",
        )

    # Check 24h rolling limit
    since = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(func.coalesce(func.sum(WithdrawalRequest.amount), 0.0)).where(
            WithdrawalRequest.agent_id == campaign.agent_id,
            WithdrawalRequest.status.in_(["pending", "approved", "completed"]),
            WithdrawalRequest.created_at >= since,
        )
    )
    daily_total = result.scalar() or 0.0

    if daily_total + data.amount > MAX_DAILY_WITHDRAWAL:
        remaining = MAX_DAILY_WITHDRAWAL - daily_total
        raise HTTPException(
            status_code=400,
            detail=f"24h withdrawal limit exceeded. Remaining: {remaining:,.0f}",
        )

    # Determine delay
    delay = LARGE_AMOUNT_DELAY_HOURS if data.amount >= LARGE_AMOUNT_THRESHOLD else DEFAULT_DELAY_HOURS

    withdrawal = WithdrawalRequest(
        agent_id=campaign.agent_id,
        campaign_id=data.campaign_id,
        amount=data.amount,
        recipient_address=data.recipient_address,
        reason=data.reason,
        delay_hours=delay,
        scheduled_at=datetime.utcnow() + timedelta(hours=delay),
        status="pending",
    )
    campaign.withdrawn += data.amount
    db.add(withdrawal)
    await db.commit()
    await db.refresh(withdrawal)

    return WithdrawalRequestResponse.model_validate(withdrawal)


@router.get("/agent/{agent_id}", response_model=list[WithdrawalRequestResponse])
async def list_agent_withdrawals(
    agent_id: UUID,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[WithdrawalRequestResponse]:
    """List withdrawal requests for an agent."""
    query = select(WithdrawalRequest).where(
        WithdrawalRequest.agent_id == agent_id
    ).order_by(WithdrawalRequest.created_at.desc())

    if status_filter:
        query = query.where(WithdrawalRequest.status == status_filter)

    result = await db.execute(query)
    return [WithdrawalRequestResponse.model_validate(w) for w in result.scalars().all()]


@router.get("/{withdrawal_id}", response_model=WithdrawalRequestResponse)
async def get_withdrawal(
    withdrawal_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WithdrawalRequestResponse:
    """Get a specific withdrawal request."""
    withdrawal = await db.get(WithdrawalRequest, withdrawal_id)
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    return WithdrawalRequestResponse.model_validate(withdrawal)
