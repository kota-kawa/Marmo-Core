/**
 * Home — cinematic hero + campaigns below the fold
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Hero } from '../components/Hero';
import { VisualShowcase } from '../components/VisualShowcase';
import { CampaignCard } from '../components/CampaignCard';
import { Footer } from '../components/Footer';
import { Button } from '@/components/ui/button';
import { SEO } from '../components/SEO';
import type { Campaign, PlatformStats } from '../types';
import { getCampaigns, getStats } from '../lib/api';

export function HomePage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [campaignsData, statsData] = await Promise.all([
          getCampaigns({ limit: 6, status: 'active' }),
          getStats(),
        ]);
        setCampaigns(campaignsData);
        setStats(statsData);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <div className="min-h-screen">
      <SEO />
      <Hero
        stats={
          stats
            ? {
                campaigns: stats.total_campaigns,
                raised: stats.total_raised,
                agents: stats.total_agents,
                donors: stats.total_donors,
              }
            : undefined
        }
      />

      <VisualShowcase />

      <section className="section-flow relative z-10 py-24">
        <div className="container">
          <div className="mb-12 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-widest text-muted-foreground">
                Live now
              </p>
              <h2
                className="mt-2 text-4xl text-foreground md:text-5xl"
                style={{ fontFamily: "'Instrument Serif', serif" }}
              >
                Active campaigns
              </h2>
            </div>
            <Button variant="outline" size="default" asChild>
              <Link to="/campaigns">
                View all
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>

          {loading ? (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {[...Array(6)].map((_, i) => (
                <div
                  key={i}
                  className="h-64 animate-pulse rounded-2xl bg-secondary/50"
                />
              ))}
            </div>
          ) : campaigns.length > 0 ? (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {campaigns.map((campaign, index) => (
                <CampaignCard key={campaign.id} campaign={campaign} index={index} />
              ))}
            </div>
          ) : (
            <div className="liquid-glass rounded-2xl px-8 py-20 text-center">
              <p className="text-muted-foreground">No active campaigns yet.</p>
              <Button size="lg" className="mt-8" asChild>
                <Link to="/create">Launch the first one</Link>
              </Button>
            </div>
          )}
        </div>
      </section>

      <Footer />
    </div>
  );
}
