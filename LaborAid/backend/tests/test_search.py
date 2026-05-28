"""Tests for /api/v1/search endpoints — unified search with different types,
empty queries."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.schemas.search import UnifiedSearchResult, LawSearchResult


# ---------------------------------------------------------------------------
# Search with mocked UnifiedSearchService
# ---------------------------------------------------------------------------

def _mock_search_result(
    query: str = "合同纠纷",
    result_type: str = "all",
    laws: list | None = None,
    cases: list | None = None,
) -> UnifiedSearchResult:
    return UnifiedSearchResult(
        query=query,
        laws=laws or [
            LawSearchResult(
                source="AI法规检索",
                document_id="民法典",
                title="中华人民共和国民法典",
                provision_ref="第469条",
                content="当事人订立合同，可以采用书面形式、口头形式或者其他形式。",
                relevance_score=0.95,
            ),
        ],
        cases=cases or [],
        total=1,
        sources_used=["AI法规检索"],
    )


@pytest.mark.asyncio
async def test_search_all_types(client, auth_headers):
    with patch(
        "app.api.routers.search.UnifiedSearchService"
    ) as MockSvc:
        instance = MockSvc.return_value
        instance.search = AsyncMock(return_value=_mock_search_result())

        resp = await client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={"query": "合同纠纷", "result_type": "all"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "合同纠纷"
    assert len(data["laws"]) >= 1
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_search_law_only(client, auth_headers):
    with patch(
        "app.api.routers.search.UnifiedSearchService"
    ) as MockSvc:
        instance = MockSvc.return_value
        instance.search = AsyncMock(
            return_value=_mock_search_result(result_type="law")
        )

        resp = await client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={"query": "民法典", "result_type": "law"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["laws"]) >= 1


@pytest.mark.asyncio
async def test_search_case_only(client, auth_headers):
    with patch(
        "app.api.routers.search.UnifiedSearchService"
    ) as MockSvc:
        instance = MockSvc.return_value
        instance.search = AsyncMock(
            return_value=UnifiedSearchResult(
                query="合同纠纷案例",
                laws=[],
                cases=[],
                total=0,
                sources_used=[],
            )
        )

        resp = await client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={"query": "合同纠纷案例", "result_type": "case"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_search_empty_query(client, auth_headers):
    resp = await client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "", "result_type": "all"},
    )
    # Pydantic validator catches empty query first (422), or router catches it (400)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_search_whitespace_query(client, auth_headers):
    resp = await client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "   ", "result_type": "all"},
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_search_unauthenticated(client):
    resp = await client.post(
        "/api/v1/search",
        json={"query": "合同法"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_search_with_custom_top_k(client, auth_headers):
    with patch(
        "app.api.routers.search.UnifiedSearchService"
    ) as MockSvc:
        instance = MockSvc.return_value
        instance.search = AsyncMock(
            return_value=_mock_search_result()
        )

        resp = await client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={"query": "合同纠纷", "result_type": "all", "top_k": 5},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_search_invalid_top_k(client, auth_headers):
    resp = await client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "合同法", "top_k": 0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_records_created(client, auth_headers, db_session):
    """Verify that a search creates a SearchRecord in the database."""
    from app.models.search import SearchRecord
    from sqlalchemy import select

    with patch(
        "app.api.routers.search.UnifiedSearchService"
    ) as MockSvc:
        instance = MockSvc.return_value
        instance.search = AsyncMock(return_value=_mock_search_result())

        await client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={"query": "合同纠纷查询"},
        )

    result = await db_session.execute(
        select(SearchRecord).where(SearchRecord.query == "合同纠纷查询")
    )
    record = result.scalar_one_or_none()
    assert record is not None
