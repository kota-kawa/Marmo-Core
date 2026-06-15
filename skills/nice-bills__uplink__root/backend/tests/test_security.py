
import pytest
from httpx import AsyncClient
from src.main import app
from src.config import get_settings

settings = get_settings()

@pytest.mark.asyncio
async def test_agent_security_rejection(client):
    # Test without header
    response = await client.post("/agents", json={})
    assert response.status_code in [401, 403]

    # Test with invalid header
    response = await client.post("/agents", headers={"X-Agent-Key": "invalid"}, json={})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_agent_security_success(client):
    # This test might fail 422 (validation error) but should PASS security (not 401/403)
    # 422 means we got past auth and hit Pydantic validation
    response = await client.post("/agents", headers={"X-Agent-Key": settings.AGENT_API_KEY}, json={})
    assert response.status_code == 422
