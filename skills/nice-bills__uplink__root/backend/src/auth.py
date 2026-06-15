from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from typing import Optional
import hmac

from src.config import get_settings, Settings

# Define API Key headers
# We use X-Admin-Key for admin actions and X-Agent-Key for automated agent actions
admin_header_scheme = APIKeyHeader(name="X-Admin-Key", auto_error=False)
agent_header_scheme = APIKeyHeader(name="X-Agent-Key", auto_error=False)


async def verify_admin_key(
    key: Optional[str] = Security(admin_header_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    """Verify the admin API key using constant-time comparison."""
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Admin-Key header",
        )
    
    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(key, settings.ADMIN_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )
    
    return key


async def verify_agent_key(
    key: Optional[str] = Security(agent_header_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    """Verify the agent API key using constant-time comparison."""
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Agent-Key header",
        )
    
    # Use constant-time comparison
    if not hmac.compare_digest(key, settings.AGENT_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid agent key",
        )
    
    return key
