# Genesis Design System

## Color (HSL CSS variables)

- background: 201 100% 13% (deep navy)
- foreground: 0 0% 100%
- muted-foreground: 240 4% 66%
- primary: 0 0% 100% / primary-foreground: 0 0% 4%
- secondary, muted, accent: 0 0% 10%
- border, input: 0 0% 18%

Neutrals tinted toward navy. No pure #000 or #fff.

## Typography

- Display: Instrument Serif (headings, logo)
- Body: Inter 400/500
- CSS: `--font-display`, `--font-body`

## Motion

- fade-rise keyframes, 0.8s ease-out, staggered delays
- hover scale 1.03 on liquid-glass CTAs
- prefers-reduced-motion: disable animations

## Components

- `.liquid-glass` for nav and primary CTAs
- shadcn/ui Button as base for actions

## Hero

- Fullscreen looping muted video background
- Minimal overlay; video provides depth

## Media (cohesive ambient)

- **One** hero video (`GENESIS_HERO_VIDEO`) — persistent via `AmbientBackground`, never remounts on navigation
- Overlay moods per route (`hero` / `soft` / `deep` / `focus`) — smooth crossfade, same light throughout
- Gallery + covers: verified navy stills only (`COHESIVE_STILLS`), unified `.media-cohesive-grade`
- `MediaImage`: skeleton → fade-in, fallback to `GENESIS_POSTER` on error
- Motion: framer-motion page transitions + `fadeUp` stagger (see `src/lib/motion.ts`)

## Inner pages

- `PageShell`: per-route background from `PAGE_BACKGROUNDS`, dimmed overlay
- `GlassPanel`, `PageHeader`, shadcn `Input` / `Textarea` / `FilterTabs`
- No industrial cards, grid lines, or monospace labels

## Tooling

- Frontend package manager: **pnpm** (`packageManager` in `package.json`, `pnpm-lock.yaml`)
