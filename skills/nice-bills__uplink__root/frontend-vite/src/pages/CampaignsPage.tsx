import { useEffect, useState, useMemo } from 'react';
import { Search, ArrowUpDown } from 'lucide-react';
import { CampaignCard } from '../components/CampaignCard';
import { PageShell } from '../components/layout/PageShell';
import { PageHeader } from '../components/layout/PageHeader';
import { GlassPanel } from '../components/layout/GlassPanel';
import { Input } from '@/components/ui/input';
import { FilterTabs } from '@/components/ui/FilterTabs';
import type { Campaign } from '../types';
import { getCampaigns } from '../lib/api';

type SortOption = 'newest' | 'funded' | 'ending';
type FilterOption = 'all' | 'active' | 'completed';

export function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterOption>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('newest');

  useEffect(() => {
    async function fetchCampaigns() {
      setLoading(true);
      try {
        const status = filter === 'all' ? undefined : filter;
        const data = await getCampaigns({ limit: 50, status });
        setCampaigns(data);
      } catch (error) {
        console.error('Failed to fetch campaigns:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchCampaigns();
  }, [filter]);

  const sortedCampaigns = useMemo(() => {
    let filtered = campaigns.filter(
      (c) =>
        c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.description?.toLowerCase().includes(searchTerm.toLowerCase()),
    );

    switch (sortBy) {
      case 'newest':
        filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        break;
      case 'funded':
        filtered.sort((a, b) => (b.raised || 0) - (a.raised || 0));
        break;
      case 'ending':
        filtered.sort((a, b) => {
          if (!a.deadline) return 1;
          if (!b.deadline) return -1;
          return new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
        });
        break;
    }

    return filtered;
  }, [campaigns, searchTerm, sortBy]);

  return (
    <PageShell>
      <div className="container">
        <PageHeader
          kicker="Browse"
          title={
            <>
              All <em className="not-italic text-muted-foreground">campaigns</em>
            </>
          }
          description="Discover active agent fundraisers on Monad. Search, filter, and sort to find what matters."
        />

        <div className="mb-10 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative max-w-md flex-1">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search campaigns..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-11"
            />
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <FilterTabs
              options={['all', 'active', 'completed'] as const}
              value={filter}
              onChange={setFilter}
            />

            <div className="relative min-w-[180px]">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="h-11 w-full appearance-none rounded-xl border border-border/80 bg-secondary/40 px-4 pr-10 text-sm text-foreground backdrop-blur-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="newest">Newest first</option>
                <option value="funded">Most funded</option>
                <option value="ending">Ending soon</option>
              </select>
              <ArrowUpDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            </div>
          </div>
        </div>

        {loading ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-64 animate-pulse rounded-2xl bg-secondary/40" />
            ))}
          </div>
        ) : sortedCampaigns.length > 0 ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {sortedCampaigns.map((campaign, index) => (
              <CampaignCard key={campaign.id} campaign={campaign} index={index} />
            ))}
          </div>
        ) : (
          <GlassPanel className="px-8 py-20 text-center">
            <p className="text-muted-foreground">No campaigns found.</p>
          </GlassPanel>
        )}
      </div>
    </PageShell>
  );
}
