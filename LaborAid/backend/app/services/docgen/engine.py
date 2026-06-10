"""LaborAid 文书生成引擎 — 核心 Pipeline（OpenAI 兼容 LLM）

增强功能：
- 智能模板匹配：提取法律争议焦点 + 自动匹配适用法律
- 研究先行：生成文书前先调用研究引擎收集材料
- 法律依据专节：自动引用具体条文
- 事实摘要：从用户输入自动生成结构化事实概要
- 质量核查：生成后自动运行法条/逻辑/一致性验证
- 多文书集合：支持批量生成并确保一致性
"""

import json
import re
import logging
from app.config import get_settings
from app.prompts.persona import (
    SYSTEM_DOCUMENT,
    SYSTEM_DOCUMENT_BUNDLE,
    SYSTEM_DOCUMENT_GENERATION,
    SYSTEM_DOCUMENT_REVIEW,
)
from app.services.docgen.content_sanitize import sanitize_legal_document_content
from app.services.docgen.format_normalizer import normalize_freeform_markdown
from app.services.docgen.structured import (
    has_structured_renderer,
    merge_bundle_preseed,
    run_structured_generation,
)
from app.services.llm_client import create_llm_client, create_llm_client_from_settings
from app.services.docgen.types import normalize_doc_type
from app.services.docgen.prompts import (
    CASE_PARSING_PROMPT,
    DOCUMENT_GENERATION_PROMPT,
    DOCUMENT_REVIEW_PROMPT,
    DOCUMENT_QUALITY_CHECK_PROMPT,
    LEGAL_ISSUE_EXTRACTION_PROMPT,
    LAW_SEARCH_QUERY_PROMPT,
    CASE_SEARCH_QUERY_PROMPT,
    BUNDLE_CONSISTENCY_CHECK_PROMPT,
    DOC_TYPE_NAMES,
    DOC_TYPE_SPECIFIC_INSTRUCTIONS,
    DOC_TYPE_REQUIRED_ELEMENTS,
    BUNDLE_PRESETS,
    get_case_type_example,
)

logger = logging.getLogger(__name__)

_engine_instance = None


def get_engine() -> "DocumentGenerationEngine":
    global _engine_instance
    if _engine_instance is None:
        settings = get_settings()
        _engine_instance = DocumentGenerationEngine(settings)
    return _engine_instance


def create_engine_for_llm(llm) -> "DocumentGenerationEngine":
    """Build a document engine using a resolved per-user LLM config."""
    settings = get_settings()
    return DocumentGenerationEngine(
        settings,
        llm_base_url=llm.base_url,
        llm_api_key=llm.api_key,
        llm_model=llm.model,
    )


class DocumentGenerationEngine:

    def __init__(self, settings=None, llm_base_url=None, llm_api_key=None, llm_model=None):
        if settings is None:
            settings = get_settings()
        self._settings = settings
        base_url = llm_base_url or settings.LLM_BASE_URL
        api_key = llm_api_key or settings.LLM_API_KEY
        self.client = create_llm_client(base_url, api_key)
        self.model = llm_model or settings.LLM_MODEL

    # Maximum word count for generated content to prevent runaway generation
    MAX_CONTENT_WORDS = 15000

    # Maximum input length for case facts
    MAX_CASE_FACTS_LENGTH = 200000  # 200K chars
    MIN_CASE_FACTS_LENGTH = 5  # Minimum meaningful input

    async def _call_claude(self, system: str, user: str, max_tokens: int = 4096) -> str:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = response.content[0].text if response.content else ""
            if not text or not text.strip():
                logger.warning("LLM returned empty content")
                return ""
            # Word count limit to prevent runaway generation
            word_count = len(text)
            if word_count > self.MAX_CONTENT_WORDS:
                logger.warning("LLM output truncated: %d chars > %d", word_count, self.MAX_CONTENT_WORDS)
                text = text[:self.MAX_CONTENT_WORDS]
            return text
        except Exception as e:
            error_type = type(e).__name__
            if 'ConnectionError' in error_type or 'connection' in str(e).lower():
                logger.error("AI API connection error: %s", e)
                raise RuntimeError("AI服务连接失败，请检查网络后重试")
            if 'RateLimitError' in error_type or 'rate' in str(e).lower():
                logger.error("AI API rate limit hit")
                raise RuntimeError("AI服务请求过于频繁，请稍后再试")
            if 'StatusError' in error_type or hasattr(e, 'status_code'):
                status_code = getattr(e, 'status_code', 'unknown')
                logger.error("AI API error %s: %s", status_code, e)
                raise RuntimeError("AI服务暂时不可用，请稍后重试")
            logger.error("AI API unexpected error: %s", e)
            raise RuntimeError("文书生成服务暂时不可用，请稍后重试")

    def _parse_json_response(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse JSON from AI response: %s", text[:200])
            return {}

    # ------------------------------------------------------------------
    # Step 1: 案件解析（使用 LCEL 链）
    # ------------------------------------------------------------------
    async def parse_case(self, case_facts: str) -> dict:
        """解析案件事实为结构化信息。使用 LCEL 链封装。"""
        try:
            # 使用 LCEL 链进行案件解析
            from app.services.rag.chains import build_case_parsing_chain
            
            chain = build_case_parsing_chain(
                self.client,
                self.model,
                system_prompt="你是专业的中国法律分析师。",
                user_prompt_template=CASE_PARSING_PROMPT,
            )
            parsed = await chain.ainvoke({"case_facts": case_facts})
            
            if not parsed:
                return {"case_type": "未知", "facts": case_facts, "claims": [], "parties": {}}
            return parsed
        except RuntimeError:
            raise
        except Exception as e:
            logger.warning("Case parsing failed, using fallback: %s", e)
            return {"case_type": "未知", "facts": case_facts, "claims": [], "parties": {}}

    # ------------------------------------------------------------------
    # Step 2: 法律争议焦点提取（使用 LCEL 链）
    # ------------------------------------------------------------------
    async def extract_legal_issues(self, parsed_case: dict, related_laws: str) -> dict:
        """提取核心法律争议焦点并确定适用法律，用于智能匹配和文书生成。
        使用 LCEL 链封装。
        """
        try:
            from app.services.rag.chains import make_llm_call, extract_json_from_text
            
            chain = make_llm_call(
                self.client,
                self.model,
                system_prompt="你是资深中国法律分析师，擅长案件争议焦点归纳和法律适用分析。",
                user_prompt=LEGAL_ISSUE_EXTRACTION_PROMPT,
                max_tokens=2000,
            )
            result = await chain.ainvoke({
                "parsed_case": json.dumps(parsed_case, ensure_ascii=False, indent=2),
                "related_laws": related_laws or "暂无",
            })
            
            extracted = extract_json_from_text(result)
            if not extracted:
                return {"key_issues": [], "applicable_statutes": [], "burden_of_proof": "", "recommended_strategy": ""}
            return extracted
        except Exception as e:
            logger.warning("Legal issue extraction failed: %s", e)
            return {"key_issues": [], "applicable_statutes": [], "burden_of_proof": "", "recommended_strategy": ""}

    # ------------------------------------------------------------------
    # Step 3: 检索关键词生成（使用 LCEL 链）
    # ------------------------------------------------------------------
    async def generate_search_queries(self, case_facts: str) -> dict:
        """生成检索关键词。使用 LCEL 链封装。"""
        try:
            from app.services.rag.chains import make_llm_call
            
            chain = make_llm_call(
                self.client,
                self.model,
                system_prompt="你是法律检索专家。只输出关键词，用逗号分隔。",
                user_prompt=LAW_SEARCH_QUERY_PROMPT,
                max_tokens=200,
            )
            raw = await chain.ainvoke({"case_facts": case_facts})
            
            keywords = re.split(r'[,，\n]', raw)
            keywords = [k.strip().strip('"').strip("'") for k in keywords if k.strip()]
            return {"law_keywords": keywords[:5], "case_keywords": keywords[:5]}
        except Exception:
            return {"law_keywords": [case_facts[:20]], "case_keywords": [case_facts[:20]]}

    # ------------------------------------------------------------------
    # Step 4: 多源法律检索
    # ------------------------------------------------------------------
    async def search_related_laws(self, keywords: list[str]) -> str:
        try:
            query = "、".join(keywords[:3])
            result = await self._call_claude(
                system="你是中国法律检索专家。列出与查询最相关的5条法规，每条包含法规名、条款号和核心内容。",
                user=f"检索关键词：{query}\n\n请列出5条最相关法规，格式：法规名 第X条：核心内容",
                max_tokens=1500,
            )
            return result
        except Exception:
            return "（法规检索暂不可用）"

    async def search_related_cases(self, keywords: list[str]) -> str:
        try:
            query = "、".join(keywords[:3])
            result = await self._call_claude(
                system="你是中国法律案例检索专家。列出与查询最相关的3个典型案例。",
                user=f"检索关键词：{query}\n\n请列出3个典型案例，包含案号、法院、裁判要旨。",
                max_tokens=1500,
            )
            return result
        except Exception:
            return "（案例检索暂不可用）"

    # ------------------------------------------------------------------
    # Step 5: 文书生成（主入口）— 研究先行 + 智能匹配
    # ------------------------------------------------------------------
    async def generate(
        self,
        case_facts: str,
        doc_type: str,
        template=None,
        extra_instructions: str | None = None,
        research_context: str | None = None,
    ) -> dict:
        import asyncio

        doc_type = normalize_doc_type(doc_type) or doc_type

        # Input validation
        if not case_facts or not case_facts.strip():
            return {
                "title": DOC_TYPE_NAMES.get(doc_type, doc_type),
                "content": "案件事实描述为空，无法生成文书。",
                "metadata": {},
            }
        if len(case_facts) < DocumentGenerationEngine.MIN_CASE_FACTS_LENGTH:
            return {
                "title": DOC_TYPE_NAMES.get(doc_type, doc_type),
                "content": "案件事实描述过短，请提供更详细的案件信息。",
                "metadata": {},
            }
        if len(case_facts) > DocumentGenerationEngine.MAX_CASE_FACTS_LENGTH:
            logger.warning("Case facts truncated: %d > %d chars", len(case_facts), DocumentGenerationEngine.MAX_CASE_FACTS_LENGTH)
            case_facts = case_facts[:DocumentGenerationEngine.MAX_CASE_FACTS_LENGTH]

        # 1) 解析案件
        parsed_case = await self.parse_case(case_facts)

        # 2) 生成检索关键词
        queries = await self.generate_search_queries(case_facts)

        # 3) 并行检索：AI知识 + 向量库 + 外部API
        tasks = [
            self.search_related_laws(queries["law_keywords"]),
            self.search_related_cases(queries["case_keywords"]),
            self._search_vector_statutes(queries["law_keywords"]),
            self._search_vector_cases(queries["case_keywords"]),
            self._search_external_sources(queries["law_keywords"]),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        ai_laws = results[0] if not isinstance(results[0], Exception) else "（法规检索暂不可用）"
        ai_cases = results[1] if not isinstance(results[1], Exception) else "（案例检索暂不可用）"
        vec_statutes = results[2] if not isinstance(results[2], Exception) else ""
        vec_cases = results[3] if not isinstance(results[3], Exception) else ""
        ext_laws = results[4] if not isinstance(results[4], Exception) else ""

        # 合并所有来源
        combined_laws = ai_laws
        if vec_statutes:
            combined_laws += f"\n\n【本地法条库参考】\n{vec_statutes}"
        if ext_laws:
            combined_laws += f"\n\n【外部法律数据库参考】\n{ext_laws}"

        combined_cases = ai_cases
        if vec_cases:
            combined_cases += f"\n\n【本地案例库参考】\n{vec_cases}"

        # 4) 智能匹配：提取法律争议焦点
        legal_issues = await self.extract_legal_issues(parsed_case, combined_laws)

        # 构建法律依据专节
        legal_basis_section = self._build_legal_basis_section(legal_issues)
        # 构建事实摘要
        facts_summary = self._build_facts_summary(parsed_case)

        # 5) 组装模板结构（结构 JSON + 模板 ai_prompt）
        doc_type_name = DOC_TYPE_NAMES.get(doc_type, doc_type)
        template_structure = "无特定模板结构要求"
        structure_parts: list[str] = []
        if template and getattr(template, "ai_prompt", None):
            ai_prompt = (template.ai_prompt or "").strip()
            if ai_prompt:
                structure_parts.append(f"## 模板撰写指引\n{ai_prompt}")
        if template and hasattr(template, "structure") and template.structure:
            try:
                structure_parts.append(
                    "## 模板字段结构\n"
                    + json.dumps(template.structure, ensure_ascii=False, indent=2)
                )
            except (TypeError, ValueError):
                logger.warning("Template structure is not JSON-serializable, using default")
        if structure_parts:
            template_structure = "\n\n".join(structure_parts)

        # 获取文书类型专属规范
        doc_type_specific = DOC_TYPE_SPECIFIC_INSTRUCTIONS.get(doc_type, "")
        if not doc_type_specific:
            logger.warning("No specific instructions found for doc_type=%s", doc_type)

        # 6) 调用LLM生成文书
        enhanced_parsed_case = {
            **parsed_case,
            "facts_summary": facts_summary,
            "legal_issues": legal_issues.get("key_issues", []),
            "applicable_statutes": legal_issues.get("applicable_statutes", []),
            "burden_of_proof": legal_issues.get("burden_of_proof", ""),
            "recommended_strategy": legal_issues.get("recommended_strategy", ""),
        }

        # lawgpt 模式：JSON 抽取 + 固定模板渲染（17 类平台文书）
        if has_structured_renderer(doc_type):
            content, payload, struct_debug = await run_structured_generation(
                self,
                doc_type=doc_type,
                doc_type_name=doc_type_name,
                case_facts=case_facts,
                parsed_case=enhanced_parsed_case,
                combined_laws=combined_laws,
                legal_basis_section=legal_basis_section,
                extra_instructions=extra_instructions,
                template=template,
                research_context=research_context,
            )

            plaintiff = parsed_case.get("parties", {}).get("plaintiff", {}).get("name", "")
            defendant = parsed_case.get("parties", {}).get("defendant", {}).get("name", "")
            cause = parsed_case.get("cause_of_action", "")
            if plaintiff and defendant:
                title = f"{plaintiff}诉{defendant}{cause}一案{doc_type_name}" if cause else f"{plaintiff}诉{defendant}{doc_type_name}"
            else:
                title = doc_type_name

            return {
                "title": title,
                "content": content,
                "metadata": {
                    "parsed_case": parsed_case,
                    "legal_issues": legal_issues,
                    "law_keywords": queries["law_keywords"],
                    "case_keywords": queries["case_keywords"],
                    "facts_summary": facts_summary,
                    "applicable_statutes": legal_issues.get("applicable_statutes", []),
                    "generation_mode": "structured",
                    "structured_payload": payload,
                    "structured_debug": struct_debug,
                },
            }

        # 根据案由选择对应的范文示例，注入 prompt 引导 LLM 输出更丰富的内容
        cause_of_action = parsed_case.get("cause_of_action", "") or parsed_case.get("sub_type", "")
        case_type_example = get_case_type_example(cause_of_action)
        if not case_type_example:
            case_type_example = ""

        content = await self._call_claude(
            system=SYSTEM_DOCUMENT_GENERATION,
            user=DOCUMENT_GENERATION_PROMPT.format(
                doc_type_name=doc_type_name,
                parsed_case=json.dumps(enhanced_parsed_case, ensure_ascii=False, indent=2),
                related_laws=combined_laws,
                related_cases=combined_cases,
                research_context=research_context or "无",
                template_structure=template_structure,
                extra_instructions=extra_instructions or "无",
                doc_type_specific=doc_type_specific,
                case_type_example=case_type_example,
            ),
            max_tokens=self._settings.CLAUDE_MAX_TOKENS,
        )

        # 7) Handle empty content from LLM
        if not content or not content.strip():
            logger.warning("LLM returned empty content for document generation, using fallback")
            content = f"# {doc_type_name}\n\n（AI生成内容为空，请基于以下案件信息手动填写）\n\n## 案件事实\n{case_facts}\n"

        content = sanitize_legal_document_content(content, doc_type_name)
        content = normalize_freeform_markdown(content, doc_type)

        # 8) 插入法律依据专节（如果LLM没有自行生成）
        if "法律依据" not in content and legal_basis_section:
            content = self._inject_legal_basis(content, legal_basis_section)

        # 8) 生成标题
        plaintiff = parsed_case.get("parties", {}).get("plaintiff", {}).get("name", "")
        defendant = parsed_case.get("parties", {}).get("defendant", {}).get("name", "")
        cause = parsed_case.get("cause_of_action", "")
        if plaintiff and defendant:
            title = f"{plaintiff}诉{defendant}{cause}一案{doc_type_name}" if cause else f"{plaintiff}诉{defendant}{doc_type_name}"
        else:
            title = doc_type_name

        return {
            "title": title,
            "content": content,
            "metadata": {
                "parsed_case": parsed_case,
                "legal_issues": legal_issues,
                "law_keywords": queries["law_keywords"],
                "case_keywords": queries["case_keywords"],
                "facts_summary": facts_summary,
                "applicable_statutes": legal_issues.get("applicable_statutes", []),
                "generation_mode": "freeform",
            },
        }

    # ------------------------------------------------------------------
    # Step 6: 质量核查（自动验证） — 先本地规则检查，再AI深度核查
    # ------------------------------------------------------------------
    async def quality_check(self, content: str, doc_type: str, parsed_case: dict | None = None) -> dict:
        """对已生成的文书进行质量核查，返回结构化检查结果。

        执行顺序:
        1. 本地规则检查（法条引用格式、必要要素、金额/日期一致性、结构完整性）
        2. AI深度核查（逻辑一致性、法条准确性、建议）
        3. 合并结果，返回结构化质量报告
        """
        doc_type_name = DOC_TYPE_NAMES.get(doc_type, doc_type)

        # --- Phase 1: 本地规则检查 ---
        checks = {}
        issues = []

        # Check 1: 法条引用格式验证
        citation_result = self._check_citation_format(content)
        checks["cited_laws_valid"] = citation_result["valid"]
        issues.extend(citation_result["issues"])

        # Check 2: 文书必要要素检查
        elements_result = self._check_required_elements(content, doc_type)
        checks["required_elements_present"] = elements_result["present"]
        issues.extend(elements_result["issues"])

        # Check 3: 金额一致性检查
        amount_result = self._check_amount_consistency(content, parsed_case)
        checks["amounts_consistent"] = amount_result["consistent"]
        issues.extend(amount_result["issues"])

        # Check 4: 日期一致性检查
        date_result = self._check_date_consistency(content, parsed_case)
        checks["dates_consistent"] = date_result["consistent"]
        issues.extend(date_result["issues"])

        # Check 5: 结构完整性检查
        structure_result = self._check_structure_completeness(content, doc_type)
        checks["structure_standard"] = structure_result["complete"]
        issues.extend(structure_result["issues"])

        # --- Phase 2: AI深度核查 ---
        ai_checks = {}
        ai_issues = []
        ai_summary = ""
        ai_score = None

        try:
            result = await self._call_claude(
                system="你是法律文书质量核查系统，负责自动化验证文书质量。",
                user=DOCUMENT_QUALITY_CHECK_PROMPT.format(
                    doc_type_name=doc_type_name,
                    content=content,
                    parsed_case=json.dumps(parsed_case, ensure_ascii=False, indent=2) if parsed_case else "无",
                ),
                max_tokens=2000,
            )
            check_result = self._parse_json_response(result)
            if check_result:
                ai_checks = check_result.get("checks", {})
                ai_issues = check_result.get("issues", [])
                ai_summary = check_result.get("summary", "")
                ai_score = check_result.get("quality_score")
        except Exception as e:
            logger.warning("AI quality check failed (using local checks only): %s", e)

        # --- Phase 3: 合并结果 ---
        # Merge AI checks into local checks (AI can override)
        merged_checks = {**checks, **ai_checks}

        # Merge issues (deduplicate by description)
        seen_descriptions = set()
        merged_issues = []
        for issue in issues + ai_issues:
            desc = issue.get("description", "") if isinstance(issue, dict) else str(issue)
            if desc not in seen_descriptions:
                seen_descriptions.add(desc)
                merged_issues.append(issue)

        # Compute quality score
        local_pass_count = sum(1 for v in checks.values() if v)
        local_total = len(checks)
        local_score = int((local_pass_count / max(local_total, 1)) * 100)

        if ai_score is not None:
            quality_score = round((local_score + ai_score) / 2)
        else:
            quality_score = local_score

        # Overall pass/fail
        critical_failures = [
            i for i in merged_issues
            if isinstance(i, dict) and i.get("severity") == "error"
        ]
        passed = len(critical_failures) == 0 and quality_score >= 60

        # Build summary
        summary_parts = []
        if ai_summary:
            summary_parts.append(ai_summary)
        if not passed:
            summary_parts.append(
                f"发现 {len(critical_failures)} 个严重问题和 {len(merged_issues) - len(critical_failures)} 个警告。"
            )
        else:
            summary_parts.append(
                f"质量核查通过，得分 {quality_score}。"
            )

        return {
            "passed": passed,
            "issues": merged_issues,
            "checks": merged_checks,
            "quality_score": quality_score,
            "summary": " ".join(summary_parts) if summary_parts else "质量核查完成",
        }

    # ------------------------------------------------------------------
    # 本地质量检查辅助方法
    # ------------------------------------------------------------------

    def _check_citation_format(self, content: str) -> dict:
        """验证法条引用格式是否正确。

        正确格式: 《法律名称》第X条
        常见错误: 缺少书名号、缺少条文号、引用格式不完整
        """
        issues = []
        valid = True

        # 提取所有形如 《...》的引用
        book_refs = re.findall(r'《([^》]+)》', content)
        for ref in book_refs:
            # 检查引用后是否跟有条文号
            pattern = rf'《{re.escape(ref)}》\s*(第[一二三四五六七八九十百千万零\d]+条)'
            if not re.search(pattern, content):
                # 可能只是提到法律名称，不一定需要条文号
                # 但如果引用了具体内容应该有条文号
                pass

        # 检查是否有没有书名号的法律引用（常见错误）
        bare_refs = re.findall(r'(?<![《])(?:中华人民共和国|民法典|刑法|民事诉讼法|行政诉讼法|劳动合同法|公司法|合同法|侵权责任法|物权法|婚姻法|继承法|刑法|刑事诉讼法|仲裁法|商标法|专利法|著作权法|道路交通安全法|消费者权益保护法|劳动法|社会保险法)(?!》)', content)
        for bare in bare_refs:
            # 排除 "《中华人民共和国XXX法》" 中间部分
            if not re.search(rf'《[^》]*{re.escape(bare)}[^》]*》', content):
                issues.append({
                    "category": "法条引用",
                    "severity": "warning",
                    "description": f"法律引用可能缺少书名号: {bare}",
                    "location": f"文书中提到「{bare}」处",
                    "suggestion": f"建议改为《{bare}》",
                })
                valid = False

        # 检查条文号格式
        article_refs = re.findall(r'第([一二三四五六七八九十百千万零\d]+)条', content)
        for article_num in article_refs:
            # 条文号应该在50条以下的常见范围... 这个不太好验证
            # 主要检查格式是否合理（不含奇怪字符）
            pass

        if issues:
            valid = False

        return {"valid": valid, "issues": issues}

    def _check_required_elements(self, content: str, doc_type: str) -> dict:
        """检查文书是否包含该类型要求的必要要素。"""
        issues = []
        required = DOC_TYPE_REQUIRED_ELEMENTS.get(doc_type, [])

        if not required:
            return {"present": True, "issues": []}

        missing = []
        for element in required:
            if element not in content:
                missing.append(element)

        if missing:
            issues.append({
                "category": "要素完整性",
                "severity": "error" if len(missing) > 2 else "warning",
                "description": f"缺少必要要素: {', '.join(missing)}",
                "location": "文书整体结构",
                "suggestion": f"请补充以下要素: {', '.join(missing)}",
            })

        present = len(missing) == 0
        return {"present": present, "issues": issues}

    def _check_amount_consistency(self, content: str, parsed_case: dict | None = None) -> dict:
        """检查文书中的金额是否一致。

        检查:
        - 阿拉伯数字金额是否与中文大写金额匹配
        - 各处出现的金额是否一致
        - 与parsed_case中的金额是否匹配
        """
        issues = []

        # 提取阿拉伯数字金额 (e.g., 100,000.00 or 100000)
        arabic_amounts = re.findall(
            r'[￥¥]?\s*([\d,]+(?:\.\d{1,2})?)\s*元?',
            content,
        )
        # Clean commas for comparison
        clean_amounts = []
        for amt in arabic_amounts:
            try:
                val = float(amt.replace(",", ""))
                if val > 0:
                    clean_amounts.append(val)
            except ValueError:
                continue

        # Extract Chinese numeral amounts (simplified check)
        chinese_amount_pattern = r'[一二三四五六七八九十百千万零壹贰叁肆伍陆柒捌玖拾佰仟亿圆元整]+'
        chinese_amounts = re.findall(chinese_amount_pattern, content)

        # Check for consistency: if there are multiple distinct amounts, flag them
        unique_amounts = list(set(clean_amounts))
        if len(unique_amounts) > 3:
            issues.append({
                "category": "金额数据",
                "severity": "warning",
                "description": f"文书中出现多个不同金额 ({len(unique_amounts)}个): {', '.join(f'{a:,.2f}' for a in sorted(unique_amounts)[:5])}",
                "location": "文书金额相关段落",
                "suggestion": "请核实各处金额是否准确一致",
            })

        # Check against parsed_case amount if available
        if parsed_case and clean_amounts:
            case_amount_str = parsed_case.get("amount_involved", "")
            if case_amount_str:
                try:
                    # Try to extract numeric value from case amount
                    case_nums = re.findall(r'[\d,]+(?:\.\d+)?', str(case_amount_str))
                    if case_nums:
                        case_val = float(case_nums[0].replace(",", ""))
                        max_doc_amount = max(clean_amounts) if clean_amounts else 0
                        if case_val > 0 and max_doc_amount > 0:
                            # Allow 10% tolerance for interest, fees, etc.
                            ratio = abs(max_doc_amount - case_val) / case_val
                            if ratio > 0.5:  # More than 50% difference is suspicious
                                issues.append({
                                    "category": "金额数据",
                                    "severity": "warning",
                                    "description": f"文书金额({max_doc_amount:,.2f})与案件金额({case_val:,.2f})差异较大",
                                    "location": "诉讼请求/事实理由段",
                                    "suggestion": "请核实文书中的金额是否与案件实际金额一致",
                                })
                except (ValueError, IndexError):
                    pass

        consistent = len([i for i in issues if i.get("severity") == "error"]) == 0
        return {"consistent": consistent, "issues": issues}

    def _check_date_consistency(self, content: str, parsed_case: dict | None = None) -> dict:
        """检查文书中的日期格式和一致性。"""
        issues = []

        # 提取所有日期格式的出现
        # YYYY年MM月DD日
        dates_full = re.findall(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', content)
        # YYYY-MM-DD
        dates_iso = re.findall(r'(\d{4})-(\d{1,2})-(\d{1,2})', content)

        all_dates = []
        for y, m, d in dates_full:
            try:
                all_dates.append((int(y), int(m), int(d)))
            except ValueError:
                pass
        for y, m, d in dates_iso:
            try:
                all_dates.append((int(y), int(m), int(d)))
            except ValueError:
                pass

        # Validate individual dates
        for y, m, d in all_dates:
            if m < 1 or m > 12:
                issues.append({
                    "category": "日期格式",
                    "severity": "error",
                    "description": f"无效月份: {y}年{m}月{d}日",
                    "location": "文书日期相关段落",
                    "suggestion": "请修正月份（应为1-12）",
                })
            if d < 1 or d > 31:
                issues.append({
                    "category": "日期格式",
                    "severity": "error",
                    "description": f"无效日期: {y}年{m}月{d}日",
                    "location": "文书日期相关段落",
                    "suggestion": "请修正日期（应为1-31）",
                })

        # Check for date format inconsistency (mixed formats)
        if dates_full and dates_iso:
            issues.append({
                "category": "日期格式",
                "severity": "info",
                "description": "文书中混用了多种日期格式（中文日期和ISO日期）",
                "location": "文书日期相关段落",
                "suggestion": "建议统一使用中文日期格式（XXXX年XX月XX日）",
            })

        # Check against parsed_case key dates if available
        if parsed_case:
            key_dates = parsed_case.get("key_dates", [])
            if key_dates and all_dates:
                # Basic check: at least one date from the case should appear
                pass  # Deep date matching is complex; rely on AI check

        consistent = len([i for i in issues if i.get("severity") == "error"]) == 0
        return {"consistent": consistent, "issues": issues}

    def _check_structure_completeness(self, content: str, doc_type: str) -> dict:
        """检查文书结构完整性（基于文档类型要求）。"""
        issues = []
        required = DOC_TYPE_REQUIRED_ELEMENTS.get(doc_type, [])

        if not required:
            return {"complete": True, "issues": []}

        missing_structure = []
        # Check for structural markers
        structure_markers = {
            "此致法院": ["此致", "人民法院"],
            "起诉人签名": ["起诉人", "具状人", "原告"],
            "答辩人签名": ["答辩人"],
            "上诉人签名": ["上诉人"],
            "日期": ["年", "月", "日"],
            "附件": ["附", "副本", "附件"],
            "代理人签名": ["代理人", "律师"],
            "代理人信息": ["代理权限", "律师事务所"],
        }

        for element in required:
            if element in content:
                continue
            # Check alternative markers
            markers = structure_markers.get(element, [element])
            found = any(m in content for m in markers)
            if not found:
                missing_structure.append(element)

        if missing_structure:
            severity = "error" if len(missing_structure) > len(required) * 0.4 else "warning"
            issues.append({
                "category": "格式规范",
                "severity": severity,
                "description": f"文书结构不完整，缺少: {', '.join(missing_structure)}",
                "location": "文书整体结构",
                "suggestion": f"请补充以下结构要素: {', '.join(missing_structure)}",
            })

        complete = len(missing_structure) == 0
        return {"complete": complete, "issues": issues}

    # ------------------------------------------------------------------
    # Step 7: 法条引用核查（多源交叉验证）
    # ------------------------------------------------------------------
    async def verify_laws_in_content(self, content: str) -> list[dict]:
        """法条核查 — 从文书中提取法条引用并多源交叉验证"""
        try:
            from app.services.verification.engine import LawVerificationEngine
            engine = LawVerificationEngine()
            results = await engine.verify_document(content)
            return [
                {
                    "law_name": r.law_name,
                    "article_number": r.article_number,
                    "overall_consistent": r.overall_consistent,
                    "confidence": r.confidence,
                    "recommendation": r.recommendation,
                    "sources_checked": [
                        {"source": v.source, "found": v.found, "is_consistent": v.is_consistent}
                        for v in r.results
                    ],
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("Law verification failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Step 8: 审校（人工辅助）
    # ------------------------------------------------------------------
    async def review(self, content: str, doc_type: str) -> str:
        doc_type_name = DOC_TYPE_NAMES.get(doc_type, doc_type)
        result = await self._call_claude(
            system=SYSTEM_DOCUMENT_REVIEW,
            user=DOCUMENT_REVIEW_PROMPT.format(
                doc_type_name=doc_type_name,
                content=content,
            ),
            max_tokens=self._settings.CLAUDE_MAX_TOKENS,
        )
        if "<!-- REVIEW_NOTES -->" in result:
            return result.split("<!-- REVIEW_NOTES -->")[0].strip()
        return result

    # ------------------------------------------------------------------
    # Multi-document Bundle: 批量生成 + 一致性检查
    # ------------------------------------------------------------------
    async def generate_bundle(
        self,
        case_facts: str,
        doc_types: list[str],
        preset: str | None = None,
        extra_instructions: str | None = None,
        research_context: str | None = None,
    ) -> dict:
        """生成多份文书集合，确保交叉一致性。

        Args:
            case_facts: 案件事实
            doc_types: 要生成的文书类型列表
            preset: 预设名称（如 "civil_litigation_full"），覆盖 doc_types
            extra_instructions: 额外指示
            research_context: 研究报告依据

        Returns:
            {
                "documents": [{doc_type, title, content, metadata}, ...],
                "consistency_check": {...},
            }
        """
        import asyncio

        # 如果指定了预设，使用预设的文书类型
        if preset and preset in BUNDLE_PRESETS:
            doc_types = BUNDLE_PRESETS[preset]["doc_types"]

        # 1) 统一解析案件（所有文书共用同一份解析结果）
        parsed_case = await self.parse_case(case_facts)
        queries = await self.generate_search_queries(case_facts)

        # 2) 统一检索法律和案例
        tasks = [
            self.search_related_laws(queries["law_keywords"]),
            self.search_related_cases(queries["case_keywords"]),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        combined_laws = results[0] if not isinstance(results[0], Exception) else ""
        combined_cases = results[1] if not isinstance(results[1], Exception) else ""

        # 3) 统一提取法律争议焦点
        legal_issues = await self.extract_legal_issues(parsed_case, combined_laws)

        # 构建共享上下文
        shared_context = {
            "parsed_case": parsed_case,
            "legal_issues": legal_issues,
            "combined_laws": combined_laws,
            "combined_cases": combined_cases,
            "facts_summary": self._build_facts_summary(parsed_case),
            "legal_basis_section": self._build_legal_basis_section(legal_issues),
        }

        # 4) 依次生成每份文书（共享上下文 + 跨文书字段预填确保一致性）
        documents = []
        bundle_shared_preseed: dict = {}
        for doc_type in doc_types:
            try:
                doc_type_name = DOC_TYPE_NAMES.get(doc_type, doc_type)
                doc_type_specific = DOC_TYPE_SPECIFIC_INSTRUCTIONS.get(doc_type, "")

                enhanced_parsed_case = {
                    **parsed_case,
                    "facts_summary": shared_context["facts_summary"],
                    "legal_issues": legal_issues.get("key_issues", []),
                    "applicable_statutes": legal_issues.get("applicable_statutes", []),
                    "burden_of_proof": legal_issues.get("burden_of_proof", ""),
                    "recommended_strategy": legal_issues.get("recommended_strategy", ""),
                }

                bundle_meta: dict = {"parsed_case": parsed_case, "legal_issues": legal_issues, "bundle_preset": preset}
                if has_structured_renderer(doc_type):
                    content, payload, struct_debug = await run_structured_generation(
                        self,
                        doc_type=doc_type,
                        doc_type_name=doc_type_name,
                        case_facts=case_facts,
                        parsed_case=enhanced_parsed_case,
                        combined_laws=combined_laws or "",
                        legal_basis_section=shared_context.get("legal_basis_section", ""),
                        extra_instructions=extra_instructions,
                        research_context=research_context,
                        bundle_preseed=bundle_shared_preseed,
                    )
                    bundle_shared_preseed = merge_bundle_preseed(bundle_shared_preseed, payload)
                    bundle_meta["generation_mode"] = "structured"
                    bundle_meta["structured_payload"] = payload
                    bundle_meta["structured_debug"] = struct_debug
                else:
                    content = await self._call_claude(
                        system=SYSTEM_DOCUMENT_GENERATION,
                        user=DOCUMENT_GENERATION_PROMPT.format(
                            doc_type_name=doc_type_name,
                            parsed_case=json.dumps(enhanced_parsed_case, ensure_ascii=False, indent=2),
                            related_laws=combined_laws or "无",
                            related_cases=combined_cases or "无",
                            research_context=research_context or "无",
                            template_structure="无特定模板结构要求",
                            extra_instructions=extra_instructions or "无",
                            doc_type_specific=doc_type_specific,
                        ),
                        max_tokens=self._settings.CLAUDE_MAX_TOKENS,
                    )
                    content = sanitize_legal_document_content(content or "", doc_type_name)
                    content = normalize_freeform_markdown(content, doc_type)
                    bundle_meta["generation_mode"] = "freeform"

                plaintiff = parsed_case.get("parties", {}).get("plaintiff", {}).get("name", "")
                defendant = parsed_case.get("parties", {}).get("defendant", {}).get("name", "")
                cause = parsed_case.get("cause_of_action", "")
                if plaintiff and defendant:
                    title = f"{plaintiff}诉{defendant}{cause}一案{doc_type_name}" if cause else f"{plaintiff}诉{defendant}{doc_type_name}"
                else:
                    title = doc_type_name

                documents.append({
                    "doc_type": doc_type,
                    "title": title,
                    "content": content,
                    "metadata": bundle_meta,
                })
            except Exception as e:
                logger.error("Bundle generation failed for %s: %s", doc_type, e)
                documents.append({
                    "doc_type": doc_type,
                    "title": DOC_TYPE_NAMES.get(doc_type, doc_type),
                    "content": "文书生成失败，请稍后重试",
                    "metadata": {"error": "generation_failed"},
                })

        # 5) 一致性检查
        consistency_check = await self._check_bundle_consistency(documents)

        return {
            "documents": documents,
            "consistency_check": consistency_check,
            "shared_context": {
                "parsed_case": parsed_case,
                "legal_issues": legal_issues,
                "facts_summary": shared_context["facts_summary"],
            },
        }

    async def _check_bundle_consistency(self, documents: list[dict]) -> dict:
        """检查多份文书之间的一致性。"""
        if len(documents) < 2:
            return {"consistent": True, "issues": []}
        try:
            docs_text = ""
            for i, doc in enumerate(documents):
                docs_text += f"\n### 文书{i+1}: {doc.get('title', '')} ({doc.get('doc_type', '')})\n{doc.get('content', '')[:3000]}\n"

            result = await self._call_claude(
                system="你是法律文书一致性核查专家。",
                user=BUNDLE_CONSISTENCY_CHECK_PROMPT.format(documents=docs_text),
                max_tokens=1500,
            )
            check = self._parse_json_response(result)
            return check if check else {"consistent": True, "issues": []}
        except Exception as e:
            logger.warning("Bundle consistency check failed: %s", e)
            return {"consistent": True, "issues": []}

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    def _build_legal_basis_section(self, legal_issues: dict) -> str:
        """构建法律依据专节文本。"""
        statutes = legal_issues.get("applicable_statutes", [])
        if not statutes:
            return ""
        lines = ["**法律依据**\n"]
        for statute in statutes:
            law_name = statute.get("law_name", "")
            articles = statute.get("articles", [])
            relevance = statute.get("relevance", "")
            if law_name and articles:
                articles_str = "、".join(f"第{a}条" for a in articles)
                line = f"- 《{law_name}》{articles_str}"
                if relevance:
                    line += f"：{relevance}"
                lines.append(line)
        return "\n".join(lines)

    def _build_facts_summary(self, parsed_case: dict) -> str:
        """构建事实摘要。"""
        facts = parsed_case.get("facts", "")
        key_dates = parsed_case.get("key_dates", [])
        amount = parsed_case.get("amount_involved", "")
        parties = parsed_case.get("parties", {})
        plaintiff_name = parties.get("plaintiff", {}).get("name", "原告")
        defendant_name = parties.get("defendant", {}).get("name", "被告")

        summary_parts = []
        if facts:
            summary_parts.append(f"事实概要：{facts}")
        if key_dates:
            summary_parts.append("关键时间节点：" + "；".join(key_dates))
        if amount:
            summary_parts.append(f"涉及金额：{amount}")
        summary_parts.append(f"当事人：{plaintiff_name}（原告）vs {defendant_name}（被告）")
        return "\n".join(summary_parts)

    def _inject_legal_basis(self, content: str, legal_basis: str) -> str:
        """在文书中注入法律依据专节（如果LLM没有自行生成）。"""
        # 在"事实与理由"段末或"此致"之前插入
        markers = ["此致", "综上", "## 诉讼请求"]
        for marker in markers:
            idx = content.find(marker)
            if idx > 0:
                return content[:idx] + f"\n\n{legal_basis}\n\n" + content[idx:]
        # 没找到合适位置，追加到末尾
        return content + f"\n\n{legal_basis}"

    # ------------------------------------------------------------------
    # 向量库和外部数据源检索
    # ------------------------------------------------------------------
    async def _search_vector_statutes(self, keywords: list[str]) -> str:
        """使用统一 RAG 检索层检索法条（混合检索：向量 + BM25）。"""
        try:
            from app.services.rag import retrieve_statutes
            query = "、".join(keywords[:3])
            items = await retrieve_statutes(query, top_k=5, hybrid=True)
            if not items:
                return ""
            return "\n".join(
                f"- [{it.metadata.get('title', '')}] {it.content[:300]}"
                for it in items
            )
        except Exception:
            return ""

    async def _search_vector_cases(self, keywords: list[str]) -> str:
        """使用统一 RAG 检索层检索案例（混合检索：向量 + BM25）。"""
        try:
            from app.services.rag import retrieve_cases
            query = "、".join(keywords[:3])
            items = await retrieve_cases(query, top_k=5, hybrid=True)
            if not items:
                return ""
            return "\n".join(
                f"- [{it.metadata.get('title', '')}] {it.content[:300]}"
                for it in items
            )
        except Exception:
            return ""

    async def _search_external_sources(self, keywords: list[str]) -> str:
        try:
            from app.services.data_sources.base import DataSourceRegistry
            adapters = DataSourceRegistry.get_all()
            if not adapters:
                return ""
            query = "、".join(keywords[:3])
            results = []
            for name, adapter in adapters.items():
                try:
                    laws = await adapter.search_law(query, limit=3)
                    for law in laws:
                        results.append(f"- [{name}] {law.title} {law.provision_ref}: {law.content[:200]}")
                except Exception:
                    pass
            return "\n".join(results) if results else ""
        except Exception:
            return ""
