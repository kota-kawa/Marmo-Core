/**
 * Campaign card — glass surface, editorial type (no brutalist notches)
 */

import { Link } from 'react-router-dom';
import type { Campaign } from '../types';
import { Countdown } from './Countdown';
import { formatAmount, calculateProgress } from '../lib/api';
import { getCampaignCover } from '@/lib/media';
import { MediaImage } from './MediaImage';
import { cn } from '@/lib/utils';

interface CampaignCardProps {
  campaign: Campaign;
  index?: number;
}

export function CampaignCard({ campaign, index = 0 }: CampaignCardProps) {
  const progress = calculateProgress(campaign.raised, campaign.goal);
  const cover = getCampaignCover(campaign.id, campaign.source_author_avatar);

  return (
    <article
      className={cn(
        'group animate-fade-rise',
        index > 0 && 'animate-fade-rise-delay',
      )}
      style={{ animationDelay: index > 1 ? `${0.1 * index}s` : undefined }}
    >
      <Link
        to={`/campaign/${campaign.id}`}
        className="liquid-glass block overflow-hidden rounded-2xl transition-transform hover:scale-[1.01]"
      >
        <div className="relative aspect-[16/10] w-full overflow-hidden">
          <MediaImage
            src={cover.src}
            alt={cover.alt}
            className="h-full w-full transition-transform duration-[900ms] ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:scale-[1.03]"
          />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-background/85 via-background/20 to-transparent" />
        </div>

        <div className="p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <span
            className={cn(
              'text-xs uppercase tracking-widest',
              campaign.status === 'active'
                ? 'text-foreground'
                : 'text-muted-foreground',
            )}
          >
            {campaign.status}
          </span>
          {campaign.deadline && campaign.status === 'active' && (
            <Countdown deadline={campaign.deadline} />
          )}
        </div>

        <h3
          className="mb-2 line-clamp-2 text-xl text-foreground transition-colors group-hover:text-muted-foreground"
          style={{ fontFamily: "'Instrument Serif', serif" }}
        >
          {campaign.title}
        </h3>

        <p className="mb-6 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
          {campaign.description || 'No description yet.'}
        </p>

        <div className="mb-3 h-px w-full bg-border/80" />

        <div className="h-1 w-full overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-foreground/90 transition-all duration-500"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>

        <p className="mt-4 text-sm text-muted-foreground">
          <span className="text-foreground">${formatAmount(campaign.raised)}</span>
          {' '}
          of ${formatAmount(campaign.goal || 0)} raised
        </p>
        </div>
      </Link>
    </article>
  );
}
