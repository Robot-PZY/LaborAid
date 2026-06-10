"""证据AI分析服务"""

import asyncio
import logging
import re

from app.config import get_settings
from app.core.monitoring import timed, LLMTimer, record_llm_call
from app.services.llm_client import create_llm_client, create_llm_client_from_settings

logger = logging.getLogger(__name__)

_MAX_OCR_LENGTH = 8000
_MAX_RESPONSE_LENGTH = 16000
_LLM_TIMEOUT = 120
_MAX_ANALYSIS_CHARS = 80

# 极简 system：禁止身份、免责声明、寒暄
SYSTEM_EVIDENCE_BRIEF = (
    "你是证据摘要助手。只输出一句中文，说明材料内容与证明作用。"
    "禁止：自我介绍、劳权智助/LaborAid、问候语、标题、分点、markdown、法律免责声明。"
)

EVIDENCE_ANALYSIS_PROMPT = """阅读证据与案情，用 **30～50 字** 一句话说明：
1. 这份材料说了什么；
2. 对本案有何证明作用。

## 证据内容
{ocr_text}

## 案件背景
{case_context}

只输出这一句话，不要其他内容。"""

# 需剔除的开场/身份/免责话术
_NOISE_PATTERNS = [
    r"^好的[，,。.!！\s]*",
    r"^收到[您的]*[证据材料与背景说明]*[，,。.!！\s]*",
    r"^作为[^，。]{0,20}[，,]\s*",
    r"^我将[^，。]{0,30}[，,]\s*",
    r"^请注意[：:][^。]*。?\s*",
    r"^\*+\s*",
    r"^\([^)]*仅供参考[^)]*\)\s*",
    r"^（[^）]*仅供参考[^）]*）\s*",
]


def normalize_evidence_analysis(text: str) -> str:
    """压成单段极短摘要，便于证据列表展示。"""
    if not text or not text.strip():
        return text
    raw = text.strip()
    if raw.startswith("无法分析") or raw.startswith("分析失败") or raw.startswith("分析超时"):
        return raw

    kept: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if re.match(r"^#+\s", stripped):
            continue
        if re.match(r"^证据分析[：:]", stripped):
            continue
        if "仅供参考" in stripped and "不构成" in stripped:
            continue
        kept.append(re.sub(r"^#+\s*", "", stripped))
    raw = " ".join(s for s in kept if s)
    raw = re.sub(r"\*\*[^*]*仅供参考[^*]*\*\*", "", raw)
    raw = re.sub(r"\*\*", "", raw)
    raw = re.sub(r"^[-*•]\s+", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

    for pat in _NOISE_PATTERNS:
        raw = re.sub(pat, "", raw, flags=re.IGNORECASE)

    # 全局剔除常见寒暄/免责/标题残留
    raw = re.sub(r"好的，收到[^。]*。?\s*", "", raw)
    raw = re.sub(r"作为[^，。]{0,30}[，,]\s*", "", raw)
    raw = re.sub(r"我将[^。]{0,50}。?\s*", "", raw)
    raw = re.sub(r"[（(]请注意[^）)]*[）)]", "", raw)
    raw = re.sub(r"#{1,6}\s*证据分析[：:][^\s]*\s*", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = re.sub(r"^(AI\s*解读|解读)[：:]\s*", "", raw, flags=re.IGNORECASE)

    if len(raw) > _MAX_ANALYSIS_CHARS:
        raw = raw[: _MAX_ANALYSIS_CHARS - 1].rstrip("，,；; ") + "…"
    return raw


@timed("evidence:analyze", slow_threshold_ms=5000)
async def analyze_evidence(
    ocr_text: str,
    case_context: str = "",
    llm=None,
    llm_base_url=None,
    llm_api_key=None,
    llm_model=None,
) -> str:
    """使用LLM对证据进行专业法律分析。"""
    if not ocr_text or not ocr_text.strip():
        return "无法分析：证据文字提取失败或为空"
    if ocr_text.strip().startswith("[") and len(ocr_text.strip()) < 100:
        return "无法分析：证据文字提取失败或为空"

    effective_context = case_context.strip() if case_context else "未提供案件背景信息"

    settings = get_settings()
    if llm:
        client, model = llm.client, llm.model
        max_tokens = min(llm.max_tokens, 128)
    elif llm_base_url and llm_api_key:
        client = create_llm_client(llm_base_url, llm_api_key)
        model = llm_model or settings.LLM_MODEL
        max_tokens = 128
    else:
        client = create_llm_client_from_settings(settings)
        model = llm_model or settings.LLM_MODEL
        max_tokens = 128

    truncated_ocr = ocr_text[:_MAX_OCR_LENGTH]

    try:
        with LLMTimer(model) as timer:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=SYSTEM_EVIDENCE_BRIEF,
                    messages=[{
                        "role": "user",
                        "content": EVIDENCE_ANALYSIS_PROMPT.format(
                            ocr_text=truncated_ocr,
                            case_context=effective_context,
                        ),
                    }],
                ),
                timeout=_LLM_TIMEOUT,
            )
            usage = getattr(response, "usage", None)
            if usage:
                timer.set_tokens(
                    getattr(usage, "input_tokens", 0),
                    getattr(usage, "output_tokens", 0),
                )
        result = response.content[0].text if response.content else "分析完成但无结果"
        return normalize_evidence_analysis(result)
    except asyncio.TimeoutError:
        logger.warning("Evidence analysis timed out after %ds", _LLM_TIMEOUT)
        return f"分析超时：LLM 响应超过 {_LLM_TIMEOUT} 秒，请稍后重试"
    except (ConnectionError, OSError) as e:
        logger.warning(f"Evidence analysis connection failed: {e}")
        return "分析失败：无法连接到 AI 服务，请检查网络配置或联系管理员"
    except Exception as e:
        logger.warning(f"Evidence analysis failed: {e}")
        return "分析失败，请稍后重试"
