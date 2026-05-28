"""Tests for /api/v1/templates endpoints — CRUD and duplicate handling."""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _template_payload(**overrides):
    payload = {
        "name": "起诉状模板",
        "type": "complaint",
        "description": "民事起诉状标准模板",
        "structure": {
            "sections": [
                {"name": "当事人信息", "required": True, "fields": ["原告", "被告"]},
                {"name": "诉讼请求", "required": True, "fields": ["请求事项"]},
            ]
        },
        "ai_prompt": "根据以下案件信息生成民事起诉状：{case_facts}",
        "format_rules": {"font": "仿宋", "size": 14},
        "variables": [
            {"name": "plaintiff", "label": "原告", "type": "text", "required": True},
        ],
        "is_public": False,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_template(client, auth_headers):
    resp = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "起诉状模板"
    assert data["type"] == "complaint"
    assert data["is_public"] is False
    assert "id" in data


@pytest.mark.asyncio
async def test_create_template_missing_fields(client, auth_headers):
    resp = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json={"name": "不完整模板"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_templates(client, auth_headers):
    await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="列表模板A"),
    )
    await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="列表模板B", type="answer"),
    )

    resp = await client.get("/api/v1/templates", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert "x-total-count" in resp.headers


@pytest.mark.asyncio
async def test_list_templates_filter_by_type(client, auth_headers):
    await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="筛选模板-起诉状", type="complaint"),
    )
    await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="筛选模板-答辩状", type="answer"),
    )

    resp = await client.get(
        "/api/v1/templates?type=complaint",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(t["type"] == "complaint" for t in data)


@pytest.mark.asyncio
async def test_get_template(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="获取测试模板"),
    )
    template_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/templates/{template_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == template_id
    assert resp.json()["name"] == "获取测试模板"


@pytest.mark.asyncio
async def test_get_template_not_found(client, auth_headers):
    resp = await client.get(
        "/api/v1/templates/999999",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_template(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="更新前模板"),
    )
    template_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/templates/{template_id}",
        headers=auth_headers,
        json={"name": "更新后模板", "description": "更新后的描述"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "更新后模板"
    assert data["description"] == "更新后的描述"


@pytest.mark.asyncio
async def test_update_template_not_owner(client, auth_headers, admin_auth_headers):
    """A user should not be able to update another user's template."""
    create_resp = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="别人的模板"),
    )
    template_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/templates/{template_id}",
        headers=admin_auth_headers,
        json={"name": "试图修改"},
    )
    assert resp.status_code == 404  # Not found or not owner


@pytest.mark.asyncio
async def test_delete_template(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="待删除模板"),
    )
    template_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/templates/{template_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Verify deleted
    get_resp = await client.get(
        f"/api/v1/templates/{template_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_template_not_owner(client, auth_headers, admin_auth_headers):
    create_resp = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="不可删除模板"),
    )
    template_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/templates/{template_id}",
        headers=admin_auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_templates_unauthenticated(client):
    resp = await client.get("/api/v1/templates")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Duplicate handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_duplicate_template(client, auth_headers):
    """Creating two templates with the same name should succeed (no unique constraint)."""
    payload = _template_payload(name="重复模板测试")
    resp1 = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=payload,
    )
    resp2 = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=payload,
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    # They should have different IDs
    assert resp1.json()["id"] != resp2.json()["id"]
