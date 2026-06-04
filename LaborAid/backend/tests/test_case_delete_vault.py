"""删除案件时同步清理材料库。"""

import pytest
from sqlalchemy import select

from app.models.case import Case
from app.models.user_material import UserMaterial


@pytest.mark.asyncio
async def test_delete_case_soft_deletes_vault_materials(client, auth_headers, test_user, db_session):
    case = Case(
        title="待删案件",
        case_type="administrative_labor",
        description="测试",
        owner_id=test_user.id,
        status="active",
    )
    db_session.add(case)
    await db_session.flush()
    await db_session.refresh(case)

    mat = UserMaterial(
        user_id=test_user.id,
        case_id=case.id,
        source="manual",
        title="测试材料",
        original_filename="test.txt",
        stored_path=f"vault/{test_user.id}/test.txt",
        size_bytes=10,
        stage="preparation",
    )
    db_session.add(mat)
    await db_session.commit()

    r = await client.delete(f"/api/v1/cases/{case.id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json().get("vault_materials_removed", 0) >= 1

    row = await db_session.get(UserMaterial, mat.id)
    assert row is not None
    assert row.deleted_at is not None

    still_active = await db_session.execute(
        select(UserMaterial).where(
            UserMaterial.user_id == test_user.id,
            UserMaterial.case_id == case.id,
            UserMaterial.deleted_at.is_(None),
        )
    )
    assert still_active.scalars().first() is None
