"""Tests for /api/v1/cases CRUD endpoints."""

import pytest


@pytest.mark.asyncio
async def test_create_case(client, auth_headers):
    """Creating a case should return 201 with the case data."""
    response = await client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={
            "title": "测试案件",
            "case_type": "civil_litigation",
            "plaintiff": "张三",
            "defendant": "李四",
            "description": "合同纠纷案件",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "测试案件"
    assert data["case_type"] == "civil_litigation"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_case_missing_title(client, auth_headers):
    """Creating a case without a title should fail validation."""
    response = await client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={
            "case_type": "civil_litigation",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_cases(client, auth_headers):
    """Listing cases should return a JSON array with total count header."""
    # Create a case first
    await client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={"title": "列表测试案件", "case_type": "civil_litigation"},
    )

    response = await client.get("/api/v1/cases", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check pagination header
    assert "x-total-count" in response.headers


@pytest.mark.asyncio
async def test_list_cases_unauthenticated(client):
    """Listing cases without auth should return 401."""
    response = await client.get("/api/v1/cases")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_case_by_id(client, auth_headers):
    """Getting a specific case by ID should return the case data."""
    create_resp = await client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={
            "title": "获取测试案件",
            "case_type": "civil_litigation",
            "court": "北京市朝阳区人民法院",
        },
    )
    case_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/cases/{case_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == case_id
    assert data["title"] == "获取测试案件"
    assert data["court"] == "北京市朝阳区人民法院"


@pytest.mark.asyncio
async def test_get_nonexistent_case(client, auth_headers):
    """Getting a non-existent case ID should return 404."""
    response = await client.get("/api/v1/cases/999999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_case(client, auth_headers):
    """Updating a case should reflect the changes."""
    create_resp = await client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={"title": "更新前标题", "case_type": "civil_litigation"},
    )
    case_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/cases/{case_id}",
        headers=auth_headers,
        json={"title": "更新后标题", "status": "closed"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "更新后标题"
    assert data["status"] == "closed"


@pytest.mark.asyncio
async def test_filter_cases_by_status(client, auth_headers):
    """Filtering cases by status should work."""
    await client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={"title": "状态筛选案件", "case_type": "civil_litigation"},
    )

    response = await client.get(
        "/api/v1/cases?status=active",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert all(c["status"] == "active" for c in data)
