from datetime import datetime
from enum import Enum as PythonEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SqlAlchemyEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base model with common attributes."""

    pass


class UserType(str, PythonEnum):
    """User type enumeration."""

    AGENT = "agent"
    HUMAN = "human"


class ReputationAction(str, PythonEnum):
    """Reputation action types."""

    FUNDS_RAISED = "funds_raised"
    ONCHAIN_EXECUTION = "onchain_execution"
    CAMPAIGN_DELIVERED = "campaign_delivered"
    CAMPAIGN_COMPLETED = "campaign_completed"
    POSITIVE_REVIEW = "positive_review"
    DEFAULT = "default"
    FAILED_DELIVERY = "failed_delivery"
    FRAUD = "fraud"


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Agent(Base, TimestampMixin):
    """Agent model for AI agents and human fundraisers."""

    __tablename__ = "agents"

    # Add composite index for common queries
    __table_args__ = (
        Index("idx_agent_status_score", "is_active", "is_blacklisted", "reputation_score"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    address: Mapped[str] = mapped_column(String(42), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reputation_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    blacklist_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    moltbook_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ERC-8004 verification for agents
    is_erc8004_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        comment="Whether agent is registered via ERC-8004 standard",
    )
    erc8004_token_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, comment="ERC-8004 token ID if registered"
    )

    # Relationships with eager loading
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )
    treasury: Mapped["Treasury"] = relationship(
        "Treasury",
        back_populates="agent",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )
    proposals: Mapped[list["MultiSigProposal"]] = relationship(
        "MultiSigProposal", back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )
    reputation_history: Mapped[list["ReputationHistory"]] = relationship(
        "ReputationHistory",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(ReputationHistory.created_at)",
    )


class Campaign(Base, TimestampMixin):
    """Campaign model for fundraising campaigns."""

    __tablename__ = "campaigns"

    # Optimize queries by status and creation date
    __table_args__ = (
        Index("idx_campaign_status_created", "status", "created_at"),
        Index("idx_campaign_agent_status", "agent_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal: Mapped[float | None] = mapped_column(Float, nullable=True)
    raised: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    withdrawn: Mapped[float] = mapped_column(Float, default=0.0)  # Total amount already withdrawn
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    metadata_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    treasury_address: Mapped[str | None] = mapped_column(String(42), nullable=True)

    # Source message fields
    source_platform: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_author_handle: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_author_avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_status: Mapped[str] = mapped_column(
        String(50), default="unverified"
    )  # unverified, pending, verified, rejected

    agent: Mapped["Agent"] = relationship("Agent", back_populates="campaigns")
    donations: Mapped[list["Donation"]] = relationship(
        "Donation",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(Donation.created_at)",
    )
    updates: Mapped[list["CampaignUpdate"]] = relationship(
        "CampaignUpdate",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(CampaignUpdate.created_at)",
    )


class Donation(Base, TimestampMixin):
    """Donation model for tracking contributions."""

    __tablename__ = "donations"

    # Index for donor lookups and campaign aggregation
    __table_args__ = (
        Index("idx_donation_donor_campaign", "donor_address", "campaign_id"),
        Index("idx_donation_created", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    donor_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    token_type: Mapped[str] = mapped_column(String(10), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="donations")


class Treasury(Base, TimestampMixin):
    """Treasury model for agent fund management."""

    __tablename__ = "treasuries"

    __table_args__ = (Index("idx_treasury_agent", "agent_id", "balance"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    safe_address: Mapped[str] = mapped_column(String(42), nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0.0, index=True)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="treasury")


class MultiSigProposal(Base, TimestampMixin):
    """MultiSig proposal model for treasury withdrawals."""

    __tablename__ = "multi_sig_proposals"

    __table_args__ = (
        Index("idx_proposal_agent_status", "agent_id", "status"),
        Index("idx_proposal_deadline", "deadline"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proposal_id: Mapped[str] = mapped_column(String(66), nullable=False)
    recipient: Mapped[str] = mapped_column(String(42), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approvals: Mapped[dict[str, str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="proposals")


class ReputationHistory(Base, TimestampMixin):
    """Reputation history model for tracking score changes."""

    __tablename__ = "reputation_history"

    __table_args__ = (
        Index("idx_reputation_user_time", "user_type", "created_at"),
        Index("idx_reputation_agent", "agent_id", "created_at"),
        Index("idx_reputation_wallet", "wallet_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_type: Mapped[str] = mapped_column(String(10), nullable=False)
    agent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    wallet_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_score: Mapped[int] = mapped_column(Integer, nullable=False)
    new_score: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="reputation_history")
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="reputation_history")


class Wallet(Base, TimestampMixin):
    """Wallet model for user wallet management."""

    __tablename__ = "wallets"

    __table_args__ = (
        Index("idx_wallet_user_provider", "user_id", "provider"),
        Index("idx_wallet_twitter", "twitter_handle"),
        Index("idx_wallet_entity", "entity_id", "user_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    wallet_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )  # For Privy wallet ID
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )  # Agent ID or User ID
    user_type: Mapped[UserType] = mapped_column(
        SqlAlchemyEnum(UserType), nullable=True, index=True
    )  # AGENT or HUMAN
    twitter_handle: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    address: Mapped[str] = mapped_column(String(42), unique=True, nullable=False, index=True)
    encrypted_private_key: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Nullable for Privy wallets
    chain_type: Mapped[str] = mapped_column(
        String(20), default="ethereum", index=True
    )  # ethereum, solana, etc.
    provider: Mapped[str] = mapped_column(
        String(50), default="self-custody", index=True
    )  # self-custody, privy, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reputation_score: Mapped[int] = mapped_column(Integer, default=0)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    reputation_history: Mapped[list["ReputationHistory"]] = relationship(
        "ReputationHistory",
        back_populates="wallet",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(ReputationHistory.created_at)",
    )


class CampaignUpdate(Base, TimestampMixin):
    """Campaign update/milestone posted by the campaign creator."""

    __tablename__ = "campaign_updates"
    __table_args__ = (Index("idx_update_campaign", "campaign_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_milestone: Mapped[bool] = mapped_column(Boolean, default=False)
    milestone_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="updates")


class WithdrawalRequest(Base, TimestampMixin):
    """Withdrawal request with time-delayed processing."""

    __tablename__ = "withdrawal_requests"
    __table_args__ = (Index("idx_withdrawal_agent_status", "agent_id", "status"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    recipient_address: Mapped[str] = mapped_column(String(42), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, approved, rejected, completed
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    delay_hours: Mapped[int] = mapped_column(Integer, default=24)  # Hours before auto-approval
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)

    agent: Mapped["Agent"] = relationship("Agent")
    campaign: Mapped["Campaign"] = relationship("Campaign")
