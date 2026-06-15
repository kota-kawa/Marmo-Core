const API_BASE = '/api'

export interface Project {
  id: string
  name: string
  directory: string
  created_at: string
  updated_at: string
}

export interface Session {
  id: string
  project_id: string
  title: string
  directory: string
  parent_id: string | null
  created_at: string
  updated_at: string
  archived_at: string | null
}

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  tool_call_id: string | null
  tokens: number
  created_at: string
}

export interface MessagePart {
  id: string
  message_id: string
  part_type: string
  data: Record<string, unknown>
}

export interface Config {
  llm: {
    default_provider: string
    default_model: string
    providers: Record<string, unknown>
  }
  storage: {
    enabled: boolean
    db_path: string
  }
  mcp_servers: Record<string, unknown>
}

export interface Provider {
  name: string
  type: string
  api_key?: string
  base_url?: string
  model?: string
}

export interface Tool {
  name: string
  description: string
  parameters: Record<string, unknown>
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const error = await response.text().catch(() => 'Unknown error')
      throw new Error(`API Error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>('/projects')
  }

  async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/projects/${id}`)
  }

  async createProject(name: string, directory: string): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, directory }),
    })
  }

  async getSessions(projectId?: string): Promise<Session[]> {
    const params = projectId ? `?project_id=${projectId}` : ''
    return this.request<Session[]>(`/sessions${params}`)
  }

  async getSession(id: string): Promise<Session> {
    return this.request<Session>(`/sessions/${id}`)
  }

  async createSession(
    projectId: string,
    title?: string,
    directory?: string
  ): Promise<Session> {
    return this.request<Session>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, title, directory }),
    })
  }

  async deleteSession(id: string): Promise<void> {
    await this.request(`/sessions/${id}`, { method: 'DELETE' })
  }

  async forkSession(id: string, newTitle?: string): Promise<Session> {
    return this.request<Session>(`/sessions/${id}/fork`, {
      method: 'POST',
      body: JSON.stringify({ title: newTitle }),
    })
  }

  async shareSession(id: string): Promise<{ url: string }> {
    return this.request<{ url: string }>(`/sessions/${id}/share`, {
      method: 'POST',
    })
  }

  async unshareSession(id: string): Promise<void> {
    await this.request(`/sessions/${id}/share`, { method: 'DELETE' })
  }

  async getMessages(sessionId: string): Promise<Message[]> {
    return this.request<Message[]>(`/sessions/${sessionId}/messages`)
  }

  async sendMessage(
    sessionId: string,
    content: string
  ): Promise<{ message: Message; response: string }> {
    return this.request<{ message: Message; response: string }>(
      `/sessions/${sessionId}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({ content }),
      }
    )
  }

  async getConfig(): Promise<Config> {
    return this.request<Config>('/config')
  }

  async saveConfig(config: Config): Promise<void> {
    await this.request('/config', {
      method: 'POST',
      body: JSON.stringify(config),
    })
  }

  async getProviders(): Promise<Provider[]> {
    return this.request<Provider[]>('/providers')
  }

  async addProvider(provider: Provider): Promise<void> {
    await this.request('/providers', {
      method: 'POST',
      body: JSON.stringify(provider),
    })
  }

  async removeProvider(name: string): Promise<void> {
    await this.request(`/providers/${name}`, { method: 'DELETE' })
  }

  async getTools(): Promise<Tool[]> {
    return this.request<Tool[]>('/tools')
  }

  async getStats(): Promise<{
    total_sessions: number
    total_messages: number
    tokens_in: number
    tokens_out: number
  }> {
    return this.request('/stats')
  }

  async getSessionStats(): Promise<{
    tokens_used: number
    context_percent_used: number
    max_tokens_context: number
    model: string
    provider: string
  }> {
    return this.request('/stats')
  }

  async getHealth(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health')
  }
}

export const api = new ApiClient()
