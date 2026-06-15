"""
CSRF Protection Middleware

Validates CSRF tokens for state-changing requests (POST, PUT, PATCH, DELETE).
The frontend must include a matching token in both a cookie and a header.
"""

import secrets
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.config import get_settings


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Double-submit cookie pattern for CSRF protection.

    - On GET requests, sets a CSRF cookie if not present
    - On state-changing requests, validates that the X-CSRF-Token header
      matches the csrf_token cookie
    """

    CSRF_COOKIE_NAME = "csrf_token"
    CSRF_HEADER_NAME = "x-csrf-token"
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        # Use secure cookies in production (DEBUG=False)
        secure_cookie = not settings.DEBUG

        # Skip CSRF for safe methods
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Set CSRF cookie if not present
            if self.CSRF_COOKIE_NAME not in request.cookies:
                token = secrets.token_hex(32)
                response.set_cookie(
                    self.CSRF_COOKIE_NAME,
                    token,
                    httponly=False,  # Must be readable by JS
                    samesite="lax",
                    secure=secure_cookie,  # True in production, False in dev
                    max_age=3600,
                )
            return response

        # Skip CSRF for webhook endpoints (they use HMAC)
        if request.url.path.startswith("/webhook"):
            return await call_next(request)

        # Validate CSRF token for state-changing requests
        cookie_token = request.cookies.get(self.CSRF_COOKIE_NAME)
        header_token = request.headers.get(self.CSRF_HEADER_NAME)

        if not cookie_token or not header_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing",
            )

        if cookie_token != header_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token mismatch",
            )

        return await call_next(request)
