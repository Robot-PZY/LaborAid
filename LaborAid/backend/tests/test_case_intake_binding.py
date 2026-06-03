"""Tests for intake → case ai_snapshot binding."""

import pytest
from httpx import AsyncClient

from app.models.case import Case
from app.services.intake.case_binding import (
    get_case_intake,
    intake_meta_from_session,
    record_intake_on_case,
    resolve_intake_context,
)
from app.services.intake.session_store import analyzer_result_to_session, session_has_plan


def test_intake_meta_from_session():
    session = {
        "causeType": "wage_arrears",
        "causeLabel": "拖欠工资",
        "channelId": "migrant-worker",
        "scenarioId": "wage_boss",
        "intakeMode": "structured",
        "structuredAnswers": {"work_region": "广东省深圳市"},
        "evidenceChecklist": ["工资条", "考勤记录"],
        "summary": "劳务公司欠薪",
    }
    meta = intake_meta_from_session(session)
    assert meta["cause_type"] == "wage_arrears"
    assert meta["work_region"] == "广东省深圳市"
    assert len(meta["evidence_checklist"]) == 2


def test_resolve_intake_prefers_snapshot_over_session():
    case = Case(
        id=1,
        title="测试",
        case_type="administrative_labor",
        owner_id=1,
        status="active",
        ai_snapshot={
            "intake": {
                "cause_type": "wage_arrears",
                "evidence_checklist": ["劳动合同"],
                "summary": "来自快照",
            }
        },
    )
    session = {
        "createdCaseId": 99,
        "causeType": "illegal_termination",
        "evidenceChecklist": ["解除通知"],
    }
    ctx = resolve_intake_context(case, session)
    assert ctx["cause_type"] == "wage_arrears"
    assert ctx["evidence_checklist"] == ["劳动合同"]
    assert ctx["has_intake_plan"] is True


def test_resolve_intake_falls_back_to_linked_session():
    case = Case(
        id=5,
        title="测试",
        case_type="administrative_labor",
        owner_id=1,
        status="active",
    )
    session = {
        "createdCaseId": 5,
        "causeType": "wage_arrears",
        "evidenceChecklist": ["银行流水"],
        "summary": "欠薪案",
    }
    ctx = resolve_intake_context(case, session)
    assert ctx["cause_type"] == "wage_arrears"
    assert ctx["evidence_checklist"] == ["银行流水"]


def test_record_intake_on_case():
    case = Case(
        id=2,
        title="测试",
        case_type="administrative_labor",
        owner_id=1,
        status="active",
    )
    record_intake_on_case(
        case,
        {
            "cause_type": "wage_arrears",
            "channel_id": "migrant-worker",
            "evidence_checklist": ["工资条"],
        },
    )
    intake = get_case_intake(case)
    assert intake["cause_type"] == "wage_arrears"
    assert intake["channel_id"] == "migrant-worker"


@pytest.mark.asyncio
async def test_create_case_binds_intake_snapshot(client: AsyncClient, auth_headers: dict):
    payload = analyzer_result_to_session(
        {
            "cause_type": "wage_arrears",
            "cause_label": "拖欠工资",
            "summary": "公司欠薪三个月",
            "parties": {"plaintiff": "张三", "defendant": "某公司"},
            "missing_info": [],
            "evidence_checklist": ["工资条", "考勤"],
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
            "channel_id": "migrant-worker",
            "scenario_id": "wage_boss",
            "intake_mode": "structured",
            "structured_answers": {"work_region": "广东省深圳市"},
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
                        "prefill": {"title": "欠薪维权"},
                    }
                ],
            },
        },
        input_text="欠我三个月工资",
    )
    assert session_has_plan(payload)

    save = await client.put("/api/v1/intake/session", json={"session": payload}, headers=auth_headers)
    assert save.status_code == 200

    created = await client.post(
        "/api/v1/intake/create-case",
        json={
            "title": "欠薪维权",
            "description": "公司欠薪三个月",
            "plaintiff": "张三",
            "defendant": "某公司",
            "cause_type": "wage_arrears",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    case_id = created.json()["id"]

    readiness = await client.get(f"/api/v1/cases/{case_id}/readiness", headers=auth_headers)
    assert readiness.status_code == 200
    body = readiness.json()
    assert body["cause_type"] == "wage_arrears"
    assert "工资条" in body["intake_checklist"]
    assert body["evidence_suggestions"]

    session_resp = await client.get("/api/v1/intake/session", headers=auth_headers)
    assert session_resp.status_code == 200
    assert session_resp.json()["session"]["createdCaseId"] == case_id
