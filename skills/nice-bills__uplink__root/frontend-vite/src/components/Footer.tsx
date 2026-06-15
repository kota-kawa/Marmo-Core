/**
 * Footer — minimal, matches cinematic register
 */

import { Link } from 'react-router-dom';
import { Twitter } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-border/40 bg-background py-16">
      <div className="container">
        <div className="grid gap-12 md:grid-cols-4">
          <div className="md:col-span-2">
            <Link
              to="/"
              className="text-2xl text-foreground"
              style={{ fontFamily: "'Instrument Serif', serif" }}
            >
              Genesis
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted-foreground">
              On-chain crowdfunding for autonomous AI agents on Monad.
            </p>
          </div>

          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted-foreground">
              Platform
            </h4>
            <ul className="mt-4 space-y-2">
              <li>
                <Link
                  to="/campaigns"
                  className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  Campaigns
                </Link>
              </li>
              <li>
                <Link
                  to="/leaderboard"
                  className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  Leaderboard
                </Link>
              </li>
              <li>
                <Link
                  to="/create"
                  className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  Create
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted-foreground">
              Connect
            </h4>
            <ul className="mt-4 space-y-2">
              <li>
                <a
                  href="https://twitter.com/break_whileloop"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Twitter className="h-4 w-4" />
                  Twitter
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-4 border-t border-border/40 pt-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Genesis Protocol</p>
          <p className="text-xs uppercase tracking-widest">Monad testnet</p>
        </div>
      </div>
    </footer>
  );
}
