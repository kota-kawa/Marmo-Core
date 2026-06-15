import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Loader2, AlertCircle, Copy, Wallet, Info } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';
import { PageShell } from '../components/layout/PageShell';
import { GlassPanel } from '../components/layout/GlassPanel';
import { Button } from '../components/ui/Button';
import { Progress } from '../components/ui/Progress';
import { Input } from '@/components/ui/input';
import { SourceCard } from '../components/SourceCard';
import { ShareButtons } from '../components/ShareButtons';
import { useDonate } from '../hooks/useDonate';
import type { Campaign } from '../types';
import { getCampaign, formatAmount, calculateProgress } from '../lib/api';
import { getCampaignCover } from '@/lib/media';
import { MediaImage } from '../components/MediaImage';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { cn } from '@/lib/utils';

const PLATFORM_TREASURY_ADDRESS = '0xEd4eb043c9faAd76B1Ec5a4522495813099FF77A';

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCampaign() {
      if (!id) return;
      try {
        setCampaign(await getCampaign(id));
      } catch (error) {
        console.error('Failed to fetch campaign:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchCampaign();
  }, [id]);

  if (loading) {
    return (
      <PageShell showFooter={false}>
        <div className="container max-w-4xl">
          <div className="h-96 animate-pulse rounded-2xl bg-secondary/40" />
        </div>
      </PageShell>
    );
  }

  if (!campaign) {
    return (
      <PageShell>
        <div className="container max-w-4xl text-center">
          <h1
            className="mb-4 text-3xl text-foreground"
            style={{ fontFamily: "'Instrument Serif', serif" }}
          >
            Campaign not found
          </h1>
          <Link to="/campaigns">
            <Button variant="secondary">Back to campaigns</Button>
          </Link>
        </div>
      </PageShell>
    );
  }

  const progress = calculateProgress(campaign.raised, campaign.goal);
  const cover = getCampaignCover(campaign.id, campaign.source_author_avatar);

  return (
    <PageShell>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'hsl(201 80% 11%)',
            color: 'hsl(0 0% 100%)',
            border: '1px solid hsl(0 0% 18%)',
            fontFamily: 'Inter, sans-serif',
            fontSize: '0.875rem',
          },
        }}
      />

      <div className="container max-w-5xl">
        <Link
          to="/campaigns"
          className="mb-8 inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to campaigns
        </Link>

        <motion.div
          custom={0}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="mb-10 overflow-hidden rounded-2xl liquid-glass"
        >
          <div className="relative aspect-[21/9] w-full">
            <MediaImage src={cover.src} alt={cover.alt} className="h-full w-full" priority />
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-background via-background/25 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-6 md:p-10">
              <p className="text-xs uppercase tracking-widest text-muted-foreground">
                {campaign.status}
              </p>
              <h1
                className="mt-2 max-w-3xl text-3xl text-foreground md:text-5xl"
                style={{ fontFamily: "'Instrument Serif', serif" }}
              >
                {campaign.title}
              </h1>
            </div>
          </div>
        </motion.div>

        <div className="grid gap-8 lg:grid-cols-5">
          <div className="space-y-6 lg:col-span-3">
            <GlassPanel className="p-6 md:p-8">
              <p className="mt-4 leading-relaxed text-muted-foreground">
                {campaign.description || 'No description provided.'}
              </p>
              <ShareButtons title={campaign.title} className="mt-6" />
            </GlassPanel>

            <SourceCard
              platform={campaign.source_platform}
              authorHandle={campaign.source_author_handle}
              authorName={campaign.source_author_name}
              authorAvatar={campaign.source_author_avatar}
              content={campaign.source_content}
              url={campaign.source_url}
              timestamp={campaign.source_timestamp}
            />
          </div>

          <div className="animate-fade-rise-delay lg:col-span-2">
            <GlassPanel className="sticky top-28 p-6 md:p-8">
              <p className="text-xs uppercase tracking-widest text-muted-foreground">Funding</p>

              <div className="mt-4 mb-6">
                <div className="flex items-baseline justify-between gap-2">
                  <span
                    className="text-3xl text-foreground"
                    style={{ fontFamily: "'Instrument Serif', serif" }}
                  >
                    ${formatAmount(campaign.raised)}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    of ${formatAmount(campaign.goal || 0)}
                  </span>
                </div>
                <Progress value={progress} className="mt-4" />
                <p className="mt-2 text-xs text-muted-foreground">{progress.toFixed(0)}% funded</p>
              </div>

              <div className="mb-6 rounded-xl border border-border/60 bg-secondary/30 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <Wallet className="h-4 w-4 text-foreground" />
                  <span className="text-xs uppercase tracking-widest text-muted-foreground">
                    Platform treasury
                  </span>
                </div>
                <p className="mb-3 text-xs text-muted-foreground">
                  Donations are tracked on-chain. Treasury address:
                </p>
                <div className="flex items-start gap-2">
                  <code className="flex-1 break-all rounded-lg bg-background/50 px-3 py-2 text-xs text-foreground/90">
                    {PLATFORM_TREASURY_ADDRESS}
                  </code>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(PLATFORM_TREASURY_ADDRESS);
                      toast.success('Address copied');
                    }}
                    className="liquid-glass flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
                    title="Copy address"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                  <Info className="h-3 w-3" />
                  Funds tracked by campaign ID
                </p>
              </div>

              {campaign.status === 'active' && (
                <DonationForm campaignId={campaign.id} />
              )}
            </GlassPanel>
          </div>
        </div>
      </div>
    </PageShell>
  );
}

function DonationForm({ campaignId }: { campaignId: string }) {
  const [amount, setAmount] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [validationError, setValidationError] = useState('');

  const { donate, isLoading, isPending, error } = useDonate({
    campaignId,
    onSuccess: (txHash) => {
      toast.success(`Donation successful! TX: ${txHash.slice(0, 10)}...`);
      setAmount('');
      setValidationError('');
      setIsAnonymous(false);
    },
    onError: (err) => {
      toast.error(err.message || 'Transaction failed');
    },
  });

  const validateAmount = (value: string): string => {
    if (!value) return 'Amount is required';
    const num = parseFloat(value);
    if (isNaN(num)) return 'Enter a valid number';
    if (num <= 0) return 'Must be greater than 0';
    if (num > 1000000) return 'Exceeds maximum';
    return '';
  };

  const handleDonate = async () => {
    const err = validateAmount(amount);
    if (err) {
      setValidationError(err);
      return;
    }
    setValidationError('');
    await donate(parseFloat(amount));
  };

  return (
    <>
      <label className="mb-2 block text-xs uppercase tracking-widest text-muted-foreground">
        Amount (MON)
      </label>
      <Input
        type="number"
        value={amount}
        onChange={(e) => {
          setAmount(e.target.value);
          if (validationError) setValidationError(validateAmount(e.target.value));
        }}
        onBlur={() => setValidationError(validateAmount(amount))}
        placeholder="0.00"
        disabled={isLoading}
        className={cn(validationError && 'border-foreground/40')}
      />
      {validationError && (
        <p className="mt-2 flex items-center gap-1 text-xs text-foreground/80">
          <AlertCircle className="h-3 w-3" />
          {validationError}
        </p>
      )}

      <label className="mt-4 flex cursor-pointer items-center gap-3">
        <input
          type="checkbox"
          checked={isAnonymous}
          onChange={(e) => setIsAnonymous(e.target.checked)}
          disabled={isLoading}
          className="h-4 w-4 rounded border-border accent-foreground"
        />
        <span className="text-sm text-muted-foreground">Donate anonymously</span>
      </label>

      <Button className="mt-6 w-full" onClick={handleDonate} disabled={isLoading || !amount}>
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            {isPending ? 'Confirming...' : 'Processing...'}
          </>
        ) : (
          'Donate now'
        )}
      </Button>
      {error && <p className="mt-2 text-xs text-muted-foreground">{error.message}</p>}
    </>
  );
}
