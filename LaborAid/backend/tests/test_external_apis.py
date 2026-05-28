"""Tests for /api/v1/external-apis CRUD + presets."""

import json

import pytest


@pytest.mark.asyncio
async def test_list_external_apis_empty(client, auth_headers):
    """Listing external APIs when none exist should return an empty list."""
    response = await client.get("/api/v1/external-apis", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_external_api(client, auth_headers):
    """Creating an external API config should succeed."""
    response = await client.post(
        "/api/v1/external-apis",
        headers=auth_headers,
        json={
            "name": "测试API",
            "base_url": "https://api.example.com",
            "auth_type": "bearer",
            "search_law_path": "/search",
            "search_law_method": "GET",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "测试API"
    assert "id" in data
    assert data["auth_token_masked"]  # token should be masked


@pytest.mark.asyncio
async def test_create_external_api_invalid_json(client, auth_headers):
    """Creating an external API with invalid JSON fields should fail."""
    response = await client.post(
        "/api/v1/external-apis",
        headers=auth_headers,
        json={
            "name": "坏API",
            "base_url": "https://api.example.com",
            "custom_headers": "not-valid-json",
        },
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_update_external_api(client, auth_headers):
    """Updating an external API config should reflect the changes."""
    create_resp = await client.post(
        "/api/v1/external-apis",
        headers=auth_headers,
        json={
            "name": "待更新API",
            "base_url": "https://api.example.com",
        },
    )
    api_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/external-apis/{api_id}",
        headers=auth_headers,
        json={"name": "已更新API"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "已更新API"


@pytest.mark.asyncio
async def test_delete_external_api(client, auth_headers):
    """Deleting an external API should succeed."""
    create_resp = await client.post(
        "/api/v1/external-apis",
        headers=auth_headers,
        json={
            "name": "待删除API",
            "base_url": "https://api.example.com",
        },
    )
    api_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/external-apis/{api_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Verify it is gone
    list_resp = await client.get("/api/v1/external-apis", headers=auth_headers)
    ids = [item["id"] for item in list_resp.json()]
    assert api_id not in ids


@pytest.mark.asyncio
async def test_delete_nonexistent_external_api(client, auth_headers):
    """Deleting a non-existent external API should return 404."""
    response = await client.delete(
        "/api/v1/external-apis/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_presets(client, auth_headers):
    """The presets endpoint should return a list of predefined API templates."""
    response = await client.get(
        "/api/v1/external-apis/presets",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Each preset should have required fields
    for preset in data:
        assert "key" in preset
        assert "name" in preset
        assert "base_url" in preset


@pytest.mark.asyncio
async def test_toggle_external_api(client, auth_headers):
    """Toggling an external API should flip its enabled status."""
    create_resp = await client.post(
        "/api/v1/external-apis",
        headers=auth_headers,
        json={
            "name": "切换API",
            "base_url": "https://api.example.com",
            "is_enabled": True,
        },
    )
    api_id = create_resp.json()["id"]
    initial_enabled = create_resp.json()["is_enabled"]

    response = await client.post(
        f"/api/v1/external-apis/{api_id}/toggle",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_enabled"] != initial_enabled
