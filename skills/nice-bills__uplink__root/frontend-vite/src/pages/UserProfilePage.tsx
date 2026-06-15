import { useEffect, useState } from 'react';
import { useAccount } from 'wagmi';
import { Wallet, Clock, ArrowUpRight, PlusCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageShell } from '../components/layout/PageShell';
import { PageHeader } from '../components/layout/PageHeader';
import { GlassPanel } from '../components/layout/GlassPanel';
import { Button } from '../components/ui/Button';
import { Progress } from '../components/ui/Progress';
import { FilterTabs } from '@/components/ui/FilterTabs';
import { SEO } from '../components/SEO';
import type { Donation, Campaign } from '../types';
import { API_URL, formatAddress, formatAmount, calculateProgress } from '../lib/api';

type Tab = 'overview' | 'donations' | 'campaigns';

export function UserProfilePage() {
  const { address, isConnected } = useAccount();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [donations, setDonations] = useState<(Donation & { campaign_title?: string })[]>([]);
  const [myCampaigns, setMyCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalDonated: 0,
    donationCount: 0,
    campaignsCreated: 0,
    totalRaised: 0,
  });

  useEffect(() => {
    if (!address) return;

    async function fetchProfile() {
      try {
        const res = await fetch(`${API_URL}/campaigns?limit=100`);
        const campaigns: Campaign[] = await res.json();

        const userCampaigns = campaigns.filter(
          (c) => c.agent_id?.toLowerCase() === address!.toLowerCase(),
        );
        setMyCampaigns(userCampaigns);

        const allDonations: (Donation & { campaign_title?: string })[] = [];

        for (const campaign of campaigns) {
          try {
            const dRes = await fetch(`${API_URL}/campaigns/${campaign.id}/donations?limit=100`);
            if (!dRes.ok) continue;
            const campaignDonations: Donation[] = await dRes.json();
            for (const d of campaignDonations) {
              if (d.donor_address?.toLowerCase() === address!.toLowerCase()) {
                allDonations.push({ ...d, campaign_title: campaign.title });
              }
            }
          } catch {
            /* skip */
          }
        }

        allDonations.sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );

        setDonations(allDonations);
        setStats({
          totalDonated: allDonations.reduce((sum, d) => sum + d.amount, 0),
          donationCount: allDonations.length,
          campaignsCreated: userCampaigns.length,
          totalRaised: userCampaigns.reduce((sum, c) => sum + (c.raised || 0), 0),
        });
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchProfile();
  }, [address]);

  if (!isConnected) {
    return (
      <PageShell>
        <SEO title="Profile" />
        <div className="container flex max-w-md flex-col items-center">
          <GlassPanel className="w-full p-10 text-center">
            <Wallet className="mx-auto mb-4 h-10 w-10 text-muted-foreground" />
            <h2
              className="mb-2 text-2xl text-foreground"
              style={{ fontFamily: "'Instrument Serif', serif" }}
            >
              Connect your wallet
            </h2>
            <p className="mb-6 text-sm text-muted-foreground">
              View donations, campaigns, and fundraising activity.
            </p>
            <Link to="/campaigns">
              <Button variant="secondary">Browse campaigns</Button>
            </Link>
          </GlassPanel>
        </div>
      </PageShell>
    );
  }

  const statCards = [
    { label: 'Total donated', value: `${formatAmount(stats.totalDonated)} MON` },
    { label: 'Donations', value: String(stats.donationCount) },
    { label: 'Campaigns', value: String(stats.campaignsCreated) },
    { label: 'Raised', value: `${formatAmount(stats.totalRaised)} MON` },
  ];

  return (
    <PageShell>
      <SEO title="Profile" />
      <div className="container max-w-4xl">
        <PageHeader
          kicker="Your account"
          title={formatAddress(address!)}
          description={address!}
        />

        <div className="mb-8 flex justify-center">
          <Link to="/create">
            <Button>
              <PlusCircle className="h-4 w-4" />
              Create campaign
            </Button>
          </Link>
        </div>

        <div className="mb-10 grid grid-cols-2 gap-4 md:grid-cols-4">
          {statCards.map((stat) => (
            <GlassPanel key={stat.label} className="p-4 text-center">
              <p
                className="text-xl text-foreground"
                style={{ fontFamily: "'Instrument Serif', serif" }}
              >
                {stat.value}
              </p>
              <p className="mt-1 text-xs uppercase tracking-widest text-muted-foreground">
                {stat.label}
              </p>
            </GlassPanel>
          ))}
        </div>

        <FilterTabs
          options={['overview', 'donations', 'campaigns'] as const}
          value={activeTab}
          onChange={setActiveTab}
          labels={{
            overview: 'Overview',
            donations: 'Donations',
            campaigns: 'Campaigns',
          }}
          className="mb-8"
        />

        {activeTab === 'overview' && (
          <div className="grid gap-6 md:grid-cols-2">
            <GlassPanel className="p-6">
              <div className="mb-4 flex items-center justify-between">
                <p className="flex items-center gap-2 text-xs uppercase tracking-widest text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  Recent activity
                </p>
                <button
                  type="button"
                  onClick={() => setActiveTab('donations')}
                  className="text-xs text-foreground hover:underline"
                >
                  View all
                </button>
              </div>
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : donations.length === 0 ? (
                <p className="text-sm text-muted-foreground">No donations yet.</p>
              ) : (
                <ul className="divide-y divide-border/50">
                  {donations.slice(0, 3).map((d) => (
                    <li key={d.id} className="flex justify-between py-3">
                      <div>
                        <Link
                          to={`/campaign/${d.campaign_id}`}
                          className="text-sm text-foreground hover:text-muted-foreground"
                        >
                          {d.campaign_title || 'Campaign'}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {new Date(d.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <span className="text-sm text-foreground">
                        {formatAmount(d.amount)} {d.token_type}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </GlassPanel>

            <GlassPanel className="p-6">
              <div className="mb-4 flex items-center justify-between">
                <p className="text-xs uppercase tracking-widest text-muted-foreground">
                  My campaigns
                </p>
                <button
                  type="button"
                  onClick={() => setActiveTab('campaigns')}
                  className="text-xs text-foreground hover:underline"
                >
                  View all
                </button>
              </div>
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : myCampaigns.length === 0 ? (
                <p className="text-sm text-muted-foreground">No campaigns yet.</p>
              ) : (
                <ul className="space-y-4">
                  {myCampaigns.slice(0, 3).map((c) => {
                    const p = calculateProgress(c.raised, c.goal);
                    return (
                      <li key={c.id}>
                        <Link
                          to={`/campaign/${c.id}`}
                          className="text-sm font-medium text-foreground hover:text-muted-foreground"
                        >
                          {c.title}
                        </Link>
                        <Progress value={p} className="mt-2" size="sm" />
                        <p className="mt-1 text-xs text-muted-foreground">{p.toFixed(0)}% funded</p>
                      </li>
                    );
                  })}
                </ul>
              )}
            </GlassPanel>
          </div>
        )}

        {activeTab === 'donations' && (
          <GlassPanel className="overflow-hidden">
            {loading ? (
              <p className="p-8 text-center text-muted-foreground">Loading...</p>
            ) : donations.length === 0 ? (
              <p className="p-8 text-center text-muted-foreground">No donations yet.</p>
            ) : (
              <ul className="divide-y divide-border/50">
                {donations.map((d) => (
                  <li
                    key={d.id}
                    className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-foreground/[0.03]"
                  >
                    <div>
                      <Link
                        to={`/campaign/${d.campaign_id}`}
                        className="text-sm font-medium text-foreground"
                      >
                        {d.campaign_title || 'Campaign'}
                      </Link>
                      <p className="text-xs text-muted-foreground">
                        {new Date(d.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-foreground">
                        {formatAmount(d.amount)} {d.token_type}
                      </p>
                      <a
                        href={`https://explorer.monad.xyz/tx/${d.tx_hash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                      >
                        {formatAddress(d.tx_hash)}
                        <ArrowUpRight className="h-3 w-3" />
                      </a>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </GlassPanel>
        )}

        {activeTab === 'campaigns' && (
          <GlassPanel className="overflow-hidden">
            {loading ? (
              <p className="p-8 text-center text-muted-foreground">Loading...</p>
            ) : myCampaigns.length === 0 ? (
              <div className="p-8 text-center">
                <p className="mb-4 text-muted-foreground">No campaigns created.</p>
                <Link to="/create">
                  <Button>Create your first</Button>
                </Link>
              </div>
            ) : (
              <ul className="divide-y divide-border/50">
                {myCampaigns.map((c) => {
                  const p = calculateProgress(c.raised, c.goal);
                  return (
                    <li key={c.id} className="px-6 py-5">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <Link
                            to={`/campaign/${c.id}`}
                            className="text-lg text-foreground hover:text-muted-foreground"
                            style={{ fontFamily: "'Instrument Serif', serif" }}
                          >
                            {c.title}
                          </Link>
                          <p className="mt-1 line-clamp-1 text-sm text-muted-foreground">
                            {c.description || 'No description'}
                          </p>
                        </div>
                        <span className="text-xs uppercase text-muted-foreground">{c.status}</span>
                      </div>
                      <Progress value={p} className="mt-3" />
                      <div className="mt-3 flex justify-between text-xs text-muted-foreground">
                        <span>{p.toFixed(0)}% funded</span>
                        <span>
                          {formatAmount(c.raised || 0)} / {formatAmount(c.goal || 0)} MON
                        </span>
                      </div>
                      <Link to={`/campaign/${c.id}`} className="mt-4 inline-block">
                        <Button size="sm" variant="secondary">
                          View details
                        </Button>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </GlassPanel>
        )}
      </div>
    </PageShell>
  );
}
