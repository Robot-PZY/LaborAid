"""维权咨询方案持久化"""

import pytest
from httpx import AsyncClient

from app.services.intake.session_store import analyzer_result_to_session, session_has_plan


@pytest.mark.asyncio
async def test_intake_session_crud(client: AsyncClient, auth_headers: dict):
    payload = analyzer_result_to_session(
        {
            "cause_type": "wage_arrears",
            "cause_label": "拖欠工资",
            "summary": "公司欠薪三个月",
            "parties": {"plaintiff": "张三", "defendant": "某公司"},
            "missing_info": [],
            "evidence_checklist": ["工资条"],
            "recommended_tools": [
                {
                    "agent_id": "evidence",
                    "priority": 1,
                    "reason": "整理证据",
                    "action": "navigate",
                    "prefill": {},
                }
            ],
            "official_links": [],
            "credibility": {"score": 0.8, "needs_human_review": False, "reason": "ok"},
            "search_query": "拖欠工资",
            "action_plan": {
                "plan_id": "wage_arrears",
                "title": "维权安排",
                "current_step": 1,
                "steps": [
                    {
                        "step": 1,
                        "step_type": "create_case",
                        "label": "建案",
                        "reason": "先建案",
                        "action": "create_case",
                        "prefill": {},
                    }
                ],
            },
        },
        input_text="欠我三个月工资",
    )
    assert session_has_plan(payload)

    r = await client.put("/api/v1/intake/session", json={"session": payload}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["session"]["causeLabel"] == "拖欠工资"

    r2 = await client.get("/api/v1/intake/session", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["session"]["summary"] == "公司欠薪三个月"

    r3 = await client.delete("/api/v1/intake/session", headers=auth_headers)
    assert r3.status_code == 200
    assert r3.json()["deleted"] is True

    r4 = await client.get("/api/v1/intake/session", headers=auth_headers)
    assert r4.status_code == 200
    assert r4.json() is None
