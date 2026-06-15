import { RemembrError, AuthenticationError, NotFoundError, ValidationError, RateLimitError, } from './errors.js';
export { RemembrError, AuthenticationError, NotFoundError, ValidationError, RateLimitError, };
const DEFAULT_BASE_URL = 'https://remembr.dev/api/v1';
export class RemembrClient {
    constructor(agentToken, options = {}) {
        this.token = agentToken;
        this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
    }
    // ---------------------------------------------------------------------------
    // Factory
    // ---------------------------------------------------------------------------
    static async register(ownerToken, name, options = {}) {
        const baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
        const res = await fetch(`${baseUrl}/agents/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                description: options.description,
                owner_token: ownerToken,
            }),
        });
        const data = (await res.json());
        if (!res.ok) {
            throw new RemembrError(data.error ?? 'Registration failed', res.status);
        }
        return {
            client: new RemembrClient(data.agent_token, { baseUrl }),
            agentId: data.agent_id,
            agentToken: data.agent_token,
        };
    }
    // ---------------------------------------------------------------------------
    // Write
    // ---------------------------------------------------------------------------
    async remember(value, options = {}) {
        return this.request('POST', '/memories', { value, ...options });
    }
    async set(key, value, visibility = 'private') {
        return this.remember(value, { key, visibility });
    }
    async update(key, data) {
        return this.request('PATCH', `/memories/${encodeURIComponent(key)}`, data);
    }
    async forget(key) {
        await this.request('DELETE', `/memories/${encodeURIComponent(key)}`);
    }
    // ---------------------------------------------------------------------------
    // Read
    // ---------------------------------------------------------------------------
    async get(key) {
        return this.request('GET', `/memories/${encodeURIComponent(key)}`);
    }
    async list(options = {}) {
        const params = new URLSearchParams();
        if (options.page)
            params.set('page', String(options.page));
        if (options.tags?.length)
            params.set('tags', options.tags.join(','));
        const qs = params.toString();
        return this.request('GET', `/memories${qs ? '?' + qs : ''}`);
    }
    // ---------------------------------------------------------------------------
    // Search
    // ---------------------------------------------------------------------------
    async search(query, options = {}) {
        const params = new URLSearchParams({ q: query });
        if (options.limit)
            params.set('limit', String(options.limit));
        if (options.tags?.length)
            params.set('tags', options.tags.join(','));
        const res = await this.request('GET', `/memories/search?${params}`);
        return res.data;
    }
    async searchCommons(query, options = {}) {
        const params = new URLSearchParams({ q: query });
        if (options.limit)
            params.set('limit', String(options.limit));
        if (options.tags?.length)
            params.set('tags', options.tags.join(','));
        const res = await this.request('GET', `/commons/search?${params}`);
        return res.data;
    }
    // ---------------------------------------------------------------------------
    // Sharing
    // ---------------------------------------------------------------------------
    async shareWith(key, agentId) {
        await this.request('POST', `/memories/${encodeURIComponent(key)}/share`, {
            agent_id: agentId,
        });
    }
    // ---------------------------------------------------------------------------
    // Internals
    // ---------------------------------------------------------------------------
    async request(method, path, body) {
        const url = `${this.baseUrl}${path}`;
        const headers = {
            Authorization: `Bearer ${this.token}`,
            Accept: 'application/json',
        };
        const init = { method, headers };
        if (body !== undefined && method !== 'GET' && method !== 'DELETE') {
            headers['Content-Type'] = 'application/json';
            init.body = JSON.stringify(body);
        }
        const res = await fetch(url, init);
        if (!res.ok) {
            await this.handleError(res);
        }
        if (res.status === 204 || method === 'DELETE') {
            return undefined;
        }
        return (await res.json());
    }
    async handleError(res) {
        let data;
        try {
            data = (await res.json());
        }
        catch {
            throw new RemembrError(`HTTP ${res.status}`, res.status);
        }
        const message = (data.error ?? data.message ?? `HTTP ${res.status}`);
        switch (res.status) {
            case 401:
                throw new AuthenticationError(message);
            case 404:
                throw new NotFoundError(message);
            case 422:
                throw new ValidationError(message, (data.errors ?? {}));
            case 429:
                throw new RateLimitError(res.headers.get('Retry-After') ? Number(res.headers.get('Retry-After')) : null);
            default:
                throw new RemembrError(message, res.status);
        }
    }
}
//# sourceMappingURL=index.js.map