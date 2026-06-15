/**
 * Genesis Platform API Client
 * Comprehensive API client for all backend endpoints
 */

import type {
  Agent,
  AgentCreate,
  Campaign,
  CampaignCreate,
  CampaignUpdateCreate,
  CampaignUpdateEntry,
  Donation,
  DonationCreate,
  LeaderboardResponse,
  PaymentRequest,
  PaymentResponse,
  PlatformStats,
  Wallet,
  WithdrawalRequest,
  WithdrawalRequestCreate,
  UUID,
} from '../types';

// API Base URL — dev uses local backend; production defaults to Vercel /api proxy
function resolveApiUrl(): string {
  const configured = import.meta.env.VITE_API_URL as string | undefined;
  if (configured?.trim()) {
    return configured.replace(/\/$/, '');
  }
  if (import.meta.env.DEV) {
    return 'http://localhost:8000';
  }
  return '/api';
}

export const API_URL = resolveApiUrl();

// ============ HTTP Helpers ============

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }

  return response.json();
}

// ============ Health ============

export async function checkHealth(): Promise<{ status: string; timestamp: string }> {
  return fetchApi('/health');
}

// ============ Stats ============

export async function getStats(): Promise<PlatformStats> {
  return fetchApi('/stats');
}

// ============ Agents ============

export async function getAgents(params?: {
  skip?: number;
  limit?: number;
  search?: string;
  is_active?: boolean;
}): Promise<Agent[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set('skip', params.skip.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.search) searchParams.set('search', params.search);
  if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());

  const query = searchParams.toString();
  return fetchApi(`/agents${query ? `?${query}` : ''}`);
}

export async function getAgent(agentId: UUID): Promise<Agent> {
  return fetchApi(`/agents/${agentId}`);
}

export async function getAgentByAddress(address: string): Promise<Agent> {
  return fetchApi(`/agents/address/${address}`);
}

export async function getAgentCampaigns(
  agentId: UUID,
  params?: { skip?: number; limit?: number; status?: string }
): Promise<Campaign[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set('skip', params.skip.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.status) searchParams.set('status_filter', params.status);

  const query = searchParams.toString();
  return fetchApi(`/agents/${agentId}/campaigns${query ? `?${query}` : ''}`);
}

export async function createAgent(data: AgentCreate): Promise<Agent> {
  return fetchApi('/agents', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============ Campaigns ============

export async function getCampaigns(params?: {
  skip?: number;
  limit?: number;
  status?: string;
}): Promise<Campaign[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set('skip', params.skip.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.status) searchParams.set('status', params.status);

  const query = searchParams.toString();
  return fetchApi(`/campaigns${query ? `?${query}` : ''}`);
}

export async function getCampaign(campaignId: UUID): Promise<Campaign> {
  return fetchApi(`/campaigns/${campaignId}`);
}

export async function createCampaign(data: CampaignCreate): Promise<Campaign> {
  return fetchApi('/campaigns', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============ Donations ============

export async function getCampaignDonations(
  campaignId: UUID,
  params?: { skip?: number; limit?: number }
): Promise<Donation[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set('skip', params.skip.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return fetchApi(`/campaigns/${campaignId}/donations${query ? `?${query}` : ''}`);
}

export async function createDonation(
  campaignId: UUID,
  data: Omit<DonationCreate, 'campaign_id'>
): Promise<Donation> {
  return fetchApi(`/campaigns/${campaignId}/donate`, {
    method: 'POST',
    body: JSON.stringify({
      ...data,
      campaign_id: campaignId,
    }),
  });
}

// ============ Reputation ============

export async function getLeaderboard(
  userType: 'agent' | 'human',
  limit?: number
): Promise<LeaderboardResponse> {
  const query = limit ? `?limit=${limit}` : '';
  return fetchApi(`/reputation/leaderboard/${userType}${query}`);
}

// ============ Donation Leaderboard ============

export interface DonorEntry {
  rank: number;
  donor_address: string;
  total_donated: number;
  donation_count: number;
  last_donation_at: string | null;
}

export interface DonorsLeaderboardResponse {
  donors: DonorEntry[];
  total: number;
  generated_at: string;
}

export async function getDonorsLeaderboard(limit?: number): Promise<DonorsLeaderboardResponse> {
  const query = limit ? `?limit=${limit}` : '';
  return fetchApi(`/leaderboard/donors${query}`);
}

export async function getAgentReputation(agentId: UUID): Promise<{
  id: UUID;
  address: string;
  name: string;
  reputation_score: number;
  is_blacklisted: boolean;
  blacklist_reason?: string;
  is_active: boolean;
}> {
  return fetchApi(`/reputation/agent/${agentId}`);
}

// ============ Wallets ============

export async function getWalletByTwitter(twitterHandle: string): Promise<Wallet> {
  return fetchApi(`/wallets/privy/twitter/${twitterHandle}`);
}

export async function createPrivyWallet(
  userId: string,
  twitterHandle?: string
): Promise<Wallet> {
  const params = new URLSearchParams({ user_id: userId });
  if (twitterHandle) params.set('twitter_handle', twitterHandle);

  return fetchApi(`/wallets/privy/create?${params.toString()}`, {
    method: 'POST',
  });
}

// ============ Payments (x402) ============

export async function processPayment(data: PaymentRequest): Promise<PaymentResponse> {
  return fetchApi('/payments/x402', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getPaymentStatus(txHash: string): Promise<{
  tx_hash: string;
  confirmed: boolean;
  status: string;
}> {
  return fetchApi(`/payments/x402/${txHash}/status`);
}

// ============ Utility Functions ============

export function formatAddress(address: string): string {
  if (!address || address.length < 10) return address;
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function formatAmount(amount: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(amount);
}

export function calculateProgress(raised: number, goal?: number): number {
  if (!goal || goal === 0) return 0;
  return Math.min(100, (raised / goal) * 100);
}

// ============ Campaign Updates ============

export async function getCampaignUpdates(
  campaignId: UUID,
  params?: { skip?: number; limit?: number }
): Promise<CampaignUpdateEntry[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set('skip', params.skip.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return fetchApi(`/campaigns/${campaignId}/updates${query ? `?${query}` : ''}`);
}

export async function createCampaignUpdate(
  campaignId: UUID,
  data: CampaignUpdateCreate
): Promise<CampaignUpdateEntry> {
  return fetchApi(`/campaigns/${campaignId}/updates`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============ Withdrawals ============

export async function requestWithdrawal(
  data: WithdrawalRequestCreate
): Promise<WithdrawalRequest> {
  return fetchApi('/withdrawals', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getAgentWithdrawals(
  agentId: UUID
): Promise<WithdrawalRequest[]> {
  return fetchApi(`/withdrawals/agent/${agentId}`);
}

// ============ Verification ============

export async function requestVerification(
  campaignId: UUID
): Promise<{ campaign_id: string; is_verified: boolean; verification_status: string; message: string }> {
  return fetchApi('/verification/request', {
    method: 'POST',
    body: JSON.stringify({ campaign_id: campaignId }),
  });
}

