"""Tests for /api/v1/app-config CRUD + defaults."""

import pytest


@pytest.mark.asyncio
async def test_list_configs_creates_defaults(client, auth_headers):
    """Listing configs for the first time should auto-create default items."""
    response = await client.get(
        "/api/v1/app-config",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should have at least the default vector_db configs
    keys = {item["config_key"] for item in data}
    assert "vector_db_host" in keys
    assert "vector_db_port" in keys


@pytest.mark.asyncio
async def test_update_config(client, auth_headers):
    """Updating a config item should persist the change."""
    # First ensure defaults exist
    list_resp = await client.get("/api/v1/app-config", headers=auth_headers)
    items = list_resp.json()
    assert len(items) > 0
    config_id = items[0]["id"]
    original_key = items[0]["config_key"]

    response = await client.put(
        f"/api/v1/app-config/{config_id}",
        headers=auth_headers,
        json={
            "config_key": original_key,
            "config_value": "updated_value",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["config_value"] == "updated_value"


@pytest.mark.asyncio
async def test_update_nonexistent_config(client, auth_headers):
    """Updating a non-existent config should return 404."""
    response = await client.put(
        "/api/v1/app-config/999999",
        headers=auth_headers,
        json={
            "config_key": "fake_key",
            "config_value": "value",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_configs_unauthenticated(client):
    """Listing configs without auth should return 401."""
    response = await client.get("/api/v1/app-config")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_batch_update(client, auth_headers):
    """Batch-updating multiple config items should work."""
    # Ensure defaults exist
    await client.get("/api/v1/app-config", headers=auth_headers)

    response = await client.post(
        "/api/v1/app-config/batch-update",
        headers=auth_headers,
        json=[
            {"config_key": "vector_db_host", "config_value": "192.168.1.100"},
            {"config_key": "vector_db_port", "config_value": "9000"},
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verify the values were updated
    updated = {item["config_key"]: item["config_value"] for item in data}
    assert updated.get("vector_db_host") == "192.168.1.100"
    assert updated.get("vector_db_port") == "9000"


@pytest.mark.asyncio
async def test_reset_vector_connection(client, auth_headers):
    """The vector connection reset endpoint should return a success message."""
    response = await client.post(
        "/api/v1/app-config/reset-vector-connection",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "message" in response.json()
