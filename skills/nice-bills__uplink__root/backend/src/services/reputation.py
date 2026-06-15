"""Reputation service for tracking agent and human reputation scores."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Agent, ReputationAction, ReputationHistory, UserType, Wallet


# Scoring logic constants
AGENT_POINTS = {
    ReputationAction.FUNDS_RAISED: 10,  # per $1K raised
    ReputationAction.ONCHAIN_EXECUTION: 25,
    ReputationAction.CAMPAIGN_DELIVERED: 50,
    ReputationAction.DEFAULT: -50,
    ReputationAction.FRAUD: -1000,
}

HUMAN_POINTS = {
    ReputationAction.CAMPAIGN_COMPLETED: 25,
    ReputationAction.POSITIVE_REVIEW: 10,
    ReputationAction.FAILED_DELIVERY: -50,
    ReputationAction.FRAUD: -1000,
}

FRAUD_THRESHOLD = -500


class ReputationService:
    """Service for managing reputation scores."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _record_history(
        self,
        user_type: UserType,
        action: ReputationAction,
        points: int,
        previous_score: int,
        new_score: int,
        agent_id: UUID | None = None,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReputationHistory:
        """Record a reputation change in history."""
        history = ReputationHistory(
            user_type=user_type.value,
            agent_id=agent_id,
            user_id=user_id,
            action=action.value,
            points=points,
            previous_score=previous_score,
            new_score=new_score,
            metadata=metadata or {},
        )
        self.db.add(history)
        await self.db.commit()
        return history

    async def update_agent_score(
        self,
        agent_id: UUID,
        action: ReputationAction,
        metadata: dict[str, Any] | None = None,
        amount: float | None = None,
    ) -> Agent:
        """Update an agent's reputation score based on action."""
        result = await self.db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent with ID {agent_id} not found")

        if agent.is_blacklisted and action != ReputationAction.FRAUD:
            raise ValueError(f"Agent {agent_id} is blacklisted")

        # Calculate points
        points = AGENT_POINTS[action]

        # Special handling for funds raised (per $1K)
        if action == ReputationAction.FUNDS_RAISED and amount:
            points = int(points * (amount / 1000))

        previous_score = agent.reputation_score
        agent.reputation_score += points

        # Check for fraud/blacklist
        if action == ReputationAction.FRAUD or agent.reputation_score <= FRAUD_THRESHOLD:
            agent.is_blacklisted = True
            agent.is_active = False
            if action == ReputationAction.FRAUD:
                agent.blacklist_reason = (
                    metadata.get("reason", "Fraud detected") if metadata else "Fraud detected"
                )

        await self.db.commit()
        await self.db.refresh(agent)

        # Record history
        await self._record_history(
            user_type=UserType.AGENT,
            action=action,
            points=points,
            previous_score=previous_score,
            new_score=agent.reputation_score,
            agent_id=agent_id,
            metadata=metadata,
        )

        return agent

    async def update_human_score(
        self,
        wallet_id: UUID,
        action: ReputationAction,
        metadata: dict[str, Any] | None = None,
    ) -> Wallet:
        """Update a human's reputation score based on action."""
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalar_one_or_none()

        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")

        if wallet.is_blacklisted and action != ReputationAction.FRAUD:
            raise ValueError(f"Wallet {wallet_id} is blacklisted")

        if action not in HUMAN_POINTS:
            raise ValueError(f"Action {action} not valid for humans")

        points = HUMAN_POINTS[action]
        previous_score = wallet.reputation_score
        wallet.reputation_score += points

        # Check for fraud/blacklist
        if action == ReputationAction.FRAUD or wallet.reputation_score <= FRAUD_THRESHOLD:
            wallet.is_blacklisted = True
            if action == ReputationAction.FRAUD:
                wallet.blacklist_reason = (
                    metadata.get("reason", "Fraud detected") if metadata else "Fraud detected"
                )

        await self.db.commit()
        await self.db.refresh(wallet)

        # Record history
        await self._record_history(
            user_type=UserType.HUMAN,
            action=action,
            points=points,
            previous_score=previous_score,
            new_score=wallet.reputation_score,
            user_id=wallet_id,
            metadata=metadata,
        )

        return wallet

    async def get_agent_reputation(self, agent_id: UUID) -> dict[str, Any]:
        """Get an agent's full reputation details."""
        result = await self.db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent with ID {agent_id} not found")

        return {
            "id": agent.id,
            "address": agent.address,
            "name": agent.name,
            "reputation_score": agent.reputation_score,
            "is_blacklisted": agent.is_blacklisted,
            "blacklist_reason": agent.blacklist_reason,
            "is_active": agent.is_active,
        }

    async def get_human_reputation(self, wallet_id: UUID) -> dict[str, Any]:
        """Get a human's full reputation details."""
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalar_one_or_none()

        if not wallet:
            raise ValueError(f"Wallet with ID {wallet_id} not found")

        return {
            "id": wallet.id,
            "address": wallet.address,
            "twitter_handle": wallet.twitter_handle,
            "reputation_score": wallet.reputation_score,
            "is_blacklisted": wallet.is_blacklisted,
            "blacklist_reason": wallet.blacklist_reason,
        }

    async def get_reputation_history(
        self,
        user_type: UserType | None = None,
        agent_id: UUID | None = None,
        user_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ReputationHistory]:
        """Get reputation history with optional filters."""
        query = select(ReputationHistory).order_by(desc(ReputationHistory.created_at))

        if user_type:
            query = query.where(ReputationHistory.user_type == user_type.value)
        if agent_id:
            query = query.where(ReputationHistory.agent_id == agent_id)
        if user_id:
            query = query.where(ReputationHistory.user_id == user_id)

        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_leaderboard(
        self,
        user_type: UserType,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get reputation leaderboard for agents or humans."""
        if user_type == UserType.AGENT:
            query = (
                select(Agent)
                .where(Agent.is_blacklisted == False)
                .order_by(desc(Agent.reputation_score))
                .limit(limit)
            )
            result = await self.db.execute(query)
            agents = result.scalars().all()
            return [
                {
                    "rank": i + 1,
                    "id": agent.id,
                    "address": agent.address,
                    "name": agent.name,
                    "reputation_score": agent.reputation_score,
                }
                for i, agent in enumerate(agents)
            ]
        else:
            query = (
                select(Wallet)
                .where(Wallet.is_blacklisted == False)
                .order_by(desc(Wallet.reputation_score))
                .limit(limit)
            )
            result = await self.db.execute(query)
            wallets = result.scalars().all()
            return [
                {
                    "rank": i + 1,
                    "id": wallet.id,
                    "address": wallet.address,
                    "twitter_handle": wallet.twitter_handle,
                    "reputation_score": wallet.reputation_score,
                }
                for i, wallet in enumerate(wallets)
            ]

    async def is_blacklisted(
        self,
        user_type: UserType,
        entity_id: UUID,
    ) -> bool:
        """Check if an entity is blacklisted."""
        if user_type == UserType.AGENT:
            result = await self.db.execute(select(Agent).where(Agent.id == entity_id))
            agent = result.scalar_one_or_none()
            return agent.is_blacklisted if agent else False
        else:
            result = await self.db.execute(select(Wallet).where(Wallet.id == entity_id))
            wallet = result.scalar_one_or_none()
            return wallet.is_blacklisted if wallet else False

    async def blacklist_entity(
        self,
        user_type: UserType,
        entity_id: UUID,
        reason: str,
    ) -> dict[str, Any]:
        """Manually blacklist an entity."""
        if user_type == UserType.AGENT:
            result = await self.db.execute(select(Agent).where(Agent.id == entity_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise ValueError(f"Agent with ID {entity_id} not found")

            agent.is_blacklisted = True
            agent.is_active = False
            agent.blacklist_reason = reason
            agent.reputation_score = min(agent.reputation_score, FRAUD_THRESHOLD)
            await self.db.commit()
            await self.db.refresh(agent)

            # Record in history
            await self._record_history(
                user_type=UserType.AGENT,
                action=ReputationAction.FRAUD,
                points=AGENT_POINTS[ReputationAction.FRAUD],
                previous_score=agent.reputation_score - AGENT_POINTS[ReputationAction.FRAUD],
                new_score=agent.reputation_score,
                agent_id=entity_id,
                metadata={"reason": reason, "manual": True},
            )

            return await self.get_agent_reputation(entity_id)
        else:
            result = await self.db.execute(select(Wallet).where(Wallet.id == entity_id))
            wallet = result.scalar_one_or_none()
            if not wallet:
                raise ValueError(f"Wallet with ID {entity_id} not found")

            wallet.is_blacklisted = True
            wallet.blacklist_reason = reason
            wallet.reputation_score = min(wallet.reputation_score, FRAUD_THRESHOLD)
            await self.db.commit()
            await self.db.refresh(wallet)

            # Record in history
            await self._record_history(
                user_type=UserType.HUMAN,
                action=ReputationAction.FRAUD,
                points=HUMAN_POINTS[ReputationAction.FRAUD],
                previous_score=wallet.reputation_score - HUMAN_POINTS[ReputationAction.FRAUD],
                new_score=wallet.reputation_score,
                user_id=entity_id,
                metadata={"reason": reason, "manual": True},
            )

            return await self.get_human_reputation(entity_id)

    async def unblacklist_entity(
        self,
        user_type: UserType,
        entity_id: UUID,
    ) -> dict[str, Any]:
        """Remove an entity from the blacklist (admin only)."""
        if user_type == UserType.AGENT:
            result = await self.db.execute(select(Agent).where(Agent.id == entity_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise ValueError(f"Agent with ID {entity_id} not found")

            agent.is_blacklisted = False
            agent.blacklist_reason = None
            agent.is_active = True
            await self.db.commit()
            await self.db.refresh(agent)
            return await self.get_agent_reputation(entity_id)
        else:
            result = await self.db.execute(select(Wallet).where(Wallet.id == entity_id))
            wallet = result.scalar_one_or_none()
            if not wallet:
                raise ValueError(f"Wallet with ID {entity_id} not found")

            wallet.is_blacklisted = False
            wallet.blacklist_reason = None
            await self.db.commit()
            await self.db.refresh(wallet)
            return await self.get_human_reputation(entity_id)

    async def record_funds_raised(
        self,
        agent_id: UUID,
        amount: float,
        campaign_id: UUID | None = None,
    ) -> Agent:
        """Record funds raised and update agent reputation."""
        metadata = {"amount": amount}
        if campaign_id:
            metadata["campaign_id"] = str(campaign_id)
        return await self.update_agent_score(
            agent_id=agent_id,
            action=ReputationAction.FUNDS_RAISED,
            metadata=metadata,
            amount=amount,
        )

    async def record_onchain_execution(
        self,
        agent_id: UUID,
        tx_hash: str,
        description: str | None = None,
    ) -> Agent:
        """Record successful on-chain execution."""
        metadata = {"tx_hash": tx_hash}
        if description:
            metadata["description"] = description
        return await self.update_agent_score(
            agent_id=agent_id,
            action=ReputationAction.ONCHAIN_EXECUTION,
            metadata=metadata,
        )

    async def record_campaign_delivered(
        self,
        agent_id: UUID,
        campaign_id: UUID,
    ) -> Agent:
        """Record campaign delivery by agent."""
        return await self.update_agent_score(
            agent_id=agent_id,
            action=ReputationAction.CAMPAIGN_DELIVERED,
            metadata={"campaign_id": str(campaign_id)},
        )

    async def record_campaign_completed(
        self,
        wallet_id: UUID,
        campaign_id: UUID,
    ) -> Wallet:
        """Record successful campaign completion by human."""
        return await self.update_human_score(
            wallet_id=wallet_id,
            action=ReputationAction.CAMPAIGN_COMPLETED,
            metadata={"campaign_id": str(campaign_id)},
        )

    async def record_positive_review(
        self,
        wallet_id: UUID,
        reviewer_address: str,
        review_text: str | None = None,
    ) -> Wallet:
        """Record positive review for human."""
        metadata = {"reviewer_address": reviewer_address}
        if review_text:
            metadata["review_text"] = review_text
        return await self.update_human_score(
            wallet_id=wallet_id,
            action=ReputationAction.POSITIVE_REVIEW,
            metadata=metadata,
        )

    async def record_default(
        self,
        agent_id: UUID,
        reason: str,
    ) -> Agent:
        """Record agent default."""
        return await self.update_agent_score(
            agent_id=agent_id,
            action=ReputationAction.DEFAULT,
            metadata={"reason": reason},
        )

    async def record_failed_delivery(
        self,
        wallet_id: UUID,
        campaign_id: UUID,
        reason: str,
    ) -> Wallet:
        """Record failed delivery by human."""
        return await self.update_human_score(
            wallet_id=wallet_id,
            action=ReputationAction.FAILED_DELIVERY,
            metadata={"campaign_id": str(campaign_id), "reason": reason},
        )

    async def report_fraud(
        self,
        user_type: UserType,
        entity_id: UUID,
        reason: str,
        reporter_address: str | None = None,
    ) -> dict[str, Any]:
        """Report fraud and blacklist entity."""
        metadata = {"reason": reason}
        if reporter_address:
            metadata["reporter_address"] = reporter_address

        if user_type == UserType.AGENT:
            await self.update_agent_score(
                agent_id=entity_id,
                action=ReputationAction.FRAUD,
                metadata=metadata,
            )
            return await self.get_agent_reputation(entity_id)
        else:
            await self.update_human_score(
                wallet_id=entity_id,
                action=ReputationAction.FRAUD,
                metadata=metadata,
            )
            return await self.get_human_reputation(entity_id)
