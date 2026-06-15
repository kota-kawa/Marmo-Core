/**
 * Embeddable campaign widget — inline styles (no Tailwind in iframe)
 */

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import type { Campaign } from '../types';
import { API_URL, formatAmount, calculateProgress } from '../lib/api';

export function EmbedPage() {
  const { id } = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    fetch(`${API_URL}/campaigns/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error('Not found');
        return res.json();
      })
      .then(setCampaign)
      .catch(() => setError('Campaign not found'));
  }, [id]);

  if (error) {
    return (
      <div style={styles.container}>
        <p style={styles.error}>{error}</p>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div style={styles.container}>
        <div style={styles.skeleton} />
      </div>
    );
  }

  const progress = calculateProgress(campaign.raised, campaign.goal);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.badge}>Genesis</span>
        <span style={styles.status}>{campaign.status}</span>
      </div>

      <h2 style={styles.title}>{campaign.title}</h2>

      <div style={styles.progressTrack}>
        <div style={{ ...styles.progressBar, width: `${progress}%` }} />
      </div>

      <div style={styles.statsRow}>
        <div>
          <div style={styles.statValue}>{formatAmount(campaign.raised)} MON</div>
          <div style={styles.statLabel}>Raised</div>
        </div>
        {campaign.goal ? (
          <div style={{ textAlign: 'right' as const }}>
            <div style={styles.statValue}>{formatAmount(campaign.goal)} MON</div>
            <div style={styles.statLabel}>Goal</div>
          </div>
        ) : null}
      </div>

      <a
        href={`${window.location.origin}/campaign/${campaign.id}`}
        target="_blank"
        rel="noopener noreferrer"
        style={styles.cta}
      >
        Donate on Genesis →
      </a>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: "'Inter', sans-serif",
    background: 'hsl(201, 100%, 13%)',
    border: '1px solid hsl(0, 0%, 18%)',
    borderRadius: '16px',
    padding: '16px',
    maxWidth: '400px',
    color: 'hsl(0, 0%, 100%)',
    fontSize: '13px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  badge: {
    fontFamily: "'Instrument Serif', serif",
    fontSize: '14px',
    letterSpacing: '-0.02em',
  },
  status: {
    color: 'hsl(240, 4%, 66%)',
    fontSize: '10px',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  title: {
    fontFamily: "'Instrument Serif', serif",
    fontSize: '18px',
    fontWeight: 400,
    marginBottom: '12px',
    lineHeight: 1.3,
  },
  progressTrack: {
    background: 'hsl(0, 0%, 10%)',
    height: '4px',
    borderRadius: '4px',
    width: '100%',
    marginBottom: '12px',
    overflow: 'hidden',
  },
  progressBar: {
    background: 'hsl(0, 0%, 100%)',
    height: '100%',
    transition: 'width 0.3s ease',
  },
  statsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '16px',
  },
  statValue: {
    fontFamily: "'Instrument Serif', serif",
    fontSize: '16px',
    color: 'hsl(0, 0%, 100%)',
  },
  statLabel: {
    fontSize: '10px',
    color: 'hsl(240, 4%, 66%)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  cta: {
    display: 'block',
    background: 'rgba(255, 255, 255, 0.08)',
    border: '1px solid hsl(0, 0%, 18%)',
    color: 'hsl(0, 0%, 100%)',
    padding: '10px',
    borderRadius: '999px',
    textAlign: 'center' as const,
    fontSize: '12px',
    textDecoration: 'none',
  },
  error: {
    textAlign: 'center' as const,
    padding: '20px',
    color: 'hsl(240, 4%, 66%)',
  },
  skeleton: {
    background: 'hsl(0, 0%, 10%)',
    height: '120px',
    borderRadius: '8px',
  },
};
