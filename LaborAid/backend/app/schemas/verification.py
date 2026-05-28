"""法条审核核查 Schema"""

from pydantic import BaseModel, field_validator


class LawVerifyRequest(BaseModel):
    """法条核查请求"""
    law_name: str  # 法律名称，如"民法典"
    article_number: str  # 条款号，如"第584条"
    content: str  # 待核查的法条内容

    @field_validator("law_name")
    @classmethod
    def law_name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("法律名称不能为空")
        return v.strip()

    @field_validator("article_number")
    @classmethod
    def article_number_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("条款号不能为空")
        return v.strip()

    @field_validator("content")
    @classmethod
    def content_length_limit(cls, v):
        if v and len(v) > 10000:
            raise ValueError("法条内容不能超过10000字")
        return v


class LawVerifyResult(BaseModel):
    """单条核查结果"""
    source: str  # 来源名称
    found: bool  # 是否找到
    matched_content: str  # 找到的实际内容
    is_consistent: bool  # 是否一致
    notes: str  # 备注


class LawVerifyResponse(BaseModel):
    """法条核查响应"""
    law_name: str
    article_number: str
    original_content: str
    results: list[LawVerifyResult]
    overall_consistent: bool
    confidence: float  # 0-1 置信度
    recommendation: str  # 建议


class BatchVerifyRequest(BaseModel):
    """批量核查请求 — 从文书中自动提取法条引用"""
    document_content: str  # 文书内容


class BatchVerifyResponse(BaseModel):
    """批量核查响应"""
    total_references: int
    verified: list[LawVerifyResponse]
    warnings: list[str]
