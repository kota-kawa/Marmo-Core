import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Agent, Campaign
from src.schemas import AgentCreate, AgentResponse, CampaignResponse
from src.auth import verify_agent_key


def sanitize_search_input(search: str) -> str:
    """Sanitize search input to prevent SQL injection and XSS."""
    # Remove any SQL special characters and limit length
    # Allow only alphanumeric, spaces, and common punctuation
    sanitized = re.sub(r"[^\w\s\-\.@]", "", search)
    return sanitized[:100]  # Limit to 100 characters


router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name or address"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
) -> list[Agent]:
    """List all agents with optional filtering and search."""
    query = select(Agent)

    # Apply filters
    if is_active is not None:
        query = query.where(Agent.is_active == is_active)

    # Apply search with sanitization
    if search:
        sanitized_search = sanitize_search_input(search)
        if sanitized_search:
            search_pattern = f"%{sanitized_search}%"
            query = query.where(
                or_(
                    Agent.name.ilike(search_pattern),
                    Agent.address.ilike(search_pattern),
                    Agent.description.ilike(search_pattern),
                )
            )

    # Order by reputation score descending
    query = query.order_by(Agent.reputation_score.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_agent_key),
) -> Agent:
    """Create a new agent."""
    # Check if agent with this address already exists
    result = await db.execute(select(Agent).where(Agent.address == agent_data.address))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with address {agent_data.address} already exists",
        )

    agent = Agent(
        address=agent_data.address,
        name=agent_data.name,
        description=agent_data.description,
        reputation_score=agent_data.reputation_score,
        is_active=agent_data.is_active,
        moltbook_api_key=agent_data.moltbook_api_key,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """Get agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )

    return agent


@router.get("/address/{address}", response_model=AgentResponse)
async def get_agent_by_address(
    address: str,
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """Get agent by wallet address."""
    result = await db.execute(select(Agent).where(Agent.address == address))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with address {address} not found",
        )

    return agent


@router.get("/{agent_id}/campaigns", response_model=list[CampaignResponse])
async def get_agent_campaigns(
    agent_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(
        None, description="Filter by status (active, completed, cancelled)"
    ),
    db: AsyncSession = Depends(get_db),
) -> list[Campaign]:
    """Get all campaigns for a specific agent."""
    # Verify agent exists
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )

    # Query campaigns
    query = select(Campaign).where(Campaign.agent_id == agent_id)

    if status_filter:
        query = query.where(Campaign.status == status_filter)

    query = query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())
