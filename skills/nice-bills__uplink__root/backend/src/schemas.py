from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentBase(BaseModel):
    address: str = Field(..., min_length=42, max_length=42)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    reputation_score: int = Field(default=0)
    is_active: bool = Field(default=True)
    moltbook_api_key: str | None = Field(default=None, max_length=255)


class AgentCreate(AgentBase):
    pass


class AgentResponse(AgentBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceMessage(BaseModel):
    platform: str = Field(..., min_length=1, max_length=20)
    author_handle: str = Field(..., min_length=1, max_length=100)
    author_name: str = Field(..., min_length=1, max_length=255)
    author_avatar: str | None = Field(default=None, max_length=500)
    content: str = Field(..., min_length=1)
    timestamp: datetime
    url: str | None = Field(default=None, max_length=500)


class CampaignBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    goal: float | None = Field(default=None)
    deadline: datetime | None = None
    metadata_uri: str | None = Field(default=None, max_length=500)


class CampaignCreate(CampaignBase):
    agent_id: UUID
    source_message: SourceMessage | None = None
    wallet_address: str | None = Field(
        default=None, description="Wallet address to receive funds (required if not using Privy)"
    )
    use_privy_wallet: bool = Field(
        default=False, description="Use Privy-managed wallet instead of provided address"
    )


class CampaignResponse(CampaignBase):
    id: UUID
    agent_id: UUID
    raised: float
    status: str
    created_at: datetime
    source_platform: str | None = None
    source_author_handle: str | None = None
    source_author_name: str | None = None
    source_author_avatar: str | None = None
    source_content: str | None = None
    source_url: str | None = None
    source_timestamp: datetime | None = None
    is_verified: bool = False
    verification_status: str = "unverified"
    treasury_address: str | None = None

    model_config = {"from_attributes": True}

    @property
    def source_message(self) -> SourceMessage | None:
        if self.source_platform:
            return SourceMessage(
                platform=self.source_platform,
                author_handle=self.source_author_handle or "",
                author_name=self.source_author_name or "",
                author_avatar=self.source_author_avatar,
                content=self.source_content or "",
                timestamp=self.source_timestamp or self.created_at,
                url=self.source_url,
            )
        return None


class DonationBase(BaseModel):
    donor_address: str = Field(..., min_length=42, max_length=42)
    amount: float = Field(..., gt=0)
    token_type: str = Field(..., min_length=1, max_length=10)
    tx_hash: str = Field(..., min_length=66, max_length=66)
    is_anonymous: bool = Field(default=False)


class DonationCreate(DonationBase):
    campaign_id: UUID


class DonationResponse(DonationBase):
    id: UUID
    campaign_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class TreasuryBase(BaseModel):
    safe_address: str = Field(..., min_length=42, max_length=42)
    balance: float = Field(default=0.0)


class TreasuryCreate(TreasuryBase):
    agent_id: UUID


class TreasuryResponse(TreasuryBase):
    id: UUID
    agent_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class MultiSigProposalBase(BaseModel):
    recipient: str = Field(..., min_length=42, max_length=42)
    amount: float = Field(..., gt=0)
    reason: str | None = None


class ProposalCreate(MultiSigProposalBase):
    agent_id: UUID
    proposal_id: str = Field(..., max_length=66)
    deadline: datetime


class ProposalResponse(MultiSigProposalBase):
    id: UUID
    agent_id: UUID
    proposal_id: str
    approvals: list[str]
    status: str
    deadline: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "0.1.0"


class WalletBase(BaseModel):
    address: str = Field(..., min_length=42, max_length=42)
    user_id: str | None = Field(default=None, max_length=255)
    twitter_handle: str | None = Field(default=None, max_length=100)


class WalletCreate(BaseModel):
    user_id: str | None = Field(default=None, max_length=255)
    twitter_handle: str | None = Field(default=None, max_length=100)


class WalletResponse(WalletBase):
    id: UUID
    wallet_id: str | None = None
    chain_type: str = "ethereum"
    provider: str = "self-custody"
    reputation_score: int = 0
    is_blacklisted: bool = False
    blacklist_reason: str | None = None
    created_at: datetime
    message: str | None = None

    model_config = {"from_attributes": True}


class WalletExport(BaseModel):
    address: str = Field(..., min_length=42, max_length=42)
    private_key: str
    user_id: str | None = None
    twitter_handle: str | None = None
    created_at: datetime


# Reputation Schemas


class AgentReputationResponse(BaseModel):
    id: UUID
    address: str
    name: str
    reputation_score: int
    is_blacklisted: bool
    blacklist_reason: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class HumanReputationResponse(BaseModel):
    id: UUID
    address: str
    twitter_handle: str | None
    reputation_score: int
    is_blacklisted: bool
    blacklist_reason: str | None

    model_config = {"from_attributes": True}


class ReputationHistoryEntry(BaseModel):
    id: UUID
    user_type: str
    action: str
    points: int
    previous_score: int
    new_score: int
    metadata: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReputationHistoryResponse(ReputationHistoryEntry):
    agent_id: UUID | None
    user_id: UUID | None


class LeaderboardEntry(BaseModel):
    rank: int
    id: UUID
    address: str
    name: str | None
    twitter_handle: str | None
    reputation_score: int


class LeaderboardResponse(BaseModel):
    user_type: str
    entries: list[LeaderboardEntry]
    total: int


class ReputationUpdateRequest(BaseModel):
    action: str
    metadata: dict | None = None
    amount: float | None = None


class BlacklistRequest(BaseModel):
    reason: str


# ============ Campaign Updates ============


class CampaignUpdateCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    is_milestone: bool = False
    milestone_percentage: int | None = Field(default=None, ge=0, le=100)


class CampaignUpdateResponse(CampaignUpdateCreate):
    id: UUID
    campaign_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ============ Withdrawal ============


class WithdrawalRequestCreate(BaseModel):
    campaign_id: UUID
    amount: float = Field(..., gt=0)
    recipient_address: str = Field(..., min_length=42, max_length=42)
    reason: str | None = None


class WithdrawalRequestResponse(BaseModel):
    id: UUID
    agent_id: UUID
    campaign_id: UUID
    amount: float
    recipient_address: str
    status: str
    reason: str | None
    delay_hours: int
    scheduled_at: datetime | None
    processed_at: datetime | None
    tx_hash: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ============ Campaign Verification ============


class VerificationRequest(BaseModel):
    campaign_id: UUID
    evidence_url: str | None = Field(default=None, max_length=500)
    notes: str | None = None


class VerificationResponse(BaseModel):
    campaign_id: UUID
    is_verified: bool
    verification_status: str
    message: str
