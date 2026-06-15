import type { Memory, MemorySearchResult, StoreOptions, UpdateOptions, SearchOptions, ListOptions, PaginatedResponse, RegisterResponse, AgentProfile, RemembrClientOptions } from './types.js';
import { RemembrError, AuthenticationError, NotFoundError, ValidationError, RateLimitError } from './errors.js';
export type { Memory, MemorySearchResult, StoreOptions, UpdateOptions, SearchOptions, ListOptions, PaginatedResponse, RegisterResponse, AgentProfile, RemembrClientOptions, };
export { RemembrError, AuthenticationError, NotFoundError, ValidationError, RateLimitError, };
export declare class RemembrClient {
    private readonly baseUrl;
    private readonly token;
    constructor(agentToken: string, options?: RemembrClientOptions);
    static register(ownerToken: string, name: string, options?: RemembrClientOptions & {
        description?: string;
    }): Promise<{
        client: RemembrClient;
        agentId: string;
        agentToken: string;
    }>;
    remember(value: string, options?: StoreOptions): Promise<Memory>;
    set(key: string, value: string, visibility?: Memory['visibility']): Promise<Memory>;
    update(key: string, data: UpdateOptions): Promise<Memory>;
    forget(key: string): Promise<void>;
    get(key: string): Promise<Memory>;
    list(options?: ListOptions): Promise<PaginatedResponse<Memory>>;
    search(query: string, options?: SearchOptions): Promise<MemorySearchResult[]>;
    searchCommons(query: string, options?: SearchOptions): Promise<MemorySearchResult[]>;
    shareWith(key: string, agentId: string): Promise<void>;
    private request;
    private handleError;
}
//# sourceMappingURL=index.d.ts.map