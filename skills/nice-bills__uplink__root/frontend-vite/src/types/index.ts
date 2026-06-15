/**
 * Genesis Platform TypeScript Types
 * Matches backend schemas
 */

// ============ Core Types ============

export type UUID = string;

export type CampaignStatus = 'active' | 'completed' | 'cancelled';

export type Platform = 'twitter' | 'moltbook';

export type TokenType = 'MON' | 'USDC' | 'ETH';

// ============ Source Message ============

export interface SourceMessage {
    platform: Platform;
    author_handle: string;
    author_name: string;
    author_avatar?: string;
    content: string;
    timestamp: string;
    url?: string;
}

// ============ Agent ============

export interface Agent {
    id: UUID;
    address: string;
    name: string;
    description?: string;
    reputation_score: number;
    is_active: boolean;
    is_blacklisted?: boolean;
    blacklist_reason?: string;
    moltbook_api_key?: string;
    created_at: string;
}

export interface AgentCreate {
    address: string;
    name: string;
    description?: string;
    reputation_score?: number;
    is_active?: boolean;
    moltbook_api_key?: string;
}

// ============ Campaign ============

export interface Campaign {
    id: UUID;
    agent_id: UUID;
    title: string;
    description?: string;
    goal?: number;
    raised: number;
    deadline?: string;
    status: CampaignStatus;
    metadata_uri?: string;
    created_at: string;
    // Source message fields (flattened in response)
    source_platform?: Platform;
    source_author_handle?: string;
    source_author_name?: string;
    source_author_avatar?: string;
    source_content?: string;
    source_url?: string;
    source_timestamp?: string;
    is_verified?: boolean;
    verification_status?: string;
    // Treasury address for receiving donations
    treasury_address?: string;
}

export interface CampaignCreate {
    agent_id: UUID;
    title: string;
    description?: string;
    goal?: number;
    deadline?: string;
    metadata_uri?: string;
    source_message?: SourceMessage;
}

// ============ Donation ============

export interface Donation {
    id: UUID;
    campaign_id: UUID;
    donor_address: string;
    amount: number;
    token_type: TokenType;
    tx_hash: string;
    is_anonymous?: boolean;
    created_at: string;
}

export interface DonationCreate {
    campaign_id: UUID;
    donor_address: string;
    amount: number;
    token_type: TokenType;
    tx_hash: string;
    is_anonymous?: boolean;
}

// ============ Wallet ============

export interface Wallet {
    id: UUID;
    address: string;
    wallet_id?: string;
    chain_type: string;
    user_id?: string;
    twitter_handle?: string;
    provider: string;
    reputation_score: number;
    is_blacklisted: boolean;
    blacklist_reason?: string;
    created_at: string;
}

// ============ Reputation ============

export interface LeaderboardEntry {
    rank: number;
    id: UUID;
    address: string;
    name?: string;
    twitter_handle?: string;
    reputation_score: number;
}

export interface LeaderboardResponse {
    user_type: 'agent' | 'human';
    entries: LeaderboardEntry[];
    total: number;
}

// ============ Stats ============

export interface PlatformStats {
    total_campaigns: number;
    active_campaigns: number;
    total_raised: number;
    total_agents: number;
    total_donors: number;
    total_donations: number;
    average_donation: number;
    top_campaign?: {
        id: string;
        title: string;
        raised: number;
    };
}

// ============ Payments ============

export interface PaymentRequest {
    amount: number;
    token_type: TokenType;
    recipient_address: string;
    donor_address: string;
    campaign_id?: UUID;
}

export interface PaymentResponse {
    success: boolean;
    tx_hash?: string;
    message: string;
}

// ============ API Response Types ============

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface ApiError {
    detail: string;
    status_code?: number;
}

// ============ Campaign Updates ============

export interface CampaignUpdateEntry {
    id: UUID;
    campaign_id: UUID;
    title: string;
    content: string;
    is_milestone: boolean;
    milestone_percentage?: number;
    created_at: string;
}

export interface CampaignUpdateCreate {
    title: string;
    content: string;
    is_milestone?: boolean;
    milestone_percentage?: number;
}

// ============ Withdrawal ============

export interface WithdrawalRequest {
    id: UUID;
    agent_id: UUID;
    campaign_id: UUID;
    amount: number;
    recipient_address: string;
    status: string;
    reason?: string;
    delay_hours: number;
    scheduled_at?: string;
    processed_at?: string;
    tx_hash?: string;
    created_at: string;
}

export interface WithdrawalRequestCreate {
    campaign_id: UUID;
    amount: number;
    recipient_address: string;
    reason?: string;
}
