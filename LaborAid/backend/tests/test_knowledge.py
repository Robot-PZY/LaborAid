"""Tests for /api/v1/knowledge endpoints: CRUD, stats, search, batch delete."""

import pytest


@pytest.mark.asyncio
async def test_list_knowledge_empty(client, auth_headers):
    """Listing knowledge items when none exist should return an empty list."""
    response = await client.get("/api/v1/knowledge", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "x-total-count" in response.headers


@pytest.mark.asyncio
async def test_create_knowledge(client, auth_headers):
    """Creating a knowledge item should succeed."""
    response = await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "title": "测试知识",
            "content": "这是一条测试知识条目的内容。",
            "source": "test",
            "tags": ["测试"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "测试知识"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_knowledge_empty_title(client, auth_headers):
    """Creating a knowledge item with an empty title should fail."""
    response = await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={"title": "", "content": "有内容"},
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_knowledge_stats(client, auth_headers):
    """Knowledge stats should return total count and tags."""
    # Create an item first
    await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "title": "统计测试",
            "content": "用于统计的内容",
            "tags": ["统计"],
        },
    )

    response = await client.get("/api/v1/knowledge/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "tags" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_delete_knowledge(client, auth_headers):
    """Deleting a knowledge item should succeed."""
    create_resp = await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={"title": "待删除", "content": "待删除内容"},
    )
    item_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/knowledge/{item_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Verify it is gone
    get_resp = await client.get(
        f"/api/v1/knowledge/{item_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_knowledge_search(client, auth_headers):
    """Searching knowledge should return matching items."""
    await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={"title": "合同法要点", "content": "合同法的基本原则是平等自愿"},
    )

    response = await client.get(
        "/api/v1/knowledge/search/results?q=合同法",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_knowledge_unauthenticated(client):
    """Accessing knowledge without auth should return 401."""
    response = await client.get("/api/v1/knowledge")
    assert response.status_code in (401, 403)
