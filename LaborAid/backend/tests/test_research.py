"""Tests for /api/v1/research endpoints: create, list, get, delete.

Note: The create endpoint calls the LLM, so these tests mock that
behaviour by testing validation and error paths.  Listing, getting,
and deleting are fully exercised.
"""

from unittest.mock import patch, AsyncMock
import pytest


@pytest.mark.asyncio
async def test_list_research_empty(client, auth_headers):
    """Listing research reports when none exist should return an empty list."""
    response = await client.get("/api/v1/research", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "x-total-count" in response.headers


@pytest.mark.asyncio
async def test_get_nonexistent_research(client, auth_headers):
    """Getting a non-existent research report should return 404."""
    response = await client.get("/api/v1/research/999999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_research(client, auth_headers):
    """Deleting a non-existent research report should return 404."""
    response = await client.delete("/api/v1/research/999999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_research_empty_query(client, auth_headers):
    """Creating a research report with an empty query should fail."""
    response = await client.post(
        "/api/v1/research",
        headers=auth_headers,
        json={"query": ""},
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_create_and_list_research(client, auth_headers):
    """Creating a research report with a mocked engine, then listing it."""
    mock_result = {
        "report": "# Mock Research Report\n\nThis is a mocked research result.",
        "sources_used": ["vector_db"],
    }

    with patch(
        "app.services.research.engine.LegalResearchEngine.research",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        create_resp = await client.post(
            "/api/v1/research",
            headers=auth_headers,
            json={"query": "合同违约金的法律规定"},
        )
        assert create_resp.status_code == 200
        data = create_resp.json()
        assert data["query"] == "合同违约金的法律规定"
        assert "id" in data

    # Verify it shows up in list
    list_resp = await client.get("/api/v1/research", headers=auth_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["query"] == "合同违约金的法律规定" for item in items)


@pytest.mark.asyncio
async def test_delete_research(client, auth_headers):
    """Deleting an existing research report should succeed."""
    mock_result = {
        "report": "Mock report",
        "sources_used": [],
    }
    with patch(
        "app.services.research.engine.LegalResearchEngine.research",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        create_resp = await client.post(
            "/api/v1/research",
            headers=auth_headers,
            json={"query": "删除测试查询"},
        )
    report_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/research/{report_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Verify it's gone
    get_resp = await client.get(
        f"/api/v1/research/{report_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_research_unauthenticated(client):
    """Accessing research without auth should return 401."""
    response = await client.get("/api/v1/research")
    assert response.status_code in (401, 403)
