export declare class RemembrError extends Error {
    readonly status: number;
    constructor(message: string, status: number);
}
export declare class AuthenticationError extends RemembrError {
    constructor(message?: string);
}
export declare class NotFoundError extends RemembrError {
    constructor(message?: string);
}
export declare class ValidationError extends RemembrError {
    readonly errors: Record<string, string[]>;
    constructor(message: string, errors?: Record<string, string[]>);
}
export declare class RateLimitError extends RemembrError {
    readonly retryAfter: number | null;
    constructor(retryAfter?: number | null);
}
//# sourceMappingURL=errors.d.ts.map