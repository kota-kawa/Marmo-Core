import { Twitter, Share2, Link2, Check } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface ShareButtonsProps {
  title: string;
  url?: string;
  className?: string;
}

export function ShareButtons({ title, url, className = '' }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);

  const shareUrl = url || (typeof window !== 'undefined' ? window.location.href : '');
  const encodedTitle = encodeURIComponent(title);
  const encodedUrl = encodeURIComponent(shareUrl);

  const iconBtn =
    'liquid-glass flex h-10 w-10 items-center justify-center rounded-full text-muted-foreground transition-transform hover:scale-[1.03] hover:text-foreground';

  const handleTwitterShare = () => {
    window.open(
      `https://twitter.com/intent/tweet?text=${encodedTitle}&url=${encodedUrl}`,
      'twitter-share',
      'width=600,height=400',
    );
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title, url: shareUrl });
      } catch {
        /* cancelled */
      }
    }
  };

  return (
    <div className={cn('flex flex-wrap items-center gap-3', className)}>
      <span className="text-xs uppercase tracking-widest text-muted-foreground">Share</span>
      <button type="button" onClick={handleTwitterShare} className={iconBtn} title="Share on X">
        <Twitter className="h-4 w-4" />
      </button>
      <button type="button" onClick={handleCopyLink} className={iconBtn} title="Copy link">
        {copied ? <Check className="h-4 w-4 text-foreground" /> : <Link2 className="h-4 w-4" />}
      </button>
      {typeof navigator !== 'undefined' && navigator.share && (
        <button type="button" onClick={handleNativeShare} className={iconBtn} title="Share">
          <Share2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
