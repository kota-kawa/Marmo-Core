export class RemembrError extends Error {
    constructor(message, status) {
        super(message);
        this.name = 'RemembrError';
        this.status = status;
    }
}
export class AuthenticationError extends RemembrError {
    constructor(message = 'Invalid or inactive agent token') {
        super(message, 401);
        this.name = 'AuthenticationError';
    }
}
export class NotFoundError extends RemembrError {
    constructor(message = 'Memory not found') {
        super(message, 404);
        this.name = 'NotFoundError';
    }
}
export class ValidationError extends RemembrError {
    constructor(message, errors = {}) {
        super(message, 422);
        this.name = 'ValidationError';
        this.errors = errors;
    }
}
export class RateLimitError extends RemembrError {
    constructor(retryAfter = null) {
        super('Rate limit exceeded', 429);
        this.name = 'RateLimitError';
        this.retryAfter = retryAfter;
    }
}
//# sourceMappingURL=errors.js.map