"""Multi-source legal research engine -- parallel data collection + LLM synthesis.

Hardened version with:
1. Enhanced research prompts -- dispute focus / strategy / risk / perspectives
2. Multi-round research -- initial report + deep-dive
3. Source quality scoring -- authority-weighted ranking
4. Smart query decomposition
5. Report structure optimization -- conclusion summary first
6. Citation accuracy -- inline verification markers
7. Edge-case handling -- invalid JSON, no gaps, all-source failure,
   max report length, circular references, pipeline timeout
8. Progress callback support for frontend
9. Query decomposition timeout fallback
10. Content policy refusal handling
11. Citation verification non-blocking delivery
"""

import re
import json
import logging
import asyncio
from datetime import datetime
from typing import Callable, Any
from app.config import get_settings
from app.prompts.persona import SYSTEM_RESEARCH, prompt_with_persona, SYSTEM_CROSS_EXAM
from app.services.llm_client import create_llm_client_from_settings
from app.services.vector.store import get_vector_service
from app.core.monitoring import timed

logger = logging.getLogger(__name__)

# Pipeline timeout (seconds)
_PIPELINE_TIMEOUT = 300  # 5 minutes

# Query decomposition timeout (seconds)
_DECOMPOSE_TIMEOUT = 30

# Safety limit on report length (characters)
_MAX_REPORT_LENGTH = 100_000

# Maximum depth for knowledge base search to prevent circular references
_MAX_KB_DEPTH = 3

# Content policy refusal markers from common LLM providers
_REFUSAL_MARKERS = [
    "我无法",
    "作为AI",
    "我不能提供",
    "I cannot",
    "I'm unable to",
    "content policy",
    "内容政策",
    "无法完成此请求",
    "违反了使用政策",
]


# ========================================================================
# 1. Enhanced research prompts
# ========================================================================

RESEARCH_SYSTEM_PROMPT = SYSTEM_RESEARCH

RESEARCH_PROMPT = prompt_with_persona("""请基于以下多源检索结果，撰写一份专业的法律研究报告。

## 研究课题：{query}

## 查询分解分析：
{query_decomposition}

## 信息来源（按权威性排序）：

### 一、外部法律数据库（权威来源）：
{external_api_results}

### 二、本地法条库检索结果：
{local_statutes}

### 三、本地案例库检索结果：
{local_cases}

### 四、AI法律知识：
{ai_knowledge}

### 五、网络搜索结果：
{web_search_results}

### 六、个人知识库：
{knowledge_base_results}

## 报告要求：

请严格按以下结构撰写研究报告（使用Markdown格式），每个部分必须完整、有实质内容。
**绝对不要省略或留空任何章节。** 如果某个来源无数据，请基于法律专业知识进行分析，并在该部分注明"该来源暂无数据，以下为基于法律一般原则的分析"。

**格式要求：**
- 全文不得使用任何emoji表情符号或星级符号（如★★★），一律使用文字描述
- 使用正式法律书面语言（法言法语），如"本院认为""依照""据以认定"等
- 报告较长时（超过3000字），在目录中标注各章节所在页码

### 结论摘要
- **必须放在报告最前面**，作为第一个章节
- 用2至3句精炼的语句概括核心结论，直接回答研究课题的核心问题
- 概括主要法律风险等级（使用文字：高风险/中风险/低风险）
- 概括核心建议的方向

### 一、争议焦点归纳
- 明确列出本案/本问题的核心争议焦点，逐一编号（1. 2. 3. ...）
- 对每个争议焦点进行简要分析
- 评估各争议焦点的重要程度（关键/重要/一般），不得使用星号

### 二、法律关系分析
- 分析涉及的法律关系主体
- 明确法律关系性质（合同、侵权、劳动等）
- 如涉及多个法律关系，分析其相互关系

### 三、相关法律法规分析
- **必须使用完整法律名称**，格式为《中华人民共和国XXX法》第X条第X款
- 列出核心法律依据，按效力层级排序（法律 > 行政法规 > 司法解释 > 部门规章）
- 分析法条之间的逻辑关系和适用顺序
- 指出适用的司法解释或指导性文件
- 对每条引用标注置信度：[高确信]/[中确信]/[需进一步核实]
- 如存在法律冲突或新旧法衔接问题，明确指出

### 四、冲突法与管辖权分析
- 如涉及跨法域问题，分析法律适用规则
- 确定有管辖权的法院/仲裁机构
- 分析诉讼时效、除斥期间等程序性要求
- 如不涉及跨法域问题，说明适用的管辖规则

### 五、典型案例分析
- 选取3至5个最具参考价值的案例（优先选取最高法、高院案例）
- 对每个案例说明：案号、法院、裁判要旨、裁判逻辑
- 对比分析各案的异同
- 总结法院的裁判倾向和趋势
- 标注案例参考价值：[最高法指导案例]/[高院典型案例]/[参考案例]

### 六、法律风险分析
- 列出主要法律风险点，逐一编号
- 对每个风险点标注：
  - **风险等级**：高风险 / 中风险 / 低风险（必须使用文字，不得使用符号或颜色）
  - **发生概率**：高/中/低
  - **影响程度**：严重/较大/一般
  - **风险描述**：具体说明
- 从原告（申请人）和被告（被申请人）两个视角分别分析风险

### 七、诉讼策略建议
- **原告（申请人）视角**（所有建议编号列出）：
  - 诉讼请求设计建议
  - 证据收集要点
  - 诉讼策略路径
- **被告（被申请人）视角**（所有建议编号列出）：
  - 抗辩理由分析
  - 反诉可能性评估
  - 防御策略路径
- 和解/调解的可行性和建议方案

### 八、实务建议
- 所有建议逐一编号列出（如"建议一：""建议二："等）
- 建议的行动方案和时间表
- 需要进一步调查的事项
- 费用估算参考

### 九、结论
- 综合性结论意见
- 对各争议焦点的逐一回应
- 整体风险评估总结

**引用规范：**
- 引用法条必须使用完整法律全名，如《中华人民共和国民法典》第五百八十四条
- 不得编造不存在的法条或案例
- 如果某个来源无数据，则基于法律专业知识进行分析，不要编造具体数据
- 对AI生成的内容和网络搜索结果，请标注「需进一步核实」

**再次强调：所有章节都必须输出，不能省略任何一个。全文不得使用emoji。所有建议必须编号。风险等级必须使用文字描述。""")


# ========================================================================
# Query decomposition prompt
# ========================================================================

QUERY_DECOMPOSITION_PROMPT = """请分析以下法律研究问题，将其分解为结构化的搜索要素。

研究问题：{query}

请返回严格的JSON格式（不要返回其他内容）：
```json
{{
  "legal_issues": ["涉及的法律问题1", "涉及的法律问题2"],
  "factual_elements": ["需要验证的事实要素1", "需要验证的事实要素2"],
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


# ========================================================================
# Deep-dive / supplementary research prompt
# ========================================================================

DEEP_DIVE_PROMPT = """你是一位法律研究质量审核专家。请审阅以下初步研究报告，识别其中的不足之处。

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


# ========================================================================
# Source quality scoring system
# ========================================================================

SOURCE_QUALITY_WEIGHTS = {
    "外部法律数据库": 1.0,
    "external_api": 1.0,
    "本地法条库": 0.9,
    "vector_db_statutes": 0.9,
    "本地案例库": 0.8,
    "vector_db_cases": 0.8,
    "AI法规检索": 0.7,
    "AI案例检索": 0.7,
    "ai_knowledge": 0.6,
    "web_search": 0.4,
    "knowledge_base": 0.5,
}

COURT_LEVEL_BONUS = {
    "最高人民法院": 0.3,
    "最高法": 0.3,
    "高级人民法院": 0.2,
    "高院": 0.2,
    "中级人民法院": 0.1,
    "中院": 0.1,
}


def score_source_quality(source_name: str, metadata: dict | None = None) -> float:
    """Return a quality score 0.0-1.0 for a given source."""
    base_score = SOURCE_QUALITY_WEIGHTS.get(source_name, 0.3)
    if metadata is None:
        return base_score
    court = metadata.get("court", "") if metadata else ""
    for court_name, bonus in COURT_LEVEL_BONUS.items():
        if court_name in court:
            base_score = min(1.0, base_score + bonus)
            break
    return base_score


def format_source_with_score(source_name: str, content: str, metadata: dict | None = None) -> str:
    """Format a source entry with a quality score label."""
    score = score_source_quality(source_name, metadata)
    if score >= 0.9:
        label = "[权威]"
    elif score >= 0.7:
        label = "[可信]"
    elif score >= 0.5:
        label = "[参考]"
    else:
        label = "[需核实]"
    return f"{label} {content}"


# ========================================================================
# Citation extraction & inline verification
# ========================================================================

def extract_citations(text: str) -> list[tuple[str, str]]:
    """Extract all law-article citations from *text*."""
    citations: list[tuple[str, str]] = []
    pattern = r'《([^》]+)》\s*(第[一二三四五六七八九十百千万零\d]+条)'
    seen: set[tuple[str, str]] = set()
    for match in re.finditer(pattern, text):
        key = (match.group(1), match.group(2))
        if key not in seen:
            seen.add(key)
            citations.append(key)
    return citations


def annotate_citations_inline(report: str, verification_results: list[dict]) -> str:
    """Add inline verification badges to citations in the report."""
    verified_map: dict[tuple[str, str], bool] = {}
    for vr in verification_results:
        key = (vr.get("law_name", ""), vr.get("article_number", ""))
        verified_map[key] = vr.get("consistent", False)

    def _replace(match: re.Match) -> str:
        key = (match.group(1), match.group(2))
        if key in verified_map:
            tag = "已验证" if verified_map[key] else "待核实"
            symbol = "OK" if verified_map[key] else "!!"
            return f"《{match.group(1)}》{match.group(2)} [{tag}{symbol}]"
        return match.group(0)

    return re.sub(
        r'《([^》]+)》\s*(第[一二三四五六七八九十百千万零\d]+条)',
        _replace,
        report,
    )


# ========================================================================
# Content policy refusal detection
# ========================================================================

def _is_refusal(text: str) -> bool:
    """Detect if the LLM response is a content policy refusal."""
    if not text:
        return True
    lower = text.lower()
    # If the response is very short and contains refusal markers
    if len(text) < 200:
        for marker in _REFUSAL_MARKERS:
            if marker.lower() in lower:
                return True
    return False


def _ensure_no_empty_sections(report: str) -> str:
    """Ensure the report has no empty sections by filling gaps with placeholders.
    Also ensure the conclusion summary (结论摘要) is always the first section.
    """
    # Required section headers that must have content
    required_sections = [
        ("### 结论摘要", "（本报告未能生成结论摘要，请基于其他章节内容进行分析）"),
        ("### 一、争议焦点归纳", "（未识别到明确的争议焦点）"),
        ("### 二、法律关系分析", "（法律关系分析暂缺）"),
        ("### 三、相关法律法规分析", "（法律法规分析暂缺）"),
        ("### 四、冲突法与管辖权分析", "（管辖权分析暂缺）"),
        ("### 五、典型案例分析", "（暂无相关典型案例数据）"),
        ("### 六、法律风险分析", "（法律风险分析暂缺）"),
        ("### 七、诉讼策略建议", "（诉讼策略建议暂缺）"),
        ("### 八、实务建议", "（实务建议暂缺）"),
        ("### 九、结论", "（综合结论暂缺）"),
    ]

    for section_header, fallback_text in required_sections:
        if section_header in report:
            # Check if the section has content after the header
            idx = report.index(section_header)
            after = report[idx + len(section_header):].lstrip()
            # If the next thing is another section header or end of doc, it's empty
            if not after or after.startswith("###") or after.startswith("---"):
                report = report[:idx + len(section_header)] + f"\n{fallback_text}\n" + after

    # Ensure 结论摘要 is the first section in the report
    summary_marker = "### 结论摘要"
    if summary_marker in report:
        summary_start = report.index(summary_marker)
        # Find the end of the summary section (next ### or end of report)
        after_summary = report[summary_start + len(summary_marker):]
        next_section_match = re.search(r'\n### ', after_summary)
        if next_section_match:
            summary_end = summary_start + len(summary_marker) + next_section_match.start()
        else:
            summary_end = len(report)
        summary_content = report[summary_start:summary_end].strip()

        # Check if summary is already at the beginning (after any title)
        # Find the position of the first ### header
        first_section_match = re.search(r'### ', report)
        if first_section_match and first_section_match.start() != summary_start:
            # Summary is not the first section -- move it
            # Remove it from its current position
            report = report[:summary_start].rstrip("\n") + "\n" + report[summary_end:].lstrip("\n")
            # Insert it before the first section
            insert_pos = first_section_match.start()
            report = report[:insert_pos] + summary_content + "\n\n" + report[insert_pos:]

    return report


# ========================================================================
# Core research engine
# ========================================================================

class LegalResearchEngine:

    # Track visited queries to detect circular references in KB search
    _visited_kb_queries: set[str]

    def __init__(self):
        self._visited_kb_queries = set()

    # ── Public entry point ───────────────────────────────────────────────

    @timed("research:engine", slow_threshold_ms=10000)
    async def research(
        self,
        query: str,
        sources: list[str],
        case_id: int | None = None,
        progress_callback: Callable[[str, float], Any] | None = None,
        llm=None,
    ) -> dict:
        """Multi-source legal research with pipeline timeout protection.

        Args:
            query: Research question
            sources: List of source types to search
            case_id: Optional case ID for context
            progress_callback: Optional async callback(stage_name, progress_pct)
        """
        if not query or not query.strip():
            return {
                "report": "研究问题不能为空",
                "sources_used": [],
                "query": query,
                "law_verification": [],
                "query_decomposition": {},
            }

        query = query.strip()

        try:
            result = await asyncio.wait_for(
                self._research_inner(query, sources, case_id, progress_callback, llm=llm),
                timeout=_PIPELINE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Research pipeline timed out after %ds for query: %s",
                _PIPELINE_TIMEOUT,
                query[:100],
            )
            result = {
                "report": f"研究超时（超过{_PIPELINE_TIMEOUT}秒限制），请缩小研究范围后重试。",
                "sources_used": [],
                "query": query,
                "law_verification": [],
                "query_decomposition": {},
            }
        return result

    # ── Inner implementation (guarded by timeout) ────────────────────────

    async def _emit_progress(self, callback: Callable[[str, float], Any] | None,
                             stage: str, progress: float):
        """Safely emit progress to callback, catching any errors."""
        if callback is None:
            return
        try:
            result = callback(stage, progress)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.debug("Progress callback error (ignored): %s", e)

    async def _research_inner(
        self, query: str, sources: list[str], case_id: int | None,
        progress_callback: Callable[[str, float], Any] | None = None,
        llm=None,
    ) -> dict:
        settings = get_settings()
        if llm:
            client = llm.client
            model = llm.model
            max_tokens = llm.max_tokens
        else:
            client = create_llm_client_from_settings(settings)
            model = settings.CLAUDE_MODEL
            max_tokens = settings.CLAUDE_MAX_TOKENS

        # Reset circular-reference guard
        self._visited_kb_queries.clear()

        # Step 0: query decomposition with timeout fallback
        await self._emit_progress(progress_callback, "query_decomposition", 0.05)
        decomposition = await self._decompose_query(client, model, query)
        sub_queries = decomposition.get("sub_queries", [query])

        # Step 1: parallel multi-source search
        await self._emit_progress(progress_callback, "source_search", 0.10)
        placeholder = "（未选择该来源）"
        local_cases = placeholder
        local_statutes = placeholder
        ai_knowledge = placeholder
        external_api_results = placeholder
        web_search_results = placeholder
        knowledge_base_results = placeholder

        tasks: dict[str, asyncio.coroutines] = {}

        if "vector_db" in sources:
            tasks["cases"] = self._search_vector_cases_multi(query, sub_queries)
            tasks["statutes"] = self._search_vector_statutes_multi(query, sub_queries)

        if "ai_knowledge" in sources:
            tasks["ai"] = self._search_ai(client, model, query, decomposition)

        if "external_api" in sources:
            tasks["external"] = self._search_external_apis(query, sub_queries)

        if "web_search" in sources:
            tasks["web"] = self._search_web(client, model, query, decomposition)

        if "knowledge_base" in sources:
            tasks["kb"] = self._search_knowledge_base_multi(query, sub_queries, depth=0)

        results: dict = {}
        if tasks:
            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), gathered):
                if not isinstance(result, Exception):
                    results[key] = result
                else:
                    logger.warning("Research source '%s' failed: %s", key, result)
                    results[key] = "（检索失败，请稍后重试）"

        # Handle ALL sources failing simultaneously
        all_failed = all(isinstance(v, str) and "检索失败" in v for v in results.values())
        if all_failed and results:
            logger.error("All research sources failed for query: %s", query[:100])

        await self._emit_progress(progress_callback, "source_search_complete", 0.40)

        # Step 1b: format results with quality scores
        if "cases" in results:
            items = results["cases"]
            if isinstance(items, list) and items:
                scored = []
                for it in items[:8]:
                    meta = it.get("metadata", {})
                    title = meta.get("title", it["id"])
                    content = it["content"][:300]
                    scored.append(
                        format_source_with_score("本地案例库", f"- [{title}] {content}", meta)
                    )
                local_cases = "\n".join(scored)
            else:
                local_cases = "（本地案例库无匹配结果）"

        if "statutes" in results:
            items = results["statutes"]
            if isinstance(items, list) and items:
                scored = []
                for it in items[:8]:
                    meta = it.get("metadata", {})
                    title = meta.get("title", it["id"])
                    content = it["content"][:300]
                    scored.append(
                        format_source_with_score("本地法条库", f"- [{title}] {content}", meta)
                    )
                local_statutes = "\n".join(scored)
            else:
                local_statutes = "（本地法条库无匹配结果）"

        if "ai" in results:
            ai_raw = results["ai"] if isinstance(results["ai"], str) else str(results["ai"])
            ai_knowledge = f"[需核实] 以下内容由AI生成，请核实关键法条引用：\n{ai_raw}"

        if "external" in results:
            ext_raw = results["external"] if isinstance(results["external"], str) else str(results["external"])
            external_api_results = f"[权威] {ext_raw}"

        if "web" in results:
            web_raw = results["web"] if isinstance(results["web"], str) else str(results["web"])
            web_search_results = f"[需核实] 以下内容来自网络搜索，准确性需要验证：\n{web_raw}"

        if "kb" in results:
            knowledge_base_results = results["kb"] if isinstance(results["kb"], str) else str(results["kb"])

        # Step 2: generate initial report
        await self._emit_progress(progress_callback, "report_generation", 0.50)
        decomposition_text = self._format_decomposition(decomposition)

        prompt = RESEARCH_PROMPT.format(
            query=query,
            query_decomposition=decomposition_text,
            local_cases=local_cases,
            local_statutes=local_statutes,
            ai_knowledge=ai_knowledge,
            external_api_results=external_api_results,
            web_search_results=web_search_results,
            knowledge_base_results=knowledge_base_results,
        )

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=RESEARCH_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            initial_report = response.content[0].text if response.content else "报告生成失败"

            # Detect content policy refusal and retry with sanitized prompt
            if _is_refusal(initial_report):
                logger.warning("LLM returned content policy refusal, retrying with neutral prompt")
                sanitized_prompt = RESEARCH_PROMPT.format(
                    query=query,
                    query_decomposition=decomposition_text,
                    local_cases="（来源数据已省略）",
                    local_statutes="（来源数据已省略）",
                    ai_knowledge="（来源数据已省略）",
                    external_api_results="（来源数据已省略）",
                    web_search_results="（来源数据已省略）",
                    knowledge_base_results="（来源数据已省略）",
                )
                try:
                    retry_response = await client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        system=RESEARCH_SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": sanitized_prompt}],
                    )
                    retry_text = retry_response.content[0].text if retry_response.content else ""
                    if retry_text and not _is_refusal(retry_text):
                        initial_report = retry_text
                    else:
                        initial_report = "报告生成受限：内容策略过滤。请调整研究课题后重试。"
                except Exception as retry_err:
                    logger.warning("Retry after refusal also failed: %s", retry_err)
                    initial_report = "报告生成受限：内容策略过滤。请调整研究课题后重试。"

        except Exception as e:
            logger.error("Initial report generation failed: %s", e)
            initial_report = "报告生成失败，请稍后重试"

        # Ensure no empty sections
        initial_report = _ensure_no_empty_sections(initial_report)

        # Step 3: deep-dive pass
        await self._emit_progress(progress_callback, "deep_dive", 0.70)
        final_report = await self._deep_dive_pass(
            client, model, max_tokens, query, initial_report, sources,
            local_cases, local_statutes, ai_knowledge,
            external_api_results, web_search_results, knowledge_base_results,
        )

        # Ensure no empty sections again after merge
        final_report = _ensure_no_empty_sections(final_report)

        # Step 3b: enforce max report length
        if len(final_report) > _MAX_REPORT_LENGTH:
            logger.warning(
                "Report truncated: %d > %d chars",
                len(final_report),
                _MAX_REPORT_LENGTH,
            )
            final_report = (
                final_report[:_MAX_REPORT_LENGTH]
                + "\n\n---\n**[报告因长度限制已截断]**"
            )

        # Step 4: citation verification + inline annotation (non-blocking)
        await self._emit_progress(progress_callback, "citation_verification", 0.90)
        law_verification = []
        try:
            law_verification = await asyncio.wait_for(
                self._verify_laws_in_report(final_report),
                timeout=30,  # Don't let verification block delivery
            )
            final_report = annotate_citations_inline(final_report, law_verification)
        except asyncio.TimeoutError:
            logger.warning("Citation verification timed out, delivering report without verification")
        except Exception as e:
            logger.warning("Citation verification failed (non-blocking): %s", e)
            # Deliver report without verification - don't block the user

        await self._emit_progress(progress_callback, "complete", 1.0)

        return {
            "report": final_report,
            "sources_used": [s for s in sources if s in results],
            "query": query,
            "law_verification": law_verification,
            "query_decomposition": decomposition,
        }

    # ── Query decomposition ──────────────────────────────────────────────

    async def _decompose_query(self, client, model: str, query: str) -> dict:
        """Decompose a user query into structured search elements.
        Returns a dict even if the LLM returns invalid JSON.
        Includes timeout fallback -- if decomposition takes too long, skip it.
        """
        fallback = {
            "legal_issues": [query],
            "factual_elements": [],
            "procedural_requirements": [],
            "key_legal_terms": [],
            "sub_queries": [query],
            "applicable_law_areas": [],
        }
        try:
            # Wrap in timeout to prevent decomposition from blocking the pipeline
            response = await asyncio.wait_for(
                client.messages.create(
                    model=model,
                    max_tokens=2000,
                    system="你是法律检索分析专家。请严格按照JSON格式返回查询分解结果。",
                    messages=[{
                        "role": "user",
                        "content": QUERY_DECOMPOSITION_PROMPT.format(query=query),
                    }],
                ),
                timeout=_DECOMPOSE_TIMEOUT,
            )
            text = response.content[0].text.strip() if response.content else ""
            # Strip code fences
            text = re.sub(r'^```(?:json)?\n?', '', text)
            text = re.sub(r'\n?```$', '', text)

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # Try to extract JSON from within the text (LLM may add prose)
                logger.warning("Query decomposition returned invalid JSON, attempting extraction")
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        logger.warning("JSON extraction also failed, using fallback decomposition")
                        return fallback
                else:
                    return fallback

            # Validate required keys exist
            if not isinstance(data, dict):
                return fallback
            for key in ("sub_queries", "legal_issues"):
                if key not in data or not isinstance(data[key], list):
                    data[key] = fallback.get(key, [])
            return data

        except asyncio.TimeoutError:
            logger.warning("Query decomposition timed out after %ds, skipping decomposition", _DECOMPOSE_TIMEOUT)
            return fallback
        except Exception as e:
            logger.warning("Query decomposition failed: %s", e)
            return fallback

    def _format_decomposition(self, decomposition: dict) -> str:
        """Format decomposition dict as readable text."""
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

    # ── Deep-dive pass ───────────────────────────────────────────────────

    async def _deep_dive_pass(
        self, client, model: str, max_tokens: int, query: str, initial_report: str,
        sources: list[str],
        local_cases: str, local_statutes: str, ai_knowledge: str,
        external_api_results: str, web_search_results: str,
        knowledge_base_results: str,
    ) -> str:
        """Second pass: identify gaps, supplementary search, merge."""
        try:
            dive_prompt = DEEP_DIVE_PROMPT.format(
                query=query,
                initial_report=initial_report[:6000],
            )
            response = await client.messages.create(
                model=model,
                max_tokens=2000,
                system="你是法律研究质量审核专家。请严格按JSON格式返回审核结果。",
                messages=[{"role": "user", "content": dive_prompt}],
            )
            text = response.content[0].text.strip() if response.content else ""
            text = re.sub(r'^```(?:json)?\n?', '', text)
            text = re.sub(r'\n?```$', '', text)

            try:
                dive_analysis = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("Deep dive returned invalid JSON, attempting extraction")
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    try:
                        dive_analysis = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        logger.warning("Deep dive JSON extraction failed, keeping initial report")
                        return initial_report
                else:
                    return initial_report

            if not isinstance(dive_analysis, dict):
                return initial_report

        except Exception as e:
            logger.warning("Deep dive analysis failed: %s", e)
            return initial_report

        # Handle the case where deep dive returns no gaps
        follow_up_queries: list[str] = dive_analysis.get("follow_up_queries", [])
        gaps = dive_analysis.get("gaps", [])
        if gaps:
            for gap in gaps:
                sq = gap.get("suggested_query", "")
                if sq and sq not in follow_up_queries:
                    follow_up_queries.append(sq)

        if not follow_up_queries:
            logger.info("Deep dive found no gaps and no follow-up queries")
            return initial_report

        # Execute supplementary searches (max 3)
        supplement_results: list[str] = []
        for fq in follow_up_queries[:3]:
            sup_tasks: list = []
            sup_keys: list[str] = []

            if "vector_db" in sources:
                sup_tasks.append(self._search_vector_statutes(fq))
                sup_keys.append("statutes")
                sup_tasks.append(self._search_vector_cases(fq))
                sup_keys.append("cases")

            if "ai_knowledge" in sources:
                sup_tasks.append(self._search_ai_simple(client, model, fq))
                sup_keys.append("ai")

            if sup_tasks:
                sup_gathered = await asyncio.gather(*sup_tasks, return_exceptions=True)
                sup_data: dict = {}
                for k, r in zip(sup_keys, sup_gathered):
                    if not isinstance(r, Exception):
                        sup_data[k] = r

                parts: list[str] = []
                if "statutes" in sup_data and sup_data["statutes"]:
                    for it in sup_data["statutes"][:3]:
                        meta = it.get("metadata", {})
                        parts.append(f"- [补充法条] [{meta.get('title', it['id'])}] {it['content'][:200]}")
                if "cases" in sup_data and sup_data["cases"]:
                    for it in sup_data["cases"][:3]:
                        meta = it.get("metadata", {})
                        parts.append(f"- [补充案例] [{meta.get('title', it['id'])}] {it['content'][:200]}")
                if "ai" in sup_data and sup_data["ai"]:
                    parts.append(f"- [补充AI分析] {str(sup_data['ai'])[:500]}")

                if parts:
                    supplement_results.append(
                        f"**补充查询「{fq}」的结果：**\n" + "\n".join(parts)
                    )

        if not supplement_results:
            return initial_report

        # Merge supplementary results into the report
        supplement_text = "\n\n".join(supplement_results)
        merge_prompt = f"""请将以下补充研究结果融入初步报告中，完善相关部分。
不要删除初步报告中的任何现有内容，只在需要的地方补充增强。
保持原有的报告结构和格式。

## 补充研究结果：
{supplement_text}

## 初步报告：
{initial_report}

请返回合并后的完整报告（Markdown格式），保持原有结构不变，在相关章节中融入补充信息。
**重要：所有九个章节都必须保留，不能省略任何一个。**"""

        try:
            merge_response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=RESEARCH_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": merge_prompt}],
            )
            merged_report = merge_response.content[0].text if merge_response.content else initial_report
            return merged_report
        except Exception as e:
            logger.warning("Report merge failed: %s", e)
            return initial_report

    # ── Source search methods ────────────────────────────────────────────

    async def _search_vector_cases(self, query: str) -> list[dict]:
        svc = get_vector_service()
        return await svc.search_cases(query, top_k=5)

    async def _search_vector_statutes(self, query: str) -> list[dict]:
        svc = get_vector_service()
        return await svc.search_statutes(query, top_k=5)

    async def _search_vector_cases_multi(
        self, main_query: str, sub_queries: list[str]
    ) -> list[dict]:
        """Multi-query parallel case search, deduplicated."""
        all_queries = [main_query] + (sub_queries or [])
        tasks = [self._search_vector_cases(q) for q in all_queries[:4]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        seen_ids: set[str] = set()
        merged: list[dict] = []
        for result in results:
            if isinstance(result, list):
                for item in result:
                    item_id = item.get("id", "")
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        merged.append(item)
        return merged

    async def _search_vector_statutes_multi(
        self, main_query: str, sub_queries: list[str]
    ) -> list[dict]:
        """Multi-query parallel statute search, deduplicated."""
        all_queries = [main_query] + (sub_queries or [])
        tasks = [self._search_vector_statutes(q) for q in all_queries[:4]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        seen_ids: set[str] = set()
        merged: list[dict] = []
        for result in results:
            if isinstance(result, list):
                for item in result:
                    item_id = item.get("id", "")
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        merged.append(item)
        return merged

    async def _search_ai(
        self, client, model: str, query: str, decomposition: dict | None = None
    ) -> str:
        """AI legal knowledge search -- uses decomposition to enhance query."""
        try:
            enhanced_query = query
            if decomposition:
                issues = decomposition.get("legal_issues", [])
                terms = decomposition.get("key_legal_terms", [])
                if issues or terms:
                    extra = "；".join(issues[:3] + terms[:3])
                    enhanced_query = f"{query}\n\n请特别关注以下方面：{extra}"

            response = await client.messages.create(
                model=model,
                max_tokens=4000,
                system="""你是一位资深中国法律专家。请提供关于以下问题的专业法律分析。

要求：
1. 引用法条时必须使用完整法律全名，如《中华人民共和国民法典》第五百八十四条
2. 区分法律、行政法规、司法解释的不同效力层级
3. 如果存在法律冲突或新旧法衔接问题，请明确指出
4. 对每个法律观点给出你的确信程度""",
                messages=[{"role": "user", "content": f"法律研究问题：{enhanced_query}"}],
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.warning("AI search failed: %s", e)
            return "（AI检索暂时不可用）"

    async def _search_ai_simple(self, client, model: str, query: str) -> str:
        """Simplified AI search (for supplementary queries)."""
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=2000,
                system="你是中国法律专家。请简要回答以下法律问题，重点引用具体法条。",
                messages=[{"role": "user", "content": f"法律问题：{query}"}],
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.warning("AI simple search failed: %s", e)
            return "（AI补充检索暂时不可用）"

    async def _search_external_apis(
        self, query: str, sub_queries: list[str] | None = None
    ) -> str:
        """Query external legal data sources (Beida Fabao MCP, etc.)."""
        from app.services.data_sources.base import DataSourceRegistry
        adapters = DataSourceRegistry.get_all()
        if not adapters:
            return "（未配置外部法律数据源）"

        all_queries = [query] + (sub_queries or [])[:2]
        results: list[str] = []
        for name, adapter in adapters.items():
            for q in all_queries[:2]:
                try:
                    laws = await adapter.search_law(q, limit=5)
                    for law in laws[:3]:
                        score = score_source_quality(name)
                        label = "[权威]" if score >= 0.9 else "[可信]"
                        results.append(
                            f"- {label} [{name}] {law.title} {law.provision_ref}: {law.content[:200]}"
                        )
                except Exception as e:
                    logger.warning("External API '%s' search failed: %s", name, e)
                    results.append(f"- [{name}] 检索暂时不可用")

        return "\n".join(results) if results else "（外部API无结果）"

    async def _search_web(
        self, client, model: str, query: str, decomposition: dict | None = None
    ) -> str:
        """Web search -- prefers configured search API, falls back to AI knowledge."""
        from app.services.data_sources.base import DataSourceRegistry
        adapters = DataSourceRegistry.get_all()
        for name, adapter in adapters.items():
            if hasattr(adapter, '_config_id'):
                if "search" in (adapter.description or "").lower() or "搜索" in (adapter.description or ""):
                    try:
                        laws = await adapter.search_law(query)
                        if laws:
                            lines = [
                                f"- [{adapter.description}] {law.title}: {law.content[:200]}"
                                for law in laws[:5]
                            ]
                            return "\n".join(lines)
                    except Exception:
                        pass

        # Fallback: AI web knowledge
        try:
            enhanced_query = query
            if decomposition and decomposition.get("key_legal_terms"):
                terms = "、".join(decomposition["key_legal_terms"][:5])
                enhanced_query = f"{query}\n\n请特别关注以下法律术语：{terms}"

            response = await client.messages.create(
                model=model,
                max_tokens=3000,
                system="你是一位法律研究专家。请基于你的知识库和网络公开信息，回答以下法律问题。所有信息请标注「需进一步核实」。引用法条时使用完整法律全名和条文号。",
                messages=[{"role": "user", "content": f"请搜索并提供关于以下法律问题的最新信息：{enhanced_query}"}],
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.warning("Web search failed: %s", e)
            return "（网络搜索暂时不可用）"

    async def _search_knowledge_base(self, query: str, depth: int = 0) -> str:
        """Search personal knowledge base (vector + DB fallback).

        *depth* is tracked to prevent circular references when sub-queries
        recursively trigger knowledge-base lookups.

        Strategy:
        1. Search ChromaDB knowledge collection (vector similarity search)
        2. Fall back to database text search if ChromaDB is unavailable
        3. Auto-vectorize knowledge items that lack embeddings
        """
        if depth > _MAX_KB_DEPTH:
            logger.warning(
                "Knowledge base search depth %d exceeds limit %d, stopping",
                depth,
                _MAX_KB_DEPTH,
            )
            return "（知识库搜索深度超限，已停止递归）"

        # Circular-reference guard
        query_key = query.strip().lower()[:200]
        if query_key in self._visited_kb_queries:
            logger.debug("Circular KB query detected, skipping: %s", query_key[:50])
            return "（知识库无匹配结果）"
        self._visited_kb_queries.add(query_key)

        # --- Step 1: Try ChromaDB knowledge collection (vector search) ---
        chroma_ok = False
        try:
            from app.services.vector.store import get_vector_service
            svc = get_vector_service()
            results = await svc.search_knowledge(query, top_k=5)
            if results:
                chroma_ok = True
                lines = [
                    f"- [知识库:{it.get('id', '')}] {it.get('content', '')[:300]}"
                    for it in results[:5]
                ]
                return "\n".join(lines)
            # ChromaDB connected but no results -- still mark as OK
            # (empty collection is not a failure)
            chroma_ok = True
        except Exception as e:
            logger.debug("ChromaDB knowledge search failed, will use DB fallback: %s", e)

        # --- Step 2: Database text search fallback ---
        db_items = []
        try:
            from app.core.database import async_session
            from app.models.knowledge import KnowledgeItem
            from sqlalchemy import select, or_
            async with async_session() as session:
                result = await session.execute(
                    select(KnowledgeItem)
                    .where(
                        KnowledgeItem.is_platform.is_(True),
                        or_(
                            KnowledgeItem.title.contains(query),
                            KnowledgeItem.content.contains(query),
                        ),
                    )
                    .limit(5)
                )
                db_items = result.scalars().all()
        except Exception as e:
            logger.debug("Database knowledge search failed: %s", e)

        if db_items:
            lines = [f"- [{it.title}] {it.content[:300]}" for it in db_items]

            # --- Step 3: Auto-vectorize items that lack embeddings ---
            # Only attempt if ChromaDB is available and items need vectorization
            if chroma_ok:
                await self._auto_vectorize_knowledge(db_items)

            return "\n".join(lines)

        # Both ChromaDB and DB yielded nothing
        return "（知识库无匹配结果）"

    async def _auto_vectorize_knowledge(self, items: list) -> None:
        """Auto-vectorize knowledge items that lack embeddings in ChromaDB.

        This runs silently in the background -- failures are logged but do
        not affect the search result that triggered the vectorization.
        """
        if not items:
            return
        try:
            from app.services.vector.store import get_vector_service
            svc = get_vector_service()

            # Filter items that don't have an embedding_id yet
            to_vectorize = []
            for it in items:
                if not getattr(it, "embedding_id", None):
                    to_vectorize.append({
                        "id": str(it.id),
                        "title": it.title,
                        "content": it.content,
                        "metadata": {
                            "title": it.title,
                            "source": it.source or "",
                            "tags": it.tags or [],
                        },
                    })

            if to_vectorize:
                count = await svc.add_knowledge(to_vectorize)
                if count > 0:
                    logger.info(
                        "Auto-vectorized %d knowledge items (batch)",
                        count,
                    )
                    # Update embedding_id on the DB records
                    try:
                        from app.core.database import async_session
                        from app.models.knowledge import KnowledgeItem
                        from sqlalchemy import select
                        async with async_session() as session:
                            for item_data in to_vectorize:
                                db_item = await session.get(
                                    KnowledgeItem, int(item_data["id"])
                                )
                                if db_item and not db_item.embedding_id:
                                    db_item.embedding_id = item_data["id"]
                            await session.commit()
                    except Exception as e:
                        logger.debug("Failed to update embedding_id: %s", e)
        except Exception as e:
            logger.debug("Auto-vectorization failed (non-blocking): %s", e)

    async def _search_knowledge_base_multi(
        self, query: str, sub_queries: list[str] | None = None, depth: int = 0
    ) -> str:
        """Multi-query knowledge-base search with circular-reference guard."""
        all_queries = [query] + (sub_queries or [])[:2]
        all_results: list[str] = []
        for q in all_queries[:3]:
            result = await self._search_knowledge_base(q, depth=depth)
            if result and "无匹配结果" not in result:
                all_results.append(result)

        return "\n".join(all_results) if all_results else "（知识库无匹配结果）"

    # ── Citation verification ────────────────────────────────────────────

    async def _verify_laws_in_report(self, report: str) -> list[dict]:
        """Cross-verify law citations in the report."""
        try:
            from app.services.verification.engine import LawVerificationEngine
            engine = LawVerificationEngine()
            verify_results = await engine.verify_document(report)
            return [
                {
                    "law_name": r.law_name,
                    "article_number": r.article_number,
                    "consistent": r.overall_consistent,
                    "confidence": r.confidence,
                    "note": r.recommendation,
                }
                for r in verify_results
            ]
        except Exception:
            return []
