"""Tests for Pydantic schema validation (app.schemas).

Covers: CaseCreate, DocumentGenerate, SearchQuery, DocumentExport,
LawVerifyRequest field validators and constraints.
"""

import pytest
from pydantic import ValidationError

from app.schemas.case import CaseCreate
from app.schemas.document import DocumentGenerate, DocumentExport
from app.schemas.search import SearchQuery
from app.schemas.verification import LawVerifyRequest


# ---------------------------------------------------------------------------
# CaseCreate
# ---------------------------------------------------------------------------


class TestCaseCreate:
    """Tests for CaseCreate schema validators."""

    def test_valid_case(self):
        case = CaseCreate(
            title="测试案件标题",
            case_type="民事",
            description="这是一个描述",
        )
        assert case.title == "测试案件标题"
        assert case.case_type == "民事"

    def test_title_stripped(self):
        """Leading/trailing whitespace should be stripped from the title."""
        case = CaseCreate(title="  有效标题  ", case_type="刑事")
        assert case.title == "有效标题"

    def test_title_empty_raises(self):
        """An empty or whitespace-only title should be rejected."""
        with pytest.raises(ValidationError, match="案件标题不能为空"):
            CaseCreate(title="", case_type="民事")

    def test_title_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="案件标题不能为空"):
            CaseCreate(title="   ", case_type="民事")

    def test_title_exceeds_200_raises(self):
        """Title longer than 200 characters should be rejected."""
        long_title = "A" * 201
        with pytest.raises(ValidationError, match="案件标题不能超过200字"):
            CaseCreate(title=long_title, case_type="民事")

    def test_title_exactly_200_ok(self):
        """Title of exactly 200 characters should be accepted."""
        case = CaseCreate(title="B" * 200, case_type="民事")
        assert len(case.title) == 200

    def test_description_exceeds_50000_raises(self):
        """Description longer than 50000 characters should be rejected."""
        long_desc = "D" * 50001
        with pytest.raises(ValidationError, match="案件描述不能超过50000字"):
            CaseCreate(title="标题", case_type="民事", description=long_desc)

    def test_description_exactly_50000_ok(self):
        case = CaseCreate(title="标题", case_type="民事", description="D" * 50000)
        assert len(case.description) == 50000

    def test_description_none_ok(self):
        case = CaseCreate(title="标题", case_type="民事", description=None)
        assert case.description is None

    def test_case_type_empty_raises(self):
        with pytest.raises(ValidationError, match="案件类型不能为空"):
            CaseCreate(title="标题", case_type="")

    def test_case_type_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="案件类型不能为空"):
            CaseCreate(title="标题", case_type="   ")

    def test_case_type_stripped(self):
        case = CaseCreate(title="标题", case_type="  民事  ")
        assert case.case_type == "民事"

    def test_optional_fields_default_to_none(self):
        case = CaseCreate(title="标题", case_type="民事")
        assert case.case_number is None
        assert case.court is None
        assert case.plaintiff is None
        assert case.defendant is None
        assert case.description is None
        assert case.filing_date is None
        assert case.hearing_dates is None
        assert case.deadline_dates is None


# ---------------------------------------------------------------------------
# DocumentGenerate
# ---------------------------------------------------------------------------


class TestDocumentGenerate:
    """Tests for DocumentGenerate schema validators."""

    def test_valid_document(self):
        doc = DocumentGenerate(
            type="complaint",
            case_facts="原告张三与被告李四签订借款合同。",
        )
        assert doc.type == "complaint"
        assert doc.case_facts == "原告张三与被告李四签订借款合同。"

    def test_case_facts_empty_raises(self):
        with pytest.raises(ValidationError, match="案件事实不能为空"):
            DocumentGenerate(type="complaint", case_facts="")

    def test_case_facts_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="案件事实不能为空"):
            DocumentGenerate(type="complaint", case_facts="   ")

    def test_case_facts_exceeds_50000_raises(self):
        with pytest.raises(ValidationError, match="案件事实不能超过50000字"):
            DocumentGenerate(type="complaint", case_facts="F" * 50001)

    def test_case_facts_exactly_50000_ok(self):
        doc = DocumentGenerate(type="complaint", case_facts="F" * 50000)
        assert len(doc.case_facts) == 50000

    def test_case_facts_stripped(self):
        doc = DocumentGenerate(type="complaint", case_facts="  有效事实  ")
        assert doc.case_facts == "有效事实"

    def test_type_empty_raises(self):
        with pytest.raises(ValidationError, match="文书类型不能为空"):
            DocumentGenerate(type="", case_facts="事实")

    def test_type_stripped(self):
        doc = DocumentGenerate(type="  complaint  ", case_facts="事实")
        assert doc.type == "complaint"

    def test_optional_fields_default(self):
        doc = DocumentGenerate(type="complaint", case_facts="事实")
        assert doc.case_id is None
        assert doc.template_id is None
        assert doc.title is None
        assert doc.extra_instructions is None
        assert doc.research_report_ids is None


# ---------------------------------------------------------------------------
# SearchQuery
# ---------------------------------------------------------------------------


class TestSearchQuery:
    """Tests for SearchQuery schema validators."""

    def test_valid_query(self):
        sq = SearchQuery(query="合同违约")
        assert sq.query == "合同违约"
        assert sq.top_k == 20
        assert sq.result_type == "all"

    def test_query_stripped(self):
        sq = SearchQuery(query="  合同违约  ")
        assert sq.query == "合同违约"

    def test_query_empty_raises(self):
        with pytest.raises(ValidationError, match="搜索内容不能为空"):
            SearchQuery(query="")

    def test_query_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="搜索内容不能为空"):
            SearchQuery(query="   ")

    def test_query_exceeds_2000_raises(self):
        with pytest.raises(ValidationError, match="搜索内容不能超过2000字"):
            SearchQuery(query="Q" * 2001)

    def test_query_exactly_2000_ok(self):
        sq = SearchQuery(query="Q" * 2000)
        assert len(sq.query) == 2000

    def test_top_k_minimum(self):
        sq = SearchQuery(query="test", top_k=1)
        assert sq.top_k == 1

    def test_top_k_maximum(self):
        sq = SearchQuery(query="test", top_k=100)
        assert sq.top_k == 100

    def test_top_k_zero_raises(self):
        with pytest.raises(ValidationError, match="top_k 必须在 1-100 之间"):
            SearchQuery(query="test", top_k=0)

    def test_top_k_negative_raises(self):
        with pytest.raises(ValidationError, match="top_k 必须在 1-100 之间"):
            SearchQuery(query="test", top_k=-1)

    def test_top_k_101_raises(self):
        with pytest.raises(ValidationError, match="top_k 必须在 1-100 之间"):
            SearchQuery(query="test", top_k=101)

    def test_top_k_default_is_20(self):
        sq = SearchQuery(query="test")
        assert sq.top_k == 20

    def test_result_type_default_all(self):
        sq = SearchQuery(query="test")
        assert sq.result_type == "all"

    def test_sources_default_none(self):
        sq = SearchQuery(query="test")
        assert sq.sources is None


# ---------------------------------------------------------------------------
# DocumentExport
# ---------------------------------------------------------------------------


class TestDocumentExport:
    """Tests for DocumentExport schema format validator."""

    @pytest.mark.parametrize("fmt", ["docx", "markdown", "html", "pdf"])
    def test_valid_format(self, fmt):
        export = DocumentExport(format=fmt)
        assert export.format == fmt

    def test_default_format_is_docx(self):
        export = DocumentExport()
        assert export.format == "docx"

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError, match="不支持的导出格式"):
            DocumentExport(format="txt")

    def test_invalid_format_json_raises(self):
        with pytest.raises(ValidationError, match="不支持的导出格式"):
            DocumentExport(format="json")

    def test_invalid_format_empty_raises(self):
        with pytest.raises(ValidationError, match="不支持的导出格式"):
            DocumentExport(format="")

    def test_case_insensitive_rejection(self):
        """Format validation should be case-sensitive."""
        with pytest.raises(ValidationError, match="不支持的导出格式"):
            DocumentExport(format="DOCX")


# ---------------------------------------------------------------------------
# LawVerifyRequest
# ---------------------------------------------------------------------------


class TestLawVerifyRequest:
    """Tests for LawVerifyRequest schema validators."""

    def test_valid_request(self):
        req = LawVerifyRequest(
            law_name="民法典",
            article_number="第584条",
            content="当事人一方不履行合同义务或者履行合同义务不符合约定...",
        )
        assert req.law_name == "民法典"
        assert req.article_number == "第584条"

    def test_law_name_empty_raises(self):
        with pytest.raises(ValidationError, match="法律名称不能为空"):
            LawVerifyRequest(law_name="", article_number="第1条", content="内容")

    def test_law_name_whitespace_raises(self):
        with pytest.raises(ValidationError, match="法律名称不能为空"):
            LawVerifyRequest(law_name="   ", article_number="第1条", content="内容")

    def test_law_name_stripped(self):
        req = LawVerifyRequest(law_name="  民法典  ", article_number="第1条", content="内容")
        assert req.law_name == "民法典"

    def test_article_number_empty_raises(self):
        with pytest.raises(ValidationError, match="条款号不能为空"):
            LawVerifyRequest(law_name="民法典", article_number="", content="内容")

    def test_article_number_whitespace_raises(self):
        with pytest.raises(ValidationError, match="条款号不能为空"):
            LawVerifyRequest(law_name="民法典", article_number="   ", content="内容")

    def test_article_number_stripped(self):
        req = LawVerifyRequest(law_name="民法典", article_number="  第1条  ", content="内容")
        assert req.article_number == "第1条"

    def test_content_exceeds_10000_raises(self):
        with pytest.raises(ValidationError, match="法条内容不能超过10000字"):
            LawVerifyRequest(
                law_name="民法典",
                article_number="第1条",
                content="C" * 10001,
            )

    def test_content_exactly_10000_ok(self):
        req = LawVerifyRequest(
            law_name="民法典",
            article_number="第1条",
            content="C" * 10000,
        )
        assert len(req.content) == 10000
