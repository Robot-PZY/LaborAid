"""Tests for /api/v1/vector endpoints — stats, ingest, search (mocked ChromaDB)."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_vector_service():
    """Create a mocked VectorStoreService."""
    svc = MagicMock()
    svc._ensure_connection.return_value = True
    svc.get_stats = AsyncMock(return_value={
        "cases_count": 150,
        "statutes_count": 500,
        "knowledge_count": 30,
        "connected": True,
    })
    svc.add_cases = AsyncMock(return_value=3)
    svc.add_statutes = AsyncMock(return_value=2)
    svc.search_cases = AsyncMock(return_value=[
        {"id": "case_1", "content": "案例内容", "metadata": {"title": "测试案例"}, "distance": 0.15},
    ])
    svc.search_statutes = AsyncMock(return_value=[
        {"id": "statute_1", "content": "法条内容", "metadata": {"title": "民法典第469条"}, "distance": 0.10},
    ])
    svc.delete_cases = AsyncMock(return_value=True)
    svc.delete_statutes = AsyncMock(return_value=True)
    return svc


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_vector_stats(client, auth_headers):
    with patch("app.api.routers.vector.get_vector_service") as mock_get:
        mock_get.return_value = _mock_vector_service()

        resp = await client.get(
            "/api/v1/vector/stats",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "cases_count" in data
    assert "statutes_count" in data
    assert "connected" in data


@pytest.mark.asyncio
async def test_get_vector_stats_not_connected(client, auth_headers):
    svc = _mock_vector_service()
    svc.get_stats = AsyncMock(return_value={
        "cases_count": 0,
        "statutes_count": 0,
        "connected": False,
    })

    with patch("app.api.routers.vector.get_vector_service") as mock_get, \
         patch("app.api.routers.vector.vector_stats_cache") as mock_cache:
        mock_get.return_value = svc
        mock_cache.get.return_value = None  # bypass cache

        resp = await client.get(
            "/api/v1/vector/stats",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["connected"] is False


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_cases(client, auth_headers):
    with patch("app.api.routers.vector.get_vector_service") as mock_get:
        mock_get.return_value = _mock_vector_service()

        resp = await client.post(
            "/api/v1/vector/ingest",
            headers=auth_headers,
            json={
                "collection": "cases",
                "items": [
                    {"id": "c1", "title": "案例1", "content": "案例内容1"},
                    {"id": "c2", "title": "案例2", "content": "案例内容2"},
                    {"id": "c3", "title": "案例3", "content": "案例内容3"},
                ],
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingested"] == 3
    assert data["collection"] == "cases"


@pytest.mark.asyncio
async def test_ingest_statutes(client, auth_headers):
    with patch("app.api.routers.vector.get_vector_service") as mock_get:
        mock_get.return_value = _mock_vector_service()

        resp = await client.post(
            "/api/v1/vector/ingest",
            headers=auth_headers,
            json={
                "collection": "statutes",
                "items": [
                    {"id": "s1", "title": "法条1", "content": "法条内容1"},
                    {"id": "s2", "title": "法条2", "content": "法条内容2"},
                ],
            },
        )
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 2


@pytest.mark.asyncio
async def test_ingest_invalid_collection(client, auth_headers):
    with patch("app.api.routers.vector.get_vector_service") as mock_get:
        mock_get.return_value = _mock_vector_service()

        resp = await client.post(
            "/api/v1/vector/ingest",
            headers=auth_headers,
            json={
                "collection": "invalid",
                "items": [{"id": "x1", "title": "x", "content": "x"}],
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingest_empty_items(client, auth_headers):
    with patch("app.api.routers.vector.get_vector_service") as mock_get:
        mock_get.return_value = _mock_vector_service()

        resp = await client.post(
            "/api/v1/vector/ingest",
            headers=auth_headers,
            json={
                "collection": "cases",
                "items": [],
            },
        )
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 3  # mocked returns 3


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_vector_all(client, auth_headers):
    with patch("app.api.routers.vector.get_vector_service") as mock_get:
        mock_get.return_value = _mock_vector_service()

        resp = await client.post(
            "/api/v1/vector/search",
            headers=auth_headers,
            json={"query": "合同纠纷", "collection": "all"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "cases" in data
    assert "statutes" in data
    assert data["query"] == "合同纠纷"


@pytest.mark.asyncio
async def test_search_vector_cases_only(client, auth_headers):
    with patch("app.api.routers.vector.get_vector_service") as mock_get:
        mock_get.return_value = _mock_vector_service()

        resp = await client.post(
            "/api/v1/vector/search",
            headers=auth_headers,
            json={"query": "合同纠纷", "collection": "cases"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["cases"]) >= 1
    assert len(data["statutes"]) == 0


@pytest.mark.asyncio
async def test_search_vector_empty_query(client, auth_headers):
    resp = await client.post(
        "/api/v1/vector/search",
        headers=auth_headers,
        json={"query": "", "collection": "all"},
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_search_vector_unauthenticated(client):
    resp = await client.post(
        "/api/v1/vector/search",
        json={"query": "合同法"},
    )
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_vector_item(client, auth_headers):
    with patch("app.api.routers.vector.get_vector_service") as mock_get:
        mock_get.return_value = _mock_vector_service()

        resp = await client.delete(
            "/api/v1/vector/cases/case_1",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


@pytest.mark.asyncio
async def test_delete_vector_invalid_collection(client, auth_headers):
    with patch("app.api.routers.vector.get_vector_service") as mock_get:
        mock_get.return_value = _mock_vector_service()

        resp = await client.delete(
            "/api/v1/vector/invalid/item_1",
            headers=auth_headers,
        )
    assert resp.status_code == 400
