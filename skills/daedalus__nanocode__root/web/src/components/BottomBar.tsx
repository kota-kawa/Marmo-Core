import { useEffect, useState } from 'react'
import { api } from '../api/client'
import './BottomBar.css'

export interface SessionStats {
  tokens_used: number
  context_percent_used: number
  max_tokens_context: number
  model: string
  provider: string
}

export function BottomBar() {
  const [stats, setStats] = useState<SessionStats | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getSessionStats()
        setStats(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load stats')
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [])

  if (error && !stats) {
    return (
      <div className="bottom-bar">
        <div className="bottom-bar-error">Unable to load stats</div>
      </div>
    )
  }

  return (
    <div className="bottom-bar">
      <div className="bottom-bar-stats">
        <div className="stat-item">
          <span className="stat-label">Tokens:</span>
          <span className="stat-value">{stats?.tokens_used.toLocaleString() ?? '-'}</span>
        </div>
        <div className="stat-divider" />
        <div className="stat-item">
          <span className="stat-label">Context:</span>
          <span className="stat-value">
            {stats?.context_percent_used != null 
              ? `${stats.context_percent_used.toFixed(1)}%` 
              : '-'}
          </span>
        </div>
        <div className="stat-divider" />
        <div className="stat-item">
          <span className="stat-label">Max Context:</span>
          <span className="stat-value">
            {stats?.max_tokens_context?.toLocaleString() ?? '-'}
          </span>
        </div>
        <div className="stat-divider" />
        <div className="stat-item">
          <span className="stat-label">Model:</span>
          <span className="stat-value">{stats?.model ?? '-'}</span>
        </div>
        <div className="stat-divider" />
        <div className="stat-item">
          <span className="stat-label">Provider:</span>
          <span className="stat-value">{stats?.provider ?? '-'}</span>
        </div>
      </div>
    </div>
  )
}
