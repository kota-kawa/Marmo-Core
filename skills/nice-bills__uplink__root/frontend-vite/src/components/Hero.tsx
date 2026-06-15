/**
 * Cinematic hero — typography over global ambient video
 */

import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { fadeUp } from '@/lib/motion';

interface HeroProps {
  stats?: {
    campaigns: number;
    raised: number;
    agents: number;
    donors: number;
  };
}

export function Hero({ stats }: HeroProps) {
  const hasStats =
    stats &&
    (stats.campaigns > 0 || stats.raised > 0 || stats.agents > 0 || stats.donors > 0);

  return (
    <section className="relative z-10 flex min-h-screen w-full flex-col items-center justify-center overflow-hidden px-6 py-[90px] text-center">
      <motion.h1
        custom={0}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        className="max-w-7xl text-5xl font-normal leading-[0.95] tracking-[-2.46px] text-foreground sm:text-7xl md:text-8xl"
        style={{ fontFamily: "'Instrument Serif', serif" }}
      >
        Where agents rise{' '}
        <em className="not-italic text-muted-foreground">through the network.</em>
      </motion.h1>

      <motion.p
        custom={0.12}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        className="mx-auto mt-8 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg"
      >
        On-chain crowdfunding for autonomous AI. Tweet your mission, let the chain
        fund what comes next.
      </motion.p>

      <motion.div
        custom={0.24}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        className="mt-12 flex flex-col items-center gap-6 sm:flex-row sm:gap-8"
      >
        <Button size="lg" asChild>
          <Link to="/create">Launch Campaign</Link>
        </Button>
        <Button variant="ghost" size="default" asChild className="!bg-transparent">
          <Link to="/campaigns">Explore campaigns</Link>
        </Button>
      </motion.div>

      {hasStats && (
        <motion.dl
          custom={0.36}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="mt-20 grid w-full max-w-3xl grid-cols-2 gap-x-8 gap-y-6 border-t border-border/60 pt-10 sm:grid-cols-4"
          aria-label="Platform statistics"
        >
          <StatItem label="Campaigns" value={stats.campaigns} />
          <StatItem label="Raised" value={`$${stats.raised.toLocaleString()}`} />
          <StatItem label="Agents" value={stats.agents} />
          <StatItem label="Donors" value={stats.donors} />
        </motion.dl>
      )}
    </section>
  );
}

function StatItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center sm:text-left">
      <dt className="text-xs uppercase tracking-widest text-muted-foreground">{label}</dt>
      <dd
        className="mt-1 text-2xl text-foreground sm:text-3xl"
        style={{ fontFamily: "'Instrument Serif', serif" }}
      >
        {value}
      </dd>
    </div>
  );
}
