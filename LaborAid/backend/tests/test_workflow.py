"""案件工作流 FSM 测试。"""

from app.models.case import Case
from app.schemas.case import CaseReadinessOut
from app.services.orchestrator.case_context import CaseWorkContext
from app.services.workflow.case_workflow import build_case_workflow_payload


def _case(**kwargs) -> Case:
    c = Case(id=1, title="测试", case_type="administrative_labor", status="active", owner_id=1)
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def _readiness(**kwargs) -> CaseReadinessOut:
    d = dict(
        case_id=1,
        readiness_score=30,
        readiness_level="low",
        summary="",
        strengths=[],
        missing_items=[],
        next_actions=[],
        cause_type="wage_arrears",
        cause_label="拖欠工资",
        evidence_suggestions=[],
        docgen_ready=False,
        docgen_recommendation="not_ready",
        docgen_blockers=[],
    )
    d.update(kwargs)
    return CaseReadinessOut(**d)


def test_workflow_starts_at_case_when_empty():
    ctx = CaseWorkContext(
        case=_case(description=""),
        documents_count=0,
        evidence_count=0,
        research_reports_count=0,
        intake_cause_type=None,
        channel_id=None,
        scenario_id=None,
        intake_summary=None,
        has_intake_plan=False,
        readiness=_readiness(),
    )
    out = build_case_workflow_payload(ctx)
    assert out["current_stage"] == "case"
    assert out["steps"][0]["status"] == "active"
    assert out["progress"] == 0


def test_workflow_materials_after_case_ready():
    ctx = CaseWorkContext(
        case=_case(description="2024年1月起公司拖欠工资共3万元，有聊天记录"),
        documents_count=0,
        evidence_count=0,
        research_reports_count=0,
        intake_cause_type="wage_arrears",
        channel_id=None,
        scenario_id=None,
        intake_summary=None,
        has_intake_plan=True,
        readiness=_readiness(),
    )
    out = build_case_workflow_payload(ctx)
    assert out["current_stage"] == "materials"
    assert out["steps"][0]["status"] == "done"
    assert out["steps"][1]["status"] == "active"
