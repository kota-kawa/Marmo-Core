import { useState, useEffect } from 'react'
import { api, Config, Provider } from '../api/client'
import './Settings.css'

export function Settings() {
  const [config, setConfig] = useState<Config | null>(null)
  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('general')

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [configData, providersData] = await Promise.all([
        api.getConfig().catch(() => null),
        api.getProviders().catch(() => []),
      ])
      setConfig(configData)
      setProviders(providersData)
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setLoading(false)
    }
  }

  async function saveConfig() {
    if (!config) return
    setSaving(true)
    try {
      await api.saveConfig(config)
    } catch (error) {
      console.error('Failed to save config:', error)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="settings-page">
        <div className="loading">
          <div className="spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Settings</h1>
      </div>

      <div className="settings-tabs">
        <button
          className={`tab ${activeTab === 'general' ? 'active' : ''}`}
          onClick={() => setActiveTab('general')}
        >
          General
        </button>
        <button
          className={`tab ${activeTab === 'providers' ? 'active' : ''}`}
          onClick={() => setActiveTab('providers')}
        >
          Providers
        </button>
        <button
          className={`tab ${activeTab === 'mcp' ? 'active' : ''}`}
          onClick={() => setActiveTab('mcp')}
        >
          MCP
        </button>
        <button
          className={`tab ${activeTab === 'advanced' ? 'active' : ''}`}
          onClick={() => setActiveTab('advanced')}
        >
          Advanced
        </button>
      </div>

      <div className="settings-content">
        {activeTab === 'general' && (
          <div className="settings-section">
            <h2>General Settings</h2>
            
            <div className="form-group">
              <label className="form-label">Default Provider</label>
              <select
                className="input"
                value={config?.llm?.default_provider || 'openai'}
                onChange={(e) =>
                  setConfig({
                    ...config!,
                    llm: { ...config!.llm, default_provider: e.target.value },
                  })
                }
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Default Model</label>
              <input
                type="text"
                className="input"
                value={config?.llm?.default_model || 'gpt-4o'}
                onChange={(e) =>
                  setConfig({
                    ...config!,
                    llm: { ...config!.llm, default_model: e.target.value },
                  })
                }
              />
            </div>

            <div className="form-group">
              <label className="form-label">Storage</label>
              <div className="toggle">
                <input
                  type="checkbox"
                  id="storage"
                  checked={config?.storage?.enabled ?? true}
                  onChange={(e) =>
                    setConfig({
                      ...config!,
                      storage: { ...config!.storage, enabled: e.target.checked },
                    })
                  }
                />
                <label htmlFor="storage">Enable persistent storage</label>
              </div>
            </div>

            <button
              className="btn btn-primary"
              onClick={saveConfig}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        )}

        {activeTab === 'providers' && (
          <div className="settings-section">
            <h2>API Providers</h2>
            
            <div className="providers-list">
              {providers.map((provider) => (
                <div key={provider.name} className="provider-card">
                  <div className="provider-info">
                    <div className="provider-name">{provider.name}</div>
                    <div className="provider-type">{provider.type}</div>
                  </div>
                  <button className="btn btn-ghost btn-sm">Configure</button>
                </div>
              ))}
            </div>

            <button className="btn btn-secondary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Add Provider
            </button>
          </div>
        )}

        {activeTab === 'mcp' && (
          <div className="settings-section">
            <h2>MCP Servers</h2>
            <p className="text-muted">Configure Model Context Protocol servers</p>
            
            <button className="btn btn-secondary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Add MCP Server
            </button>
          </div>
        )}

        {activeTab === 'advanced' && (
          <div className="settings-section">
            <h2>Advanced Settings</h2>
            
            <div className="form-group">
              <label className="form-label">Context Strategy</label>
              <select className="input">
                <option value="sliding">Sliding Window</option>
                <option value="summary">Summary</option>
                <option value="importance">Importance</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Max Tokens</label>
              <input
                type="number"
                className="input"
                defaultValue={8000}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
