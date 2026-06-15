import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api, Session } from '../api/client'
import './Dashboard.css'

export function Dashboard() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    total_sessions: 0,
    total_messages: 0,
    tokens_in: 0,
    tokens_out: 0,
  })

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [sessionsData, statsData] = await Promise.all([
        api.getSessions(),
        api.getStats().catch(() => stats),
      ])
      setSessions(sessionsData)
      setStats(statsData)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">
          <div className="spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <Link to="/projects" className="btn btn-primary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Session
        </Link>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_sessions}</div>
            <div className="stat-label">Total Sessions</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <message square x="3" y="3" width="18" height="18" rx="2" ry="2" />
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_messages}</div>
            <div className="stat-label">Messages</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.tokens_in.toLocaleString()}</div>
            <div className="stat-label">Tokens In</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.tokens_out.toLocaleString()}</div>
            <div className="stat-label">Tokens Out</div>
          </div>
        </div>
      </div>

      <div className="recent-sessions">
        <div className="section-header">
          <h2>Recent Sessions</h2>
        </div>

        {sessions.length === 0 ? (
          <div className="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <p>No sessions yet</p>
            <Link to="/projects" className="btn btn-primary">
              Start a new session
            </Link>
          </div>
        ) : (
          <div className="session-list">
            {sessions.map((session) => (
              <Link
                key={session.id}
                to={`/session/${session.id}`}
                className="session-item"
              >
                <div className="session-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                </div>
                <div className="session-info">
                  <div className="session-title">{session.title}</div>
                  <div className="session-meta">
                    {new Date(session.updated_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="session-arrow">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
