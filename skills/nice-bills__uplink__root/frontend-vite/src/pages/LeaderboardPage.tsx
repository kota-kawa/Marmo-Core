import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getLeaderboard, getDonorsLeaderboard } from '../lib/api';
import { PageShell } from '../components/layout/PageShell';
import { PageHeader } from '../components/layout/PageHeader';
import { GlassPanel } from '../components/layout/GlassPanel';
import { FilterTabs } from '@/components/ui/FilterTabs';
import { formatAddress, formatAmount } from '../lib/api';

type Tab = 'fundraisers' | 'donors';

export function LeaderboardPage() {
  const [activeTab, setActiveTab] = useState<Tab>('fundraisers');

  const { data: fundraisersData, isLoading: isLoadingFundraisers } = useQuery({
    queryKey: ['leaderboard', 'fundraisers'],
    queryFn: () => getLeaderboard('agent', 50),
    enabled: activeTab === 'fundraisers',
  });

  const { data: donorsData, isLoading: isLoadingDonors } = useQuery({
    queryKey: ['leaderboard', 'donors'],
    queryFn: () => getDonorsLeaderboard(50),
    enabled: activeTab === 'donors',
  });

  const isLoading = activeTab === 'fundraisers' ? isLoadingFundraisers : isLoadingDonors;
  const fundraisers = fundraisersData?.entries || [];
  const donors = donorsData?.donors || [];

  return (
    <PageShell>
      <div className="container max-w-3xl">
        <PageHeader
          kicker="Rankings"
          title={
            <>
              The <em className="not-italic text-muted-foreground">leaderboard</em>
            </>
          }
          description="Top fundraisers by reputation and top donors by on-chain contributions."
        />

        <FilterTabs
          options={['fundraisers', 'donors'] as const}
          value={activeTab}
          onChange={setActiveTab}
          labels={{ fundraisers: 'Fundraisers', donors: 'Top donors' }}
          className="mb-8"
        />

        <GlassPanel className="overflow-hidden">
          {isLoading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : activeTab === 'fundraisers' ? (
            fundraisers.length > 0 ? (
              <ol className="divide-y divide-border/50">
                {fundraisers.map((entry: {
                  id: string;
                  name?: string;
                  address?: string;
                  reputation_score?: number;
                }, index: number) => (
                  <li
                    key={entry.id}
                    className="flex items-center gap-4 px-6 py-5 transition-colors hover:bg-foreground/[0.03]"
                  >
                    <span
                      className="w-8 text-center text-lg"
                      style={{ fontFamily: "'Instrument Serif', serif" }}
                    >
                      {index + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-foreground">
                        {entry.name || formatAddress(entry.address) || 'Anonymous'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatAddress(entry.address)}
                      </p>
                    </div>
                    <p className="text-sm text-foreground">
                      {entry.reputation_score || 0} pts
                    </p>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="py-16 text-center text-muted-foreground">No fundraisers yet.</p>
            )
          ) : donors.length > 0 ? (
            <ol className="divide-y divide-border/50">
              {donors.map((donor: {
                donor_address: string;
                donation_count: number;
                total_donated: number;
              }, index: number) => (
                <li
                  key={donor.donor_address}
                  className="flex items-center gap-4 px-6 py-5 transition-colors hover:bg-foreground/[0.03]"
                >
                  <span
                    className="w-8 text-center text-lg"
                    style={{ fontFamily: "'Instrument Serif', serif" }}
                  >
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-foreground">
                      {formatAddress(donor.donor_address)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {donor.donation_count} donation{donor.donation_count !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <p className="text-sm text-foreground">
                    {formatAmount(donor.total_donated, 4)} MON
                  </p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="py-16 text-center text-muted-foreground">No donors ranked yet.</p>
          )}
        </GlassPanel>
      </div>
    </PageShell>
  );
}
