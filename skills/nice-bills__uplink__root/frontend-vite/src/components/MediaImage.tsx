import { useState } from 'react';
import { motion } from 'framer-motion';
import { GENESIS_POSTER } from '@/lib/media';
import { imageReveal } from '@/lib/motion';
import { cn } from '@/lib/utils';

interface MediaImageProps {
  src: string;
  alt: string;
  className?: string;
  /** Unified color grade for gallery/covers */
  cohesive?: boolean;
  priority?: boolean;
}

export function MediaImage({
  src,
  alt,
  className,
  cohesive = true,
  priority = false,
}: MediaImageProps) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const displaySrc = failed ? GENESIS_POSTER : src;

  return (
    <div className={cn('relative overflow-hidden bg-background', className)}>
      <div
        className={cn(
          'absolute inset-0 bg-secondary/30 transition-opacity duration-700',
          loaded ? 'opacity-0' : 'opacity-100',
        )}
        aria-hidden
      />
      <motion.img
        src={displaySrc}
        alt={alt}
        variants={imageReveal}
        initial="hidden"
        animate={loaded ? 'visible' : 'hidden'}
        onLoad={() => setLoaded(true)}
        onError={() => {
          setFailed(true);
          setLoaded(true);
        }}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        className={cn(
          'h-full w-full object-cover will-change-transform',
          cohesive && 'media-cohesive-grade',
        )}
      />
    </div>
  );
}
