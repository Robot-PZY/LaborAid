"""Derive OCR / text-extraction status for API responses."""

from __future__ import annotations

OcrStatus = str  # pending | processing | success | failed


def classify_ocr_result(
    text: str | None,
    *,
    has_file: bool = False,
    force_processing: bool = False,
) -> tuple[OcrStatus, str | None]:
    """Classify extracted text into user-facing OCR status."""
    if force_processing:
        return "processing", "正在识别文字…"
    if not has_file:
        return "pending", None
    if text is None or not str(text).strip():
        return "failed", "未识别到文字，请上传更清晰的文件后重试"
    raw = str(text).strip()
    if raw.startswith("[") and raw.endswith("]"):
        return "failed", "文字识别失败，请上传更清晰的文件后重试"
    if "需要OCR" in raw or "需要配置" in raw or "提取失败" in raw or raw.startswith("[文件"):
        return "failed", "文字识别失败，请上传更清晰的文件后重试"
    if len(raw) < 10:
        return "failed", "识别文字过短，可能为空白页或扫描不清晰"
    return "success", f"已识别约 {len(raw):,} 字"


def apply_ocr_fields(
    payload: dict,
    text: str | None,
    *,
    has_file: bool,
    force_processing: bool = False,
) -> dict:
    status, message = classify_ocr_result(
        text, has_file=has_file, force_processing=force_processing
    )
    payload["ocr_status"] = status
    payload["ocr_message"] = message
    return payload
