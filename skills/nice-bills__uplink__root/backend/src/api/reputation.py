"""Reputation API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import UserType
from src.schemas import (
    AgentReputationResponse,
    BlacklistRequest,
    HumanReputationResponse,
    LeaderboardResponse,
    ReputationHistoryResponse,
    ReputationUpdateRequest,
)
from src.services.reputation import ReputationService

router = APIRouter(prefix="/reputation", tags=["reputation"])


def get_reputation_service(db: AsyncSession = Depends(get_db)) -> ReputationService:
    """Dependency to get reputation service."""
    return ReputationService(db)


@router.get("/agent/{agent_id}", response_model=AgentReputationResponse)
async def get_agent_reputation(
    agent_id: UUID,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Get an agent's reputation details."""
    try:
        return await service.get_agent_reputation(agent_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/human/{wallet_id}", response_model=HumanReputationResponse)
async def get_human_reputation(
    wallet_id: UUID,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Get a human's reputation details."""
    try:
        return await service.get_human_reputation(wallet_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/history", response_model=list[ReputationHistoryResponse])
async def get_reputation_history(
    user_type: UserType | None = Query(None, description="Filter by user type"),
    agent_id: UUID | None = Query(None, description="Filter by agent ID"),
    user_id: UUID | None = Query(None, description="Filter by user/wallet ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: ReputationService = Depends(get_reputation_service),
) -> list[ReputationHistoryResponse]:
    """Get reputation history with optional filters."""
    return await service.get_reputation_history(
        user_type=user_type,
        agent_id=agent_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.get("/leaderboard/{user_type}", response_model=LeaderboardResponse)
async def get_leaderboard(
    user_type: UserType,
    limit: int = Query(100, ge=1, le=1000),
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Get reputation leaderboard."""
    entries = await service.get_leaderboard(user_type=user_type, limit=limit)
    return {
        "user_type": user_type.value,
        "entries": entries,
        "total": len(entries),
    }


@router.get("/check-blacklist/{user_type}/{entity_id}")
async def check_blacklist(
    user_type: UserType,
    entity_id: UUID,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Check if an entity is blacklisted."""
    is_blacklisted = await service.is_blacklisted(user_type, entity_id)
    return {
        "user_type": user_type.value,
        "entity_id": entity_id,
        "is_blacklisted": is_blacklisted,
    }


@router.post("/update/agent/{agent_id}", response_model=AgentReputationResponse)
async def update_agent_reputation(
    agent_id: UUID,
    request: ReputationUpdateRequest,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Update an agent's reputation score."""
    try:
        from src.models import ReputationAction

        await service.update_agent_score(
            agent_id=agent_id,
            action=request.action,
            metadata=request.metadata,
            amount=request.amount,
        )
        return await service.get_agent_reputation(agent_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/update/human/{wallet_id}", response_model=HumanReputationResponse)
async def update_human_reputation(
    wallet_id: UUID,
    request: ReputationUpdateRequest,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Update a human's reputation score."""
    try:
        from src.models import ReputationAction

        await service.update_human_score(
            wallet_id=wallet_id,
            action=request.action,
            metadata=request.metadata,
        )
        return await service.get_human_reputation(wallet_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/blacklist/{user_type}/{entity_id}")
async def blacklist_entity(
    user_type: UserType,
    entity_id: UUID,
    request: BlacklistRequest,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Blacklist an entity."""
    try:
        if user_type == UserType.AGENT:
            return await service.blacklist_entity(user_type, entity_id, request.reason)
        else:
            return await service.blacklist_entity(user_type, entity_id, request.reason)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/unblacklist/{user_type}/{entity_id}")
async def unblacklist_entity(
    user_type: UserType,
    entity_id: UUID,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Remove an entity from the blacklist (admin only)."""
    try:
        if user_type == UserType.AGENT:
            return await service.unblacklist_entity(user_type, entity_id)
        else:
            return await service.unblacklist_entity(user_type, entity_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/report-fraud/{user_type}/{entity_id}")
async def report_fraud(
    user_type: UserType,
    entity_id: UUID,
    request: BlacklistRequest,
    reporter_address: str | None = Query(None),
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Report fraud and blacklist entity."""
    try:
        return await service.report_fraud(
            user_type=user_type,
            entity_id=entity_id,
            reason=request.reason,
            reporter_address=reporter_address,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/events/funds-raised/{agent_id}", response_model=AgentReputationResponse)
async def record_funds_raised(
    agent_id: UUID,
    amount: float,
    campaign_id: UUID | None = None,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Record funds raised event for agent."""
    try:
        await service.record_funds_raised(agent_id, amount, campaign_id)
        return await service.get_agent_reputation(agent_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/events/onchain-execution/{agent_id}", response_model=AgentReputationResponse)
async def record_onchain_execution(
    agent_id: UUID,
    tx_hash: str,
    description: str | None = None,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Record on-chain execution event for agent."""
    try:
        await service.record_onchain_execution(agent_id, tx_hash, description)
        return await service.get_agent_reputation(agent_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/events/campaign-delivered/{agent_id}", response_model=AgentReputationResponse)
async def record_campaign_delivered(
    agent_id: UUID,
    campaign_id: UUID,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Record campaign delivered event for agent."""
    try:
        await service.record_campaign_delivered(agent_id, campaign_id)
        return await service.get_agent_reputation(agent_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/events/campaign-completed/{wallet_id}", response_model=HumanReputationResponse)
async def record_campaign_completed(
    wallet_id: UUID,
    campaign_id: UUID,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Record campaign completed event for human."""
    try:
        await service.record_campaign_completed(wallet_id, campaign_id)
        return await service.get_human_reputation(wallet_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/events/positive-review/{wallet_id}", response_model=HumanReputationResponse)
async def record_positive_review(
    wallet_id: UUID,
    reviewer_address: str,
    review_text: str | None = None,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Record positive review event for human."""
    try:
        await service.record_positive_review(wallet_id, reviewer_address, review_text)
        return await service.get_human_reputation(wallet_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/events/default/{agent_id}", response_model=AgentReputationResponse)
async def record_default(
    agent_id: UUID,
    reason: str,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Record default event for agent."""
    try:
        await service.record_default(agent_id, reason)
        return await service.get_agent_reputation(agent_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/events/failed-delivery/{wallet_id}", response_model=HumanReputationResponse)
async def record_failed_delivery(
    wallet_id: UUID,
    campaign_id: UUID,
    reason: str,
    service: ReputationService = Depends(get_reputation_service),
) -> dict[str, Any]:
    """Record failed delivery event for human."""
    try:
        await service.record_failed_delivery(wallet_id, campaign_id, reason)
        return await service.get_human_reputation(wallet_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
