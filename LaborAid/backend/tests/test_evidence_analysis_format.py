"""证据 AI 分析输出格式。"""

from app.services.evidence.analysis import normalize_evidence_analysis


def test_normalize_evidence_analysis_single_paragraph():
    raw = """## 证明力
    较强。

    ## 关联性
    与欠薪相关。"""
    out = normalize_evidence_analysis(raw)
    assert "##" not in out
    assert len(out) <= 80


def test_normalize_strips_identity_and_greeting():
    raw = "好的，收到您的证据材料。作为劳权智助，我将为您分析。这是一份解除通知，证明单位单方辞退。"
    out = normalize_evidence_analysis(raw)
    assert "劳权智助" not in out
    assert "收到" not in out[:6]
    assert "解除通知" in out


def test_normalize_preserves_error_prefix():
    assert normalize_evidence_analysis("无法分析：OCR 为空").startswith("无法分析")
