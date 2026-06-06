"""LCEL (LangChain Expression Language) 链封装 -- 可组合的 LLM Pipeline。

第二阶段目标：
- 使用 Runnable 原语构建可组合的 LLM 链
- 支持 Callback 统计（token 用量、每步耗时）
- 为 research 和 docgen 提供标准化的 Pipeline 接口
"""

import json
import logging
import re
import time
from typing import Any, Callable

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, RunnableSequence

logger = logging.getLogger(__name__)


# ── Callback: 统计 token 和耗时 ──────────────────────────────────────────────

class PipelineStatsCallback(BaseCallbackHandler):
    """统计 Pipeline 执行的 token 用量和每步耗时。"""

    def __init__(self):
        self.stats = {
            "steps": [],
            "total_tokens": 0,
            "total_time_ms": 0,
        }
        self._step_start_times: dict[str, float] = {}

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs):
        step_name = serialized.get("name", "unknown")
        self._step_start_times[step_name] = time.monotonic()
        logger.debug("Chain start: %s", step_name)

    def on_chain_end(self, outputs: dict[str, Any], **kwargs):
        step_name = kwargs.get("run_id", "unknown")
        start_time = self._step_start_times.pop(step_name, None)
        if start_time:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            self.stats["steps"].append({
                "step": step_name,
                "elapsed_ms": round(elapsed_ms, 2),
            })
            self.stats["total_time_ms"] += elapsed_ms

    def on_llm_end(self, response: Any, **kwargs):
        # 尝试从 response 提取 token 信息
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            tokens = usage.get("total_tokens", 0)
            self.stats["total_tokens"] += tokens


# ── 工具函数：JSON 提取与容错 ─────────────────────────────────────────────────

def extract_json_from_text(text: str) -> dict | list | None:
    """从 LLM 输出中提取 JSON（支持代码块和混合文本）。"""
    if not text or not text.strip():
        return None

    # 去除代码块标记
    text = re.sub(r'^```(?:json)?\n?', '', text.strip())
    text = re.sub(r'\n?```$', '', text.strip())

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试从文本中提取 JSON 对象或数组
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    return None


# ── LLM 调用包装器 ───────────────────────────────────────────────────────────

def make_llm_call(
    client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
    stats_callback: PipelineStatsCallback | None = None,
) -> Runnable[dict, str]:
    """创建 LLM 调用 Runnable。

    Args:
        client: LLM 客户端（OpenAI 或 Anthropic 兼容）
        model: 模型名称
        system_prompt: 系统提示词
        user_prompt: 用户提示词（可包含 {variable} 占位符）
        max_tokens: 最大输出 token 数
        stats_callback: 可选的统计回调，用于记录 token 和耗时

    Returns:
        Runnable[dict, str] - 输入 dict，输出 str
    """

    async def _call(inputs: dict) -> str:
        # 格式化 user_prompt
        formatted_prompt = user_prompt.format(**inputs)

        start_time = time.monotonic()
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": formatted_prompt}],
            )
            text = response.content[0].text if response.content else ""
            
            # 记录统计信息
            if stats_callback:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                stats_callback.stats["steps"].append({
                    "step": "llm_call",
                    "elapsed_ms": round(elapsed_ms, 2),
                    "model": model,
                })
                stats_callback.stats["total_time_ms"] += elapsed_ms
                
                # 估算 token 用量（基于字符数）
                input_tokens = len(formatted_prompt) // 4  # 粗略估算
                output_tokens = len(text) // 4
                stats_callback.stats["total_tokens"] += input_tokens + output_tokens
            
            return text
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return ""

    return RunnableLambda(_call).with_config(run_name="llm_call")


# ── Research Pipeline ────────────────────────────────────────────────────────

def build_query_decomposition_chain(
    client,
    model: str,
    stats_callback: PipelineStatsCallback | None = None,
) -> Runnable[dict, dict]:
    """构建查询分解链 -- 将用户查询分解为结构化搜索要素。

    Input: {"query": str}
    Output: {"legal_issues": [...], "sub_queries": [...], ...}
    """

    system_prompt = "你是法律检索分析专家。请严格按照JSON格式返回查询分解结果。"

    user_prompt = """请分析以下法律研究问题，将其分解为结构化的搜索要素。

研究问题：{query}

请返回严格的JSON格式（不要返回其他内容）：
```json
{{
  "legal_issues": ["涉及的法律问题1", "涉及的法律问题2"],
  "factual_elements": ["需要验证的事实要素1", "需要验证的事实要素要素2"],
  "procedural_requirements": ["程序性要求1", "程序性要求2"],
  "key_legal_terms": ["关键法律术语1", "关键法律术语2"],
  "sub_queries": ["分解后的子查询1（用于分别检索）", "分解后的子查询2", "分解后的子查询3"],
  "applicable_law_areas": ["涉及的法律领域1", "涉及的法律领域2"]
}}
```

要求：
1. legal_issues: 识别涉及的核心法律争议点
2. factual_elements: 识别需要查明的事实要素
3. procedural_requirements: 识别程序性要求（时效、管辖等）
4. key_legal_terms: 提取需要精确检索的法律术语
5. sub_queries: 生成3-5个针对性子查询，每个覆盖不同角度
6. applicable_law_areas: 识别涉及的法律领域"""

    async def _decompose(inputs: dict) -> dict:
        fallback = {
            "legal_issues": [inputs.get("query", "")],
            "factual_elements": [],
            "procedural_requirements": [],
            "key_legal_terms": [],
            "sub_queries": [inputs.get("query", "")],
            "applicable_law_areas": [],
        }

        llm_chain = make_llm_call(client, model, system_prompt, user_prompt, max_tokens=2000, stats_callback=stats_callback)
        text = await llm_chain.ainvoke(inputs)

        result = extract_json_from_text(text)
        if not result or not isinstance(result, dict):
            return fallback

        # 确保必要字段存在
        for key in ("sub_queries", "legal_issues"):
            if key not in result or not isinstance(result[key], list):
                result[key] = fallback.get(key, [])

        return result

    return RunnableLambda(_decompose).with_config(run_name="query_decomposition")


def build_research_synthesis_chain(
    client,
    model: str,
    system_prompt: str,
    user_prompt_template: str,
    stats_callback: PipelineStatsCallback | None = None,
) -> Runnable[dict, str]:
    """构建研究报告合成链。

    Input: {
        "query": str,
        "query_decomposition": str,
        "local_cases": str,
        "local_statutes": str,
        "ai_knowledge": str,
        "external_api_results": str,
        "web_search_results": str,
        "knowledge_base_results": str,
    }
    Output: str (研究报告)
    """

    async def _synthesize(inputs: dict) -> str:
        llm_chain = make_llm_call(
            client,
            model,
            system_prompt,
            user_prompt_template,
            max_tokens=8192,
            stats_callback=stats_callback,
        )
        return await llm_chain.ainvoke(inputs)

    return RunnableLambda(_synthesize).with_config(run_name="research_synthesis")


def build_deep_dive_analysis_chain(
    client,
    model: str,
    stats_callback: PipelineStatsCallback | None = None,
) -> Runnable[dict, dict]:
    """构建深度分析链 -- 识别报告中的不足并建议补充检索。

    Input: {"query": str, "initial_report": str}
    Output: {"gaps": [...], "follow_up_queries": [...], ...}
    """

    system_prompt = "你是法律研究质量审核专家。请严格按JSON格式返回审核结果。"

    user_prompt = """你是一位法律研究质量审核专家。请审阅以下初步研究报告，识别其中的不足之处。

## 研究课题：{query}

## 初步报告：
{initial_report}

请分析以下方面并返回JSON格式：
```json
{{
  "gaps": [
    {{
      "area": "缺失领域（如：某个法律问题未被充分分析）",
      "description": "具体说明缺失了什么",
      "suggested_query": "建议的补充搜索查询"
    }}
  ],
  "weak_citations": ["引用不够具体或可能不准确的法条引用"],
  "missing_perspectives": ["缺少的分析视角"],
  "follow_up_queries": ["建议的补充检索查询1", "建议的补充检索查询2"]
}}
```

要求：
1. 至少识别2-3个需要补充的领域
2. 为每个缺失领域提供具体的补充搜索建议
3. 检查是否有法条引用过于笼统（如只提法律名未提具体条文号）
4. 检查是否缺少某一方当事人视角的分析"""

    async def _analyze(inputs: dict) -> dict:
        llm_chain = make_llm_call(client, model, system_prompt, user_prompt, max_tokens=2000, stats_callback=stats_callback)
        text = await llm_chain.ainvoke(inputs)

        result = extract_json_from_text(text)
        if not result or not isinstance(result, dict):
            return {"gaps": [], "follow_up_queries": []}

        return result

    return RunnableLambda(_analyze).with_config(run_name="deep_dive_analysis")


# ── Docgen Pipeline ──────────────────────────────────────────────────────────

def build_case_parsing_chain(
    client,
    model: str,
    system_prompt: str,
    user_prompt_template: str,
    stats_callback: PipelineStatsCallback | None = None,
) -> Runnable[dict, dict]:
    """构建案件解析链 -- 从案件事实描述中提取结构化信息。

    Input: {"case_facts": str}
    Output: {"parties": {...}, "cause_of_action": str, "key_facts": [...], ...}
    """

    async def _parse(inputs: dict) -> dict:
        llm_chain = make_llm_call(client, model, system_prompt, user_prompt_template, max_tokens=2000, stats_callback=stats_callback)
        text = await llm_chain.ainvoke(inputs)

        result = extract_json_from_text(text)
        if not result or not isinstance(result, dict):
            return {
                "parties": {"plaintiff": {}, "defendant": {}},
                "cause_of_action": "",
                "key_facts": [],
                "dispute_focus": [],
            }

        return result

    return RunnableLambda(_parse).with_config(run_name="case_parsing")


def build_document_generation_chain(
    client,
    model: str,
    system_prompt: str,
    user_prompt_template: str,
    stats_callback: PipelineStatsCallback | None = None,
) -> Runnable[dict, str]:
    """构建文书生成链。

    Input: {
        "case_facts": str,
        "parsed_case": dict,
        "combined_laws": str,
        "combined_cases": str,
        "doc_type_name": str,
        "template_structure": str,
        ...
    }
    Output: str (生成的文书内容)
    """

    async def _generate(inputs: dict) -> str:
        llm_chain = make_llm_call(
            client,
            model,
            system_prompt,
            user_prompt_template,
            max_tokens=8192,
            stats_callback=stats_callback,
        )
        return await llm_chain.ainvoke(inputs)

    return RunnableLambda(_generate).with_config(run_name="document_generation")


def build_quality_review_chain(
    client,
    model: str,
    system_prompt: str,
    user_prompt_template: str,
    stats_callback: PipelineStatsCallback | None = None,
) -> Runnable[dict, dict]:
    """构建质量审查链 -- 检查生成文书的质量问题。

    Input: {"document_content": str, "case_facts": str}
    Output: {"issues": [...], "score": float, "suggestions": [...]}
    """

    async def _review(inputs: dict) -> dict:
        llm_chain = make_llm_call(client, model, system_prompt, user_prompt_template, max_tokens=2000, stats_callback=stats_callback)
        text = await llm_chain.ainvoke(inputs)

        result = extract_json_from_text(text)
        if not result or not isinstance(result, dict):
            return {"issues": [], "score": 0.5, "suggestions": []}

        return result

    return RunnableLambda(_review).with_config(run_name="quality_review")


# ── Pipeline 构建器 ──────────────────────────────────────────────────────────

def build_research_pipeline(
    client,
    model: str,
    system_prompt: str,
    user_prompt_template: str,
    stats_callback: PipelineStatsCallback | None = None,
) -> Runnable[dict, dict]:
    """构建完整的法律研究 Pipeline。

    Pipeline 流程：
    1. 查询分解 (Query Decomposition)
    2. 报告合成 (Report Synthesis)
    3. 深度分析 (Deep Dive Analysis)

    Input: {
        "query": str,
        "local_cases": str,
        "local_statutes": str,
        "ai_knowledge": str,
        "external_api_results": str,
        "web_search_results": str,
        "knowledge_base_results": str,
    }
    Output: {
        "decomposition": dict,
        "initial_report": str,
        "deep_dive_analysis": dict,
    }
    """

    # Step 1: 查询分解
    decompose_chain = build_query_decomposition_chain(client, model, stats_callback=stats_callback)

    # Step 2: 报告合成
    synthesize_chain = build_research_synthesis_chain(client, model, system_prompt, user_prompt_template, stats_callback=stats_callback)

    # Step 3: 深度分析
    deep_dive_chain = build_deep_dive_analysis_chain(client, model, stats_callback=stats_callback)

    # 构建 Pipeline
    async def _pipeline(inputs: dict) -> dict:
        # 1. 查询分解
        decomposition = await decompose_chain.ainvoke({"query": inputs["query"]})

        # 格式化 decomposition 为文本
        decomp_text = _format_decomposition(decomposition)

        # 2. 报告合成
        synthesis_inputs = {
            **inputs,
            "query_decomposition": decomp_text,
        }
        initial_report = await synthesize_chain.ainvoke(synthesis_inputs)

        # 3. 深度分析
        deep_dive_result = await deep_dive_chain.ainvoke({
            "query": inputs["query"],
            "initial_report": initial_report[:6000],
        })

        return {
            "decomposition": decomposition,
            "initial_report": initial_report,
            "deep_dive_analysis": deep_dive_result,
        }

    return RunnableLambda(_pipeline).with_config(run_name="research_pipeline")


def _format_decomposition(decomposition: dict) -> str:
    """格式化 decomposition 为可读文本。"""
    lines: list[str] = []
    if decomposition.get("legal_issues"):
        lines.append("**涉及的法律问题：**")
        for issue in decomposition["legal_issues"]:
            lines.append(f"  - {issue}")
    if decomposition.get("factual_elements"):
        lines.append("\n**需要验证的事实要素：**")
        for elem in decomposition["factual_elements"]:
            lines.append(f"  - {elem}")
    if decomposition.get("procedural_requirements"):
        lines.append("\n**程序性要求：**")
        for req in decomposition["procedural_requirements"]:
            lines.append(f"  - {req}")
    if decomposition.get("key_legal_terms"):
        lines.append("\n**关键法律术语：**")
        for term in decomposition["key_legal_terms"]:
            lines.append(f"  - {term}")
    if decomposition.get("applicable_law_areas"):
        lines.append("\n**涉及法律领域：**")
        for area in decomposition["applicable_law_areas"]:
            lines.append(f"  - {area}")
    return "\n".join(lines) if lines else "（自动分解不可用，使用原始查询）"


# ── 便捷函数 ─────────────────────────────────────────────────────────────────

async def run_query_decomposition(
    client,
    model: str,
    query: str,
    stats_callback: PipelineStatsCallback | None = None,
) -> dict:
    """运行查询分解。

    Args:
        client: LLM 客户端
        model: 模型名称
        query: 用户查询
        stats_callback: 可选的统计回调

    Returns:
        分解结果 dict
    """
    chain = build_query_decomposition_chain(client, model, stats_callback=stats_callback)
    return await chain.ainvoke({"query": query})


async def run_research_pipeline(
    client,
    model: str,
    system_prompt: str,
    user_prompt_template: str,
    query: str,
    local_cases: str,
    local_statutes: str,
    ai_knowledge: str,
    external_api_results: str,
    web_search_results: str,
    knowledge_base_results: str,
    stats_callback: PipelineStatsCallback | None = None,
) -> dict:
    """运行完整的法律研究 Pipeline。

    Returns:
        {
            "decomposition": dict,
            "initial_report": str,
            "deep_dive_analysis": dict,
        }
    """
    pipeline = build_research_pipeline(client, model, system_prompt, user_prompt_template, stats_callback=stats_callback)
    return await pipeline.ainvoke({
        "query": query,
        "local_cases": local_cases,
        "local_statutes": local_statutes,
        "ai_knowledge": ai_knowledge,
        "external_api_results": external_api_results,
        "web_search_results": web_search_results,
        "knowledge_base_results": knowledge_base_results,
    })
