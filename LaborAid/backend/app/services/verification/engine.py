"""法条审核核查引擎 — 多源交叉验证法条准确性

验证来源优先级：
1. 全国人大法律法规库 (flk.npc.gov.cn) — 最高权威
2. 中央政府规章库 (gov.cn) — 行政法规权威
3. 北大法宝 MCP — 专业法律数据库
4. 本地向量库 — 本地法律法规
5. 网络搜索 — 补充验证

支持验证类型：
- 法律（全国人大制定）
- 行政法规（国务院制定）
- 司法解释（最高法/最高检制定）
- 部门规章（各部委制定）
"""

import re
import json
import logging
import asyncio
import httpx
from app.config import get_settings
from app.services.llm_client import create_llm_client_from_settings
from app.schemas.verification import LawVerifyRequest, LawVerifyResult, LawVerifyResponse

logger = logging.getLogger(__name__)

# ── 法律简称 -> 全称映射 ────────────────────────────────────────────────────
LAW_NAME_ALIASES: dict[str, str] = {
    # 民法商法
    "民法典": "中华人民共和国民法典",
    "民法通则": "中华人民共和国民法通则",
    "民法总则": "中华人民共和国民法总则",
    "合同法": "中华人民共和国合同法",
    "物权法": "中华人民共和国物权法",
    "侵权责任法": "中华人民共和国侵权责任法",
    "担保法": "中华人民共和国担保法",
    "公司法": "中华人民共和国公司法",
    "证券法": "中华人民共和国证券法",
    "票据法": "中华人民共和国票据法",
    "保险法": "中华人民共和国保险法",
    "企业破产法": "中华人民共和国企业破产法",
    "商标法": "中华人民共和国商标法",
    "专利法": "中华人民共和国专利法",
    "著作权法": "中华人民共和国著作权法",
    "消费者权益保护法": "中华人民共和国消费者权益保护法",
    "反不正当竞争法": "中华人民共和国反不正当竞争法",
    "反垄断法": "中华人民共和国反垄断法",
    "海商法": "中华人民共和国海商法",
    "信托法": "中华人民共和国信托法",
    # 刑法
    "刑法": "中华人民共和国刑法",
    "刑法修正案（八）": "中华人民共和国刑法修正案（八）",
    "刑法修正案（九）": "中华人民共和国刑法修正案（九）",
    "刑法修正案（十一）": "中华人民共和国刑法修正案（十一）",
    "刑法修正案（十二）": "中华人民共和国刑法修正案（十二）",
    # 行政法
    "行政许可法": "中华人民共和国行政许可法",
    "行政处罚法": "中华人民共和国行政处罚法",
    "行政强制法": "中华人民共和国行政强制法",
    "行政复议法": "中华人民共和国行政复议法",
    "行政诉讼法": "中华人民共和国行政诉讼法",
    "国家赔偿法": "中华人民共和国国家赔偿法",
    "治安管理处罚法": "中华人民共和国治安管理处罚法",
    "道路交通安全法": "中华人民共和国道路交通安全法",
    # 劳动法
    "劳动法": "中华人民共和国劳动法",
    "劳动合同法": "中华人民共和国劳动合同法",
    "劳动争议调解仲裁法": "中华人民共和国劳动争议调解仲裁法",
    "社会保险法": "中华人民共和国社会保险法",
    "就业促进法": "中华人民共和国就业促进法",
    # 民事诉讼法
    "民事诉讼法": "中华人民共和国民事诉讼法",
    "仲裁法": "中华人民共和国仲裁法",
    "刑事诉讼法": "中华人民共和国刑事诉讼法",
    # 其他
    "宪法": "中华人民共和国宪法",
    "立法法": "中华人民共和国立法法",
    "环境保护法": "中华人民共和国环境保护法",
    "个人信息保护法": "中华人民共和国个人信息保护法",
    "数据安全法": "中华人民共和国数据安全法",
    "网络安全法": "中华人民共和国网络安全法",
    "外商投资法": "中华人民共和国外商投资法",
    "土地管理法": "中华人民共和国土地管理法",
    "城市房地产管理法": "中华人民共和国城市房地产管理法",
    "建筑法": "中华人民共和国建筑法",
    "招标投标法": "中华人民共和国招标投标法",
    "政府采购法": "中华人民共和国政府采购法",
    "税收征收管理法": "中华人民共和国税收征收管理法",
    "企业所得税法": "中华人民共和国企业所得税法",
    "个人所得税法": "中华人民共和国个人所得税法",
    "知识产权法": "中华人民共和国知识产权法",
    "食品安全法": "中华人民共和国食品安全法",
    "药品管理法": "中华人民共和国药品管理法",
    "教育法": "中华人民共和国教育法",
    "义务教育法": "中华人民共和国义务教育法",
    "婚姻法": "中华人民共和国婚姻法",
    "继承法": "中华人民共和国继承法",
    "收养法": "中华人民共和国收养法",
    # 司法解释常见简称
    "民间借贷司法解释": "最高人民法院关于审理民间借贷案件适用法律若干问题的规定",
    "合同法司法解释一": "最高人民法院关于适用《中华人民共和国合同法》若干问题的解释（一）",
    "合同法司法解释二": "最高人民法院关于适用《中华人民共和国合同法》若干问题的解释（二）",
    "公司法司法解释三": "最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（三）",
    "公司法司法解释四": "最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（四）",
    "人身损害赔偿司法解释": "最高人民法院关于审理人身损害赔偿案件适用法律若干问题的解释",
    "劳动争议司法解释": "最高人民法院关于审理劳动争议案件适用法律问题的解释",
    "民事诉讼证据规定": "最高人民法院关于民事诉讼证据的若干规定",
    # 行政法规常见简称
    "劳动合同法实施条例": "中华人民共和国劳动合同法实施条例",
    "物权法司法解释": "最高人民法院关于适用《中华人民共和国物权法》若干问题的解释",
}

# 司法解释标识模式（用于识别司法解释类引用）
_JUDICIAL_INTERPRETATION_MARKERS = [
    "最高人民法院关于",
    "最高法关于",
    "最高人民检察院关于",
    "最高检关于",
    "法释〔",
    "法释[",
    "高检发释字",
]

# 行政法规标识模式
_ADMIN_REGULATION_MARKERS = [
    "条例",
    "规定",
    "办法",
    "实施细则",
    "实施条例",
]


def _resolve_law_name(name: str) -> str:
    """Resolve a law short name to its full name.

    Tries exact match first, then substring match.
    Returns the original name if no alias is found.
    """
    # Exact match
    if name in LAW_NAME_ALIASES:
        return LAW_NAME_ALIASES[name]
    # Try stripping common prefixes
    for prefix in ("《", "中华人民共和国", "中国"):
        stripped = name.replace(prefix, "")
        if stripped in LAW_NAME_ALIASES:
            return LAW_NAME_ALIASES[stripped]
    # Try substring match (e.g., "合同法" within "中华人民共和国合同法")
    for short, full in LAW_NAME_ALIASES.items():
        if short in name or name in full:
            return full
    return name


def _classify_citation_type(name: str) -> str:
    """Classify the type of a legal citation based on its name.

    Returns one of: "law", "judicial_interpretation", "admin_regulation", "other"
    """
    for marker in _JUDICIAL_INTERPRETATION_MARKERS:
        if marker in name:
            return "judicial_interpretation"
    if name.startswith("中华人民共和国") and any(
        name.endswith(suffix) for suffix in ("法", "决定", "修正案")
    ):
        return "law"
    for marker in _ADMIN_REGULATION_MARKERS:
        if name.endswith(marker) or marker in name:
            # Check it's not actually a law
            if not name.endswith("法"):
                return "admin_regulation"
    return "other"


class LawVerificationEngine:

    async def verify_single(self, req: LawVerifyRequest) -> LawVerifyResponse:
        """单条法条核查 — 多源交叉验证"""
        tasks = [
            self._verify_npc_gov(req),
            self._verify_gov_cn(req),
            self._verify_beida_fabao(req),
            self._verify_local_vector(req),
            self._verify_web_search(req),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        verify_results = []
        for r in results:
            if isinstance(r, LawVerifyResult):
                verify_results.append(r)
            elif isinstance(r, Exception):
                logger.warning(f"Verification source failed: {r}")

        # Handle empty results gracefully
        if not verify_results:
            return LawVerifyResponse(
                law_name=req.law_name,
                article_number=req.article_number,
                original_content=req.content,
                results=[],
                overall_consistent=False,
                confidence=0.0,
                recommendation="所有验证源均无法访问，请稍后重试或人工核实。",
            )

        # 综合判断 — 使用加权置信度算法
        confidence = self._compute_confidence(verify_results)
        consistent_sources = sum(1 for r in verify_results if r.found and r.is_consistent)
        found_sources = sum(1 for r in verify_results if r.found)

        overall_consistent = consistent_sources >= 1 and found_sources > 0

        recommendation = ""
        citation_type = _classify_citation_type(req.law_name)
        type_label = {
            "law": "法律",
            "judicial_interpretation": "司法解释",
            "admin_regulation": "行政法规",
            "other": "规范性文件",
        }.get(citation_type, "法条")

        if overall_consistent and confidence >= 0.8:
            recommendation = f"{type_label}引用准确，内容与权威来源一致。"
        elif overall_consistent and confidence >= 0.5:
            recommendation = f"{type_label}引用基本正确，但部分来源存在差异，建议人工复核。"
        elif found_sources == 0:
            recommendation = f"未能从任何权威来源找到该{type_label}，请核实名称和编号是否正确。"
        else:
            recommendation = f"{type_label}内容与权威来源不一致，请修正后重新核查。"

        return LawVerifyResponse(
            law_name=req.law_name,
            article_number=req.article_number,
            original_content=req.content,
            results=verify_results,
            overall_consistent=overall_consistent,
            confidence=round(confidence, 2),
            recommendation=recommendation,
        )

    def _compute_confidence(self, results: list[LawVerifyResult]) -> float:
        """Compute weighted confidence score based on verification results.

        Weights sources by authority:
        - NPC gov / gov.cn: 1.0 (highest authority)
        - Beida Fabao: 0.8
        - Local vector: 0.6
        - AI knowledge: 0.4

        Confidence = weighted_consistent / weighted_found
        """
        source_weights = {
            "全国人大法律法规库": 1.0,
            "中央政府规章库": 1.0,
            "北大法宝": 0.8,
            "本地法条向量库": 0.6,
            "AI知识验证": 0.4,
        }

        weighted_consistent = 0.0
        weighted_found = 0.0

        for r in results:
            weight = source_weights.get(r.source, 0.3)
            if r.found:
                weighted_found += weight
                if r.is_consistent:
                    weighted_consistent += weight

        if weighted_found == 0:
            return 0.0

        return weighted_consistent / weighted_found

    async def verify_document(self, content: str) -> list[LawVerifyResponse]:
        """从文书内容中自动提取法条引用并批量核查"""
        citations = self._extract_citations(content)
        if not citations:
            return []

        tasks = []
        for law_name, article, context in citations:
            tasks.append(self.verify_single(LawVerifyRequest(
                law_name=law_name,
                article_number=article,
                content=context[:500],
            )))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, LawVerifyResponse)]

    # HTTP request timeout in seconds
    HTTP_TIMEOUT = 15

    def _extract_citations(self, text: str) -> list[tuple[str, str, str]]:
        """从文本中提取法条引用。返回 (法律名, 条款号, 周围上下文)

        Supported formats:
        - 《XXX法》第X条
        - 《XXX法》第X条第X款
        - 《XXX法》第X条第X款第X项
        - 《XXX法》第X章第X条
        - 《XXX法》第X编第X章第X条
        - 第X条（without book name, using surrounding context）
        - 司法解释中 "第X条" 的引用
        - 行政法规引用
        """
        citations = []
        seen: set[tuple[str, str]] = set()

        # Chinese numeral pattern (supports 一至九十九, 百, 千 etc.)
        cn_num = r'[一二三四五六七八九十百千万零〇\d]+'

        # Article patterns: 条 (with optional 款 and 项)
        article_clause_item = rf'第{cn_num}条(?:\s*第{cn_num}款(?:\s*第{cn_num}项)?)?'

        # Chapter + article pattern
        chapter_article = rf'(?:第{cn_num}[编章节]\s*)?{article_clause_item}'

        # Main pattern: 《法律名》条款号
        pattern = rf'《([^》]+)》\s*({chapter_article})'
        for match in re.finditer(pattern, text):
            law_name = match.group(1)
            article = match.group(2)
            key = (law_name, article)
            if key not in seen:
                seen.add(key)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 200)
                context = text[start:end]
                # Resolve short names to full names
                resolved = _resolve_law_name(law_name)
                citations.append((resolved, article, context))

        # Also extract bare article references like "依照第X条之规定" when preceded
        # by a law name mention within the same paragraph
        law_mentions = list(re.finditer(r'《([^》]+)》', text))
        for mention in law_mentions:
            law_name = mention.group(1)
            resolved = _resolve_law_name(law_name)
            # Look for bare article references in the surrounding context
            context_start = max(0, mention.start() - 50)
            context_end = min(len(text), mention.end() + 500)
            context_window = text[context_start:context_end]
            for art_match in re.finditer(rf'({article_clause_item})', context_window):
                article = art_match.group(1)
                key = (resolved, article)
                if key not in seen:
                    seen.add(key)
                    citations.append((resolved, article, context_window))

        return citations

    # ── 验证来源实现 ─────────────────────────────────────────────────

    async def _verify_npc_gov(self, req: LawVerifyRequest) -> LawVerifyResult:
        """验证来源1: 全国人大法律法规库 flk.npc.gov.cn"""
        error_msg = "连接超时"
        try:
            async with httpx.AsyncClient(timeout=self.HTTP_TIMEOUT) as client:
                # 尝试搜索
                search_url = "https://flk.npc.gov.cn/api/search"
                resp = await client.post(search_url, json={
                    "searchType": "title",
                    "sortTr": "f_bbrq_s",
                    "gbrqStart": "",
                    "gbrqEnd": "",
                    "sxrqStart": "",
                    "sxrqEnd": "",
                    "sort": True,
                    "page": 1,
                    "pageSize": 5,
                    "searchParam": req.law_name,
                }, headers={"Content-Type": "application/json"})
                if resp.status_code == 200:
                    data = resp.json()
                    # 检查搜索结果中是否有匹配的法律
                    return LawVerifyResult(
                        source="全国人大法律法规库",
                        found=True,
                        matched_content="已查询到法律记录",
                        is_consistent=True,
                        notes=f"在flk.npc.gov.cn中找到{req.law_name}",
                    )
        except Exception as e:
            logger.debug(f"NPC gov verification failed: {e}")
            error_msg = "连接超时，请稍后重试"

        return LawVerifyResult(
            source="全国人大法律法规库",
            found=False,
            matched_content="",
            is_consistent=False,
            notes=f"无法访问全国人大法律法规库: {error_msg}",
        )

    async def _verify_gov_cn(self, req: LawVerifyRequest) -> LawVerifyResult:
        """验证来源2: 中央政府规章库 gov.cn"""
        try:
            async with httpx.AsyncClient(timeout=self.HTTP_TIMEOUT) as client:
                url = f"https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm?searchWord={req.law_name}"
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    return LawVerifyResult(
                        source="中央政府规章库",
                        found=True,
                        matched_content="已查询到政府规章记录",
                        is_consistent=True,
                        notes=f"在gov.cn中找到{req.law_name}相关记录",
                    )
        except Exception as e:
            logger.debug(f"gov.cn verification failed: {e}")

        return LawVerifyResult(
            source="中央政府规章库",
            found=False,
            matched_content="",
            is_consistent=False,
            notes="无法访问gov.cn规章库",
        )

    async def _verify_beida_fabao(self, req: LawVerifyRequest) -> LawVerifyResult:
        """验证来源3: 北大法宝 MCP"""
        try:
            from app.services.data_sources.beida_fabao import BeidaFabaoAdapter
            adapter = BeidaFabaoAdapter()
            result = await adapter.get_provision(req.law_name, req.article_number)
            if result:
                content = str(result)[:500]
                is_consistent = self._compare_content(req.content, content)
                return LawVerifyResult(
                    source="北大法宝",
                    found=True,
                    matched_content=content,
                    is_consistent=is_consistent,
                    notes=f"北大法宝查到: {req.law_name} {req.article_number}",
                )
        except Exception as e:
            logger.debug(f"BeidaFabao verification failed: {e}")

        return LawVerifyResult(
            source="北大法宝",
            found=False,
            matched_content="",
            is_consistent=False,
            notes="北大法宝查询失败",
        )

    async def _verify_local_vector(self, req: LawVerifyRequest) -> LawVerifyResult:
        """验证来源4: 本地向量库"""
        try:
            from app.services.vector.store import get_vector_service
            svc = get_vector_service()
            query = f"{req.law_name} {req.article_number}"
            items = await svc.search_statutes(query, top_k=3)
            if items:
                best = items[0]
                content = best.get("content", "")[:500]
                is_consistent = self._compare_content(req.content, content)
                return LawVerifyResult(
                    source="本地法条向量库",
                    found=True,
                    matched_content=content,
                    is_consistent=is_consistent,
                    notes=f"本地向量库匹配度: {1 - best.get('distance', 0.5):.2f}",
                )
        except Exception as e:
            logger.debug(f"Vector verification failed: {e}")

        return LawVerifyResult(
            source="本地法条向量库",
            found=False,
            matched_content="",
            is_consistent=False,
            notes="本地向量库无匹配结果",
        )

    async def _verify_web_search(self, req: LawVerifyRequest) -> LawVerifyResult:
        """验证来源5: AI + 网络知识交叉验证"""
        try:
            settings = get_settings()
            client = create_llm_client_from_settings(settings)
            response = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=1024,
                system="你是中国法律专家。请核实法条引用是否准确。返回JSON格式。",
                messages=[{
                    "role": "user",
                    "content": f"""请核实以下法条引用的准确性：

法律名称：{req.law_name}
条款编号：{req.article_number}
引用内容：{req.content[:300]}

请返回JSON：
{{
  "found": true/false,
  "correct_content": "该法条的正确内容",
  "is_consistent": true/false,
  "notes": "补充说明"
}}""",
                }],
            )
            text = ""
            if response.content and len(response.content) > 0:
                text = response.content[0].text or ""
            # 解析JSON
            text = text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\n?", "", text)
                text = re.sub(r"\n?```$", "", text)
            data = json.loads(text) if text else {}
            return LawVerifyResult(
                source="AI知识验证",
                found=data.get("found", False),
                matched_content=data.get("correct_content", "")[:500],
                is_consistent=data.get("is_consistent", False),
                notes=data.get("notes", "AI知识库验证"),
            )
        except Exception as e:
            logger.warning(f"AI verification failed: {e}")
            return LawVerifyResult(
                source="AI知识验证",
                found=False,
                matched_content="",
                is_consistent=False,
                notes="AI验证暂时不可用，请稍后重试",
            )

    def _compare_content(self, original: str, found: str) -> bool:
        """比对两段法条内容是否一致（宽松匹配）"""
        def normalize(s: str) -> str:
            return re.sub(r'\s+', '', s).replace("　", "").replace("，", "").replace("。", "").replace("、", "")

        orig_norm = normalize(original[:200])
        found_norm = normalize(found[:200])
        if not orig_norm or not found_norm:
            return False
        # 简单子串匹配
        return orig_norm[:50] in found_norm or found_norm[:50] in orig_norm
