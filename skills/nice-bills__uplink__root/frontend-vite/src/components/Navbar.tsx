/**
 * Glassmorphic navigation — cinematic landing register
 */

import { Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Home', href: '/' },
  { name: 'Campaigns', href: '/campaigns' },
  { name: 'Leaderboard', href: '/leaderboard' },
  { name: 'Create', href: '/create' },
];

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/';
    return location.pathname.startsWith(href);
  };

  const isHome = location.pathname === '/';

  return (
    <header
      className={cn(
        'relative z-50 w-full',
        isHome ? 'absolute top-0 left-0 right-0' : 'sticky top-0 border-b border-border/40 bg-background/80 backdrop-blur-md',
      )}
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="mx-auto flex max-w-7xl flex-row items-center justify-between px-8 py-6">
        <Link
          to="/"
          className="text-3xl tracking-tight text-foreground transition-opacity hover:opacity-90"
          style={{ fontFamily: "'Instrument Serif', serif" }}
        >
          Genesis<sup className="text-xs align-super">®</sup>
        </Link>

        <nav className="hidden items-center gap-8 md:flex" aria-label="Primary">
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              aria-current={isActive(item.href) ? 'page' : undefined}
              className={cn(
                'text-sm transition-colors',
                isActive(item.href)
                  ? 'text-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {item.name}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden sm:block [&_button]:!liquid-glass [&_button]:!rounded-full [&_button]:!text-sm">
            <ConnectButton chainStatus="icon" showBalance={false} />
          </div>

          <Button size="default" className="hidden md:inline-flex" asChild>
            <Link to="/create">Launch Campaign</Link>
          </Button>

          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="rounded-full p-2 text-muted-foreground transition-colors hover:text-foreground md:hidden"
            aria-expanded={isOpen}
            aria-label="Toggle navigation menu"
          >
            {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="border-t border-border/40 bg-background/95 px-8 py-6 backdrop-blur-md md:hidden">
          <nav className="flex flex-col gap-4" aria-label="Mobile">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setIsOpen(false)}
                className={cn(
                  'text-sm transition-colors',
                  isActive(item.href)
                    ? 'text-foreground'
                    : 'text-muted-foreground',
                )}
              >
                {item.name}
              </Link>
            ))}
            <Link to="/profile" onClick={() => setIsOpen(false)} className="text-sm text-muted-foreground">
              Profile
            </Link>
            <div className="pt-4">
              <ConnectButton />
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
