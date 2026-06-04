"""证据AI分析服务"""

import asyncio
import logging
from app.prompts.persona import prompt_with_persona, SYSTEM_EVIDENCE
from app.services.llm_client import create_llm_client, create_llm_client_from_settings
from app.config import get_settings
from app.core.monitoring import timed, LLMTimer, record_llm_call

logger = logging.getLogger(__name__)

# Maximum characters for OCR text sent to LLM to prevent token overflow.
_MAX_OCR_LENGTH = 8000

# Maximum characters for the analysis response (safety cap).
_MAX_RESPONSE_LENGTH = 16000

# Timeout for LLM call in seconds.
_LLM_TIMEOUT = 120

EVIDENCE_ANALYSIS_PROMPT = prompt_with_persona("""请对以下证据材料进行专业分析。

## 证据内容：
{ocr_text}

## 案件背景：
{case_context}

请从以下 **7 个栏目** 简要分析（每栏 **不超过 80 字**，不要写开场白、不要重复案情背景、不要写总结段）：

## 证据类型
（一句：证据种类与形式是否合规）

## 证明力
（一句：对争议事实的证明强弱）

## 关联性
（一句：与本案争议焦点的关联）

## 真实性
（一句：形式与内容是否可信）

## 合法性
（一句：取得方式是否合法）

## 质证要点
（一句：对方可能质疑点及应对）

## 补充建议
（一句：还需补充什么证据）

仅输出以上 7 个二级标题及对应短段落，不要其他章节。""")


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
    # Guard: empty or failed OCR extraction.
    if not ocr_text or not ocr_text.strip():
        return "无法分析：证据文字提取失败或为空"
    if ocr_text.strip().startswith("[") and len(ocr_text.strip()) < 100:
        # Looks like a placeholder error message, e.g. "[OCR failed]"
        return "无法分析：证据文字提取失败或为空"

    # Default case context when not provided.
    effective_context = case_context.strip() if case_context else "未提供案件背景信息"

    settings = get_settings()
    if llm:
        client, model = llm.client, llm.model
        max_tokens = min(llm.max_tokens, 4096)
    elif llm_base_url and llm_api_key:
        client = create_llm_client(llm_base_url, llm_api_key)
        model = llm_model or settings.LLM_MODEL
        max_tokens = 4096
    else:
        client = create_llm_client_from_settings(settings)
        model = llm_model or settings.LLM_MODEL
        max_tokens = 4096

    # Truncate OCR text to prevent token overflow.
    truncated_ocr = ocr_text[:_MAX_OCR_LENGTH]

    try:
        with LLMTimer(model) as timer:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=SYSTEM_EVIDENCE,
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
            # Extract token usage if available
            usage = getattr(response, "usage", None)
            if usage:
                timer.set_tokens(
                    getattr(usage, "input_tokens", 0),
                    getattr(usage, "output_tokens", 0),
                )
        result = response.content[0].text if response.content else "分析完成但无结果"
        # Safety cap on response length.
        if len(result) > _MAX_RESPONSE_LENGTH:
            result = result[:_MAX_RESPONSE_LENGTH] + "\n\n[... 分析结果过长，已截断]"
        return result
    except asyncio.TimeoutError:
        logger.warning("Evidence analysis timed out after %ds", _LLM_TIMEOUT)
        return f"分析超时：LLM 响应超过 {_LLM_TIMEOUT} 秒，请稍后重试"
    except Exception as e:
        logger.warning(f"Evidence analysis failed: {e}")
        return f"分析失败: {e}"
