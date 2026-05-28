"""模板元数据与抽取 schema 合并。"""

from types import SimpleNamespace

from app.services.docgen.template_helpers import enrich_template_dict
from app.services.docgen.template_meta import supports_structured_generation
from app.services.docgen.template_structure import build_extraction_schema, structure_to_variables


def test_structure_to_variables():
    sections = [
        {
            "name": "申请人",
            "fields": [{"key": "applicant_name", "label": "姓名", "required": True}],
        },
    ]
    vars_ = structure_to_variables(sections)
    assert len(vars_) == 1
    assert vars_[0]["name"] == "applicant_name"


def test_build_extraction_schema_merges_template_labels():
    template = SimpleNamespace(
        structure={
            "sections": [
                {
                    "name": "仲裁请求",
                    "fields": [{"key": "requests", "label": "仲裁请求明细"}],
                },
            ],
        },
    )
    schema = build_extraction_schema("application", template)
    assert "requests" in schema
    assert "仲裁请求" in schema["requests"]


def test_enrich_template_dict_structured():
    tmpl = SimpleNamespace(
        type="application",
        structure={"sections": [{"name": "申请人", "fields": [{"key": "applicant_name", "label": "姓名"}]}]},
        format_rules={"generation_mode": "structured", "word_export": "native"},
    )
    meta = enrich_template_dict(tmpl)
    assert meta["supports_structured"] is True
    assert meta["generation_mode"] == "structured"
    assert "申请人" in meta["sections_preview"]


def test_supports_structured_generation():
    assert supports_structured_generation("application") is True
    assert supports_structured_generation("other") is False
