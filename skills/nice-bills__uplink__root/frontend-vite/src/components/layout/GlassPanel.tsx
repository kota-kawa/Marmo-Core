import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface GlassPanelProps {
  children: ReactNode;
  className?: string;
  as?: 'div' | 'section' | 'article';
}

export function GlassPanel({ children, className, as: Tag = 'div' }: GlassPanelProps) {
  return (
    <Tag className={cn('liquid-glass rounded-2xl', className)}>{children}</Tag>
  );
}
