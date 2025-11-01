"""
Tests for health and readiness endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health endpoint returns ok status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_endpoint(client: AsyncClient):
    """Test readiness endpoint."""
    response = await client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert "db" in data
    assert "cache" in data
    assert "ready" in data

