"""Tests for structured intake builder."""

import pytest

from app.services.intake.structured_builder import build_structured_intake


def test_structured_migrant_wage_boss():
    result = build_structured_intake(
        channel_id="migrant-worker",
        scenario_id="wage_boss",
        answers={
            "work_region": "广东省深圳市",
            "industry": "建筑工地",
            "employer_name": "某某劳务公司",
            "wage_amount": "24000",
            "wage_period": "2024年3月—6月",
            "has_iou": "有",
            "still_employed": "是",
        },
    )
    assert result["cause_type"] == "wage_arrears"
    assert result["channel_id"] == "migrant-worker"
    assert result["scenario_id"] == "wage_boss"
    assert result["intake_mode"] == "structured"
    assert result["parties"]["defendant"] == "某某劳务公司"
    assert result["action_plan"]["steps"][0]["step_type"] == "create_case"
    assert len(result["evidence_checklist"]) > 0


def test_structured_missing_required():
    result = build_structured_intake(
        channel_id="migrant-worker",
        scenario_id="wage_boss",
        answers={"work_region": "北京"},
    )
    assert any("用人单位" in m or "欠薪" in m for m in result["missing_info"])


def test_structured_unknown_scenario_raises():
    with pytest.raises(ValueError, match="未找到"):
        build_structured_intake(
            channel_id="migrant-worker",
            scenario_id="nonexistent",
            answers={},
        )
