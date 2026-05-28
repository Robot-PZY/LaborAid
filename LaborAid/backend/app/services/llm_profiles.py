"""LLM 配置角色分类（文本主模型 / 视觉 OCR）。"""

from __future__ import annotations


def is_vision_profile(name: str, model_name: str) -> bool:
    name_l = (name or "").lower()
    model_l = (model_name or "").lower()
    return (
        "视觉" in (name or "")
        or "ocr" in name_l
        or "文字识别" in (name or "")
        or "-vl" in model_l
        or "vl-" in model_l
        or "vl_" in model_l
        or "4v" in model_l
        or "vision" in model_l
        or "qwen-vl" in model_l
    )


def is_ocr_profile(name: str, model_name: str) -> bool:
    if not is_vision_profile(name, model_name):
        return False
    name_l = (name or "").lower()
    model_l = (model_name or "").lower()
    return "ocr" in name_l or "ocr" in model_l or "文字识别" in (name or "")


def profile_role(name: str, model_name: str, *, is_default: bool) -> str:
    if is_ocr_profile(name, model_name):
        return "vision_ocr"
    if is_vision_profile(name, model_name):
        return "vision"
    if is_default:
        return "text_primary"
    return "other"


PROFILE_ROLE_LABELS = {
    "text_primary": "主模型（文书/对话）",
    "vision_ocr": "视觉 OCR（识图/PDF）",
    "vision": "视觉理解",
    "other": "备用",
}
