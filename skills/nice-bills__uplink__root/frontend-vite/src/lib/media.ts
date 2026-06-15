/**
 * Genesis visual system — one cinematic source, verified stills, navy cohesion.
 * All remote URLs are checked (no 404s). Swap assets here only.
 */

export type MediaKind = 'video' | 'image';

export interface MediaAsset {
  id: string;
  kind: MediaKind;
  src: string;
  alt: string;
  poster?: string;
}

/** Primary loop — used site-wide for ambient continuity */
export const GENESIS_HERO_VIDEO =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260314_131748_f2ca2a28-fed7-44c8-b9a9-bd9acdd5ec31.mp4';

/** Fallback still when video/images fail — deep navy galaxy */
export const GENESIS_POSTER =
  'https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=crop&w=1920&q=85';

/** Cohesive stills: deep navy / blue / soft light only (verified HTTP 200) */
export const COHESIVE_STILLS: MediaAsset[] = [
  {
    id: 'still-orbit',
    kind: 'image',
    src: 'https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=crop&w=1600&q=85',
    alt: 'Deep space light over dark water',
  },
  {
    id: 'still-agents',
    kind: 'image',
    src: 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=1600&q=85',
    alt: 'Autonomous agent in soft studio light',
  },
  {
    id: 'still-network',
    kind: 'image',
    src: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=1600&q=85',
    alt: 'Network infrastructure in blue ambient light',
  },
  {
    id: 'still-chain',
    kind: 'image',
    src: 'https://images.unsplash.com/photo-1639762681485-074b7f938ba0?auto=format&fit=crop&w=1600&q=85',
    alt: 'On-chain visualization in deep blue',
  },
  {
    id: 'still-signal',
    kind: 'image',
    src: 'https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1600&q=85',
    alt: 'Abstract signal forms in navy',
  },
  {
    id: 'still-horizon',
    kind: 'image',
    src: 'https://images.unsplash.com/photo-1506318137071-a8e063b4bec0?auto=format&fit=crop&w=1600&q=85',
    alt: 'Horizon glow through atmospheric haze',
  },
];

export const SHOWCASE_GALLERY = COHESIVE_STILLS;

/** Per-route overlay mood — same video, different depth (coherent flow) */
export type AmbientOverlay = 'hero' | 'soft' | 'deep' | 'focus';

export const AMBIENT_OVERLAY: Record<string, AmbientOverlay> = {
  home: 'hero',
  campaigns: 'soft',
  leaderboard: 'soft',
  create: 'deep',
  profile: 'deep',
  campaignDetail: 'focus',
  embed: 'deep',
};

export type PageBackgroundKey = keyof typeof AMBIENT_OVERLAY;

/** @deprecated Route keys map to overlay moods; video is always GENESIS_HERO_VIDEO */
export const PAGE_BACKGROUNDS = {
  home: {
    id: 'ambient-hero',
    kind: 'video' as const,
    src: GENESIS_HERO_VIDEO,
    alt: 'Genesis ambient',
    poster: GENESIS_POSTER,
  },
} as const;

export const CAMPAIGN_COVER_POOL: MediaAsset[] = COHESIVE_STILLS.map((s, i) => ({
  ...s,
  id: `cover-${i + 1}`,
  src: s.src.replace('w=1600', 'w=800'),
}));

export function getCampaignCover(campaignId: string, avatarUrl?: string): MediaAsset {
  if (avatarUrl) {
    return {
      id: `avatar-${campaignId}`,
      kind: 'image',
      src: avatarUrl,
      alt: 'Campaign author',
    };
  }
  let hash = 0;
  for (let i = 0; i < campaignId.length; i++) {
    hash = (hash + campaignId.charCodeAt(i)) % CAMPAIGN_COVER_POOL.length;
  }
  return CAMPAIGN_COVER_POOL[hash] ?? CAMPAIGN_COVER_POOL[0];
}

export function getAmbientOverlay(routeKey: PageBackgroundKey = 'campaigns'): AmbientOverlay {
  return AMBIENT_OVERLAY[routeKey] ?? 'soft';
}
