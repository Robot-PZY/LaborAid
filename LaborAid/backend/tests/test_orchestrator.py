"""维权编排 Agent 规则测试。"""

from app.models.case import Case
from app.schemas.case import CaseReadinessOut
from app.services.orchestrator.case_context import CaseWorkContext
from app.services.orchestrator.next_step import compute_case_next_step


def _minimal_case(**kwargs) -> Case:
    c = Case(
        id=1,
        title="测试案件",
        case_type="administrative_labor",
        status="active",
        owner_id=1,
    )
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def _readiness(**kwargs) -> CaseReadinessOut:
    defaults = dict(
        case_id=1,
        readiness_score=30,
        readiness_level="low",
        summary="测试",
        strengths=[],
        missing_items=[],
        next_actions=[],
        cause_type="wage_arrears",
        cause_label="拖欠工资",
        evidence_suggestions=[],
        docgen_ready=False,
        docgen_recommendation="not_ready",
        docgen_blockers=["尚无证据材料"],
    )
    defaults.update(kwargs)
    return CaseReadinessOut(**defaults)


def test_next_step_guidance_when_empty():
    ctx = CaseWorkContext(
        case=_minimal_case(description=""),
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
    out = compute_case_next_step(ctx)
    assert out["agent_id"] == "guidance"
    assert out["pipeline_stage"] == "path"


def test_next_step_evidence_when_no_files():
    ctx = CaseWorkContext(
        case=_minimal_case(description="2024年1月起公司拖欠工资共3万元"),
        documents_count=0,
        evidence_count=0,
        research_reports_count=0,
        intake_cause_type="wage_arrears",
        channel_id=None,
        scenario_id=None,
        intake_summary="拖欠工资",
        has_intake_plan=True,
        readiness=_readiness(readiness_score=35),
    )
    out = compute_case_next_step(ctx)
    assert out["agent_id"] == "evidence"
    assert out["pipeline_stage"] == "evidence"


def test_next_step_docgen_when_ready():
    ctx = CaseWorkContext(
        case=_minimal_case(description="拖欠工资三个月，有聊天记录和流水"),
        documents_count=0,
        evidence_count=2,
        research_reports_count=0,
        intake_cause_type="wage_arrears",
        channel_id=None,
        scenario_id=None,
        intake_summary=None,
        has_intake_plan=True,
        readiness=_readiness(
            readiness_score=55,
            combined_score=75,
            docgen_ready=True,
            docgen_recommendation="ready",
            docgen_blockers=[],
        ),
    )
    out = compute_case_next_step(ctx)
    assert out["agent_id"] == "docgen"
    assert out["pipeline_stage"] == "documents"


def test_next_step_docgen_blocked_when_low_score():
    ctx = CaseWorkContext(
        case=_minimal_case(description="拖欠工资三个月"),
        documents_count=0,
        evidence_count=1,
        research_reports_count=0,
        intake_cause_type="wage_arrears",
        channel_id=None,
        scenario_id=None,
        intake_summary=None,
        has_intake_plan=True,
        readiness=_readiness(
            readiness_score=35,
            combined_score=35,
            docgen_ready=False,
            docgen_recommendation="not_ready",
            docgen_blockers=["仍缺 2 项关键证据"],
        ),
    )
    out = compute_case_next_step(ctx)
    assert out["agent_id"] != "docgen"


def test_next_step_docgen_caution_mid_score():
    ctx = CaseWorkContext(
        case=_minimal_case(description="拖欠工资三个月，有聊天记录"),
        documents_count=0,
        evidence_count=1,
        research_reports_count=0,
        intake_cause_type="wage_arrears",
        channel_id=None,
        scenario_id=None,
        intake_summary=None,
        has_intake_plan=True,
        readiness=_readiness(
            readiness_score=55,
            combined_score=59,
            docgen_ready=True,
            docgen_recommendation="caution",
            docgen_blockers=["仍缺 1 项关键证据"],
        ),
    )
    out = compute_case_next_step(ctx)
    # caution 档 docgen 仍然可以 active
    assert out["agent_id"] == "docgen"
    assert out["pipeline_stage"] == "documents"


def test_agents_list_includes_pipeline():
    from app.services.agents import build_agents_list_payload

    ctx = CaseWorkContext(
        case=_minimal_case(description=""),
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
    payload = build_agents_list_payload(ctx)
    ids = [a["agent_id"] for a in payload["agents"]]
    assert payload["active_agent_id"] == "guidance"
    assert ids == ["guidance", "evidence", "docgen", "research", "records"]
