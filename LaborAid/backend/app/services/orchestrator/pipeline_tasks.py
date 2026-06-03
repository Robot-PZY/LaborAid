"""分阶段子任务清单 — 供前端展示流水线进度。"""

from __future__ import annotations

from typing import Any

from app.services.orchestrator.case_context import CaseWorkContext
from app.services.orchestrator.next_step import _build_route


def build_pipeline_tasks(ctx: CaseWorkContext, pipeline_stage: str) -> list[dict[str, Any]]:
    cid = ctx.case.id
    r = ctx.readiness

    if pipeline_stage == "evidence":
        upload_done = ctx.evidence_count > 0
        return [
            {
                "id": "upload",
                "label": "上传关键证据",
                "status": "done" if upload_done else "active",
                "route": _build_route("evidence", cid),
            },
            {
                "id": "chain",
                "label": "运行证据链分析",
                "status": "done" if (r.chain_completeness_score or 0) >= 50 else ("active" if upload_done else "pending"),
                "route": _build_route("evidence", cid),
                "hint": "在证链页对本案执行「证据链分析」",
            },
            {
                "id": "checklist",
                "label": "对照案由清单查漏",
                "status": "active" if upload_done else "pending",
                "route": _build_route("evidence", cid),
            },
        ]

    if pipeline_stage == "documents":
        has_desc = bool((ctx.case.description or "").strip())
        return [
            {
                "id": "review",
                "label": "核对案情与证据",
                "status": "done" if has_desc and ctx.evidence_count > 0 else "active",
                "route": _build_route("cases", cid),
            },
            {
                "id": "research",
                "label": "可选：检索法条争点",
                "status": "done" if ctx.research_reports_count > 0 else "pending",
                "route": _build_route("research", cid),
                "optional": True,
            },
            {
                "id": "docgen",
                "label": "生成仲裁申请书等",
                "status": "done" if ctx.documents_count > 0 else ("active" if r.docgen_ready else "pending"),
                "route": _build_route(
                    "docgen",
                    cid,
                    {"docType": "application", "causeType": r.cause_type or "wage_arrears"},
                ),
            },
            {
                "id": "verify",
                "label": "人工核对后提交",
                "status": "pending" if ctx.documents_count == 0 else "active",
                "route": f"/documents?caseId={cid}" if ctx.documents_count else _build_route("docgen", cid),
                "hint": "生成后请核对事实、请求事项与证据对应关系",
            },
        ]

    if pipeline_stage == "research":
        return [
            {
                "id": "materials",
                "label": "确认材料已齐",
                "status": "done" if ctx.evidence_count > 0 and ctx.documents_count > 0 else "active",
                "route": _build_route("cases", cid),
            },
            {
                "id": "report",
                "label": "生成案情总结报告",
                "status": "done" if ctx.research_reports_count > 0 else "active",
                "route": _build_route("research", cid),
            },
        ]

    return []
