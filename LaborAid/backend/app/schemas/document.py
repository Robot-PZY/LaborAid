from datetime import datetime
from pydantic import BaseModel, field_validator


class TemplateCreate(BaseModel):
    name: str
    type: str
    description: str | None = None
    structure: dict
    ai_prompt: str
    format_rules: dict | None = None
    variables: list[dict] | None = None
    is_public: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "民事起诉状模板",
                    "type": "complaint",
                    "description": "标准民事起诉状模板",
                    "structure": {"sections": [{"name": "当事人信息", "required": True}]},
                    "ai_prompt": "根据案件信息生成民事起诉状：{case_facts}",
                    "is_public": False,
                }
            ]
        }
    }


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    structure: dict | None = None
    ai_prompt: str | None = None
    format_rules: dict | None = None
    variables: list[dict] | None = None
    is_public: bool | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"name": "更新后的模板名", "description": "更新后的描述"}
            ]
        }
    }


class TemplateOut(BaseModel):
    id: int
    name: str
    type: str
    description: str | None
    structure: dict
    ai_prompt: str
    format_rules: dict | None
    variables: list | dict
    is_public: bool
    owner_id: int | None
    created_at: datetime
    updated_at: datetime
    # 由 template_helpers.enrich_template_dict 填充（列表/详情 API）
    sections_preview: list[str] = []
    field_count: int = 0
    supports_structured: bool = False
    category: str | None = None
    generation_mode: str | None = None
    word_export_mode: str | None = None

    model_config = {"from_attributes": True}


class DocumentGenerate(BaseModel):
    case_id: int | None = None
    template_id: int | None = None
    type: str
    title: str | None = None
    case_facts: str
    extra_instructions: str | None = None
    research_report_ids: list[int] | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "complaint",
                    "title": "民事起诉状",
                    "case_facts": "原告张三与被告李四于2024年签订借款合同，被告未按期还款。",
                    "extra_instructions": "请重点引用《民法典》相关规定",
                }
            ]
        }
    }

    @field_validator("type")
    @classmethod
    def type_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("文书类型不能为空")
        return v.strip()

    @field_validator("case_facts")
    @classmethod
    def case_facts_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("案件事实不能为空")
        if len(v.strip()) > 50000:
            raise ValueError("案件事实不能超过50000字")
        return v.strip()


class DocumentBundleGenerate(BaseModel):
    """多文书集合生成请求"""
    case_id: int | None = None
    doc_types: list[str] | None = None
    preset: str | None = None       # 预设名称（如 civil_litigation_full）
    title: str | None = None
    case_facts: str
    extra_instructions: str | None = None
    research_report_ids: list[int] | None = None


class DocumentBatchDelete(BaseModel):
    ids: list[int]

    model_config = {
        "json_schema_extra": {
            "examples": [{"ids": [1, 2, 3]}],
        }
    }


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"title": "修改后的标题", "status": "draft"}
            ]
        }
    }


class DocumentOut(BaseModel):
    id: int
    case_id: int | None
    template_id: int | None
    type: str
    title: str
    content: str
    ai_metadata: dict | None
    status: str
    version: int
    exported_path: str | None
    owner_id: int
    created_at: datetime
    updated_at: datetime
    vault_archived: bool = False

    model_config = {"from_attributes": True}


class DocumentExport(BaseModel):
    format: str = "docx"  # docx / markdown / html / pdf

    @field_validator("format")
    @classmethod
    def format_must_be_valid(cls, v):
        allowed = {"docx", "markdown", "html", "pdf"}
        if v not in allowed:
            raise ValueError(f"不支持的导出格式: {v}，允许: {', '.join(sorted(allowed))}")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"format": "docx"}
            ]
        }
    }
