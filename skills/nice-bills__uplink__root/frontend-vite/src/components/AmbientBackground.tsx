import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { GENESIS_HERO_VIDEO, GENESIS_POSTER, type AmbientOverlay } from '@/lib/media';
import { cn } from '@/lib/utils';

const OVERLAY_CLASS: Record<AmbientOverlay, string> = {
  hero: 'from-background/25 via-background/10 to-background/70',
  soft: 'from-background/55 via-background/72 to-background/88',
  deep: 'from-background/70 via-background/82 to-background/92',
  focus: 'from-background/65 via-background/78 to-background/90',
};

function routeToOverlay(pathname: string): AmbientOverlay {
  if (pathname === '/') return 'hero';
  if (pathname.startsWith('/campaign/')) return 'focus';
  if (pathname.startsWith('/campaigns')) return 'soft';
  if (pathname.startsWith('/leaderboard')) return 'soft';
  if (pathname.startsWith('/create')) return 'deep';
  if (pathname.startsWith('/profile')) return 'deep';
  if (pathname.startsWith('/embed')) return 'deep';
  return 'soft';
}

export function AmbientBackground() {
  const location = useLocation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlay = routeToOverlay(location.pathname);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.play().catch(() => {
      /* autoplay blocked — poster still visible */
    });
  }, []);

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
      aria-hidden
    >
      <video
        ref={videoRef}
        className="ambient-video absolute inset-0 h-full w-full object-cover"
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        poster={GENESIS_POSTER}
      >
        <source src={GENESIS_HERO_VIDEO} type="video/mp4" />
      </video>

      <div className="absolute inset-0 bg-background/40" />

      <AnimatePresence mode="wait">
        <motion.div
          key={overlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
          className={cn(
            'absolute inset-0 bg-gradient-to-b',
            OVERLAY_CLASS[overlay],
          )}
        />
      </AnimatePresence>

      <div className="ambient-vignette absolute inset-0" />
    </div>
  );
}

