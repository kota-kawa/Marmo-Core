/**
 * Inner-page shell — content over global ambient (no per-route video reload)
 */

import type { ReactNode } from 'react';
import { Footer } from '../Footer';

interface PageShellProps {
  children: ReactNode;
  className?: string;
  showFooter?: boolean;
}

export function PageShell({ children, className = '', showFooter = true }: PageShellProps) {
  return (
    <div className={`relative min-h-screen ${className}`}>
      <div className="relative z-10 pt-28 pb-16">{children}</div>
      {showFooter && <Footer />}
    </div>
  );
}
