"""Tests for the /health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """The health endpoint should return a JSON response with overall status."""
    response = await client.get("/health")
    assert response.status_code in (200, 503)

    data = response.json()
    assert "status" in data
    assert "app" in data
    assert "version" in data
    assert "components" in data
    assert "database" in data["components"]
    assert "chromadb" in data["components"]
    assert "llm" in data["components"]


@pytest.mark.asyncio
async def test_health_database_ok(client):
    """The database component should report 'ok' status (in-memory SQLite)."""
    response = await client.get("/health")
    data = response.json()
    db_status = data["components"]["database"]["status"]
    assert db_status == "ok"


@pytest.mark.asyncio
async def test_health_includes_latency(client):
    """The top-level response should include a latency_ms field."""
    response = await client.get("/health")
    data = response.json()
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], (int, float))
