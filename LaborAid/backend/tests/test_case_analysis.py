"""案情分析（案件材料汇总报告）与案件删除。"""

import pytest


@pytest.mark.asyncio
async def test_case_materials_not_found(client, auth_headers):
    r = await client.get("/api/v1/cases/999999/materials", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_case_not_found(client, auth_headers):
    r = await client.delete("/api/v1/cases/999999", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_case_report_requires_materials(client, auth_headers, test_user, db_session):
    from app.models.case import Case

    case = Case(
        title="空材料案件",
        case_type="administrative_labor",
        description="",
        owner_id=test_user.id,
        status="active",
    )
    db_session.add(case)
    await db_session.flush()
    await db_session.refresh(case)

    r = await client.post(
        f"/api/v1/cases/{case.id}/case-report",
        headers=auth_headers,
        json={},
    )
    assert r.status_code == 400
