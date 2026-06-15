import { ExternalLink, Twitter } from 'lucide-react';
import { GlassPanel } from './layout/GlassPanel';

interface SourceCardProps {
  platform?: string | null;
  authorHandle?: string | null;
  authorName?: string | null;
  authorAvatar?: string | null;
  content?: string | null;
  url?: string | null;
  timestamp?: string | null;
}

export function SourceCard({
  platform,
  authorHandle,
  authorName,
  authorAvatar,
  content,
  url,
  timestamp,
}: SourceCardProps) {
  if (!platform || !content) return null;

  const platformIcon = () => {
    switch (platform?.toLowerCase()) {
      case 'twitter':
      case 'x':
        return <Twitter className="h-4 w-4" />;
      default:
        return null;
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  return (
    <GlassPanel className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs uppercase tracking-widest text-muted-foreground">Source</p>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
      </div>

      <div className="flex items-center gap-3 mb-4">
        {authorAvatar ? (
          <img
            src={authorAvatar}
            alt={authorName || authorHandle || 'Author'}
            className="h-10 w-10 rounded-full object-cover"
          />
        ) : (
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-sm text-muted-foreground">
            {(authorHandle || '?')[0].toUpperCase()}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate font-medium text-foreground">
              {authorName || authorHandle}
            </span>
            <span className="text-muted-foreground">{platformIcon()}</span>
          </div>
          {authorHandle && (
            <span className="text-sm text-muted-foreground">
              @{authorHandle.replace('@', '')}
            </span>
          )}
        </div>
      </div>

      <p className="leading-relaxed text-foreground/90">{content}</p>

      {timestamp && (
        <p className="mt-4 text-xs text-muted-foreground">{formatDate(timestamp)}</p>
      )}
    </GlassPanel>
  );
}
