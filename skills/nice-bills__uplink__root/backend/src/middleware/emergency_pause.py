"""
Emergency Pause Middleware

Provides the ability to pause all campaign operations in case of 
security incidents or critical bugs. The pause state is controlled
via an admin endpoint.
"""

import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Simple in-memory pause state (upgrade to Redis for multi-instance)
_platform_paused = False
_pause_reason = ""


def get_pause_status() -> dict:
    return {
        "paused": _platform_paused,
        "reason": _pause_reason,
    }


def set_pause_status(paused: bool, reason: str = "") -> dict:
    global _platform_paused, _pause_reason
    _platform_paused = paused
    _pause_reason = reason
    action = "PAUSED" if paused else "RESUMED"
    logger.warning(f"Platform {action}: {reason}")
    return get_pause_status()


class EmergencyPauseMiddleware(BaseHTTPMiddleware):
    """
    Blocks state-changing requests to campaign/donation endpoints
    when the platform is in emergency pause mode.
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    PAUSED_PATHS = {"/campaigns", "/donate"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if not _platform_paused:
            return await call_next(request)

        # Allow safe methods (reads) even during pause
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        # Allow admin endpoints
        if request.url.path.startswith("/admin"):
            return await call_next(request)

        # Allow health check
        if request.url.path == "/health":
            return await call_next(request)

        # Block state-changing requests to campaign paths
        for path in self.PAUSED_PATHS:
            if path in request.url.path:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Platform is temporarily paused: {_pause_reason}",
                )

        return await call_next(request)
