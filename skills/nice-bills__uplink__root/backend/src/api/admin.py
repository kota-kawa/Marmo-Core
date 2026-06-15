"""
Admin API endpoints

Provides platform administration controls including
emergency pause/resume functionality.
"""

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel

from src.middleware.emergency_pause import get_pause_status, set_pause_status
from src.config import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])

# Simple admin key from environment (upgrade to proper auth in production)
settings = get_settings()
ADMIN_KEY = settings.ADMIN_KEY


class PauseRequest(BaseModel):
    paused: bool
    reason: str = ""


class PauseResponse(BaseModel):
    paused: bool
    reason: str


def verify_admin(x_admin_key: str = Header(...)) -> None:
    """Verify admin authorization via header key."""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )


@router.get("/pause", response_model=PauseResponse)
async def get_pause(x_admin_key: str = Header(...)) -> PauseResponse:
    """Get current pause status."""
    verify_admin(x_admin_key)
    status_data = get_pause_status()
    return PauseResponse(**status_data)


@router.post("/pause", response_model=PauseResponse)
async def toggle_pause(
    request: PauseRequest,
    x_admin_key: str = Header(...),
) -> PauseResponse:
    """Pause or resume the platform."""
    verify_admin(x_admin_key)
    status_data = set_pause_status(request.paused, request.reason)
    return PauseResponse(**status_data)
