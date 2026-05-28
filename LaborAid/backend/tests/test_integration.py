"""End-to-end integration tests for LaborAid backend workflows.

Tests full lifecycle of major features: research, document generation,
contracts, external APIs, and vector config.
"""

import json
from unittest.mock import patch, AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _template_payload(**overrides):
    """Return a valid template creation payload."""
    payload = {
        "name": "起诉状模板",
        "type": "complaint",
        "description": "民事起诉状标准模板",
        "structure": {
            "sections": [
                {"name": "当事人信息", "required": True, "fields": ["原告", "被告"]},
                {"name": "诉讼请求", "required": True, "fields": ["请求事项"]},
            ]
        },
        "ai_prompt": "根据以下案件信息生成民事起诉状：{case_facts}",
        "format_rules": {"font": "仿宋", "size": 14},
        "variables": [
            {"name": "plaintiff", "label": "原告", "type": "text", "required": True},
        ],
        "is_public": True,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# 1. Full research workflow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_research_workflow_create_get_verify(client, auth_headers):
    """Full research lifecycle: create report -> get report -> verify structure."""
    # 1) Create a research report with mocked engine
    mock_result = {
        "report": "# 研究报告\n\n## 一、法律依据\n\n根据《民法典》第469条...\n\n## 二、案例分析\n\n参考案例(2024)京0105民初1234号。",
        "sources_used": ["vector_db", "ai_knowledge"],
    }
    with patch(
        "app.services.research.engine.LegalResearchEngine.research",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        create_resp = await client.post(
            "/api/v1/research",
            headers=auth_headers,
            json={"query": "民间借贷利率上限及违约金标准"},
        )
    assert create_resp.status_code == 200
    data = create_resp.json()
    report_id = data["id"]
    assert data["query"] == "民间借贷利率上限及违约金标准"
    assert data["report"]  # report body exists
    assert "vector_db" in data["sources_used"]

    # 2) Get the report by ID and verify citations
    get_resp = await client.get(
        f"/api/v1/research/{report_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    report = get_resp.json()
    assert report["id"] == report_id
    assert "民法典" in report["report"]
    assert report["sources_used"] == ["vector_db", "ai_knowledge"]

    # 3) Verify it appears in the list
    list_resp = await client.get("/api/v1/research", headers=auth_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["id"] == report_id for item in items)

    # 4) Delete the report
    del_resp = await client.delete(
        f"/api/v1/research/{report_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 200

    # 5) Confirm deletion
    get_resp2 = await client.get(
        f"/api/v1/research/{report_id}",
        headers=auth_headers,
    )
    assert get_resp2.status_code == 404


# ---------------------------------------------------------------------------
# 2. Full document generation workflow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_generation_workflow(client, auth_headers):
    """Create case -> create template -> generate document -> quality check."""
    # 1) Create a case
    case_resp = await client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={
            "title": "张三诉李四借款合同纠纷",
            "case_type": "civil",
            "description": "原告张三与被告李四于2024年签订借款合同，约定借款10万元，年利率12%，被告未按期还款。",
        },
    )
    assert case_resp.status_code == 201
    case_id = case_resp.json()["id"]

    # 2) Create a template for the document type
    template_resp = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(name="民事起诉状模板-集成测试"),
    )
    assert template_resp.status_code == 201
    template_id = template_resp.json()["id"]

    # 3) Generate a document with mocked engine
    mock_gen_result = {
        "content": "民事起诉状\n\n原告：张三\n被告：李四\n\n诉讼请求：\n1. 判令被告偿还借款本金10万元...\n\n事实与理由：\n根据《民法典》第六百七十九条...",
        "title": "民事起诉状",
        "metadata": {"parsed_case": {"plaintiff": "张三", "defendant": "李四"}},
    }
    with patch(
        "app.services.docgen.engine.DocumentGenerationEngine.generate",
        new_callable=AsyncMock,
        return_value=mock_gen_result,
    ):
        gen_resp = await client.post(
            "/api/v1/documents/generate",
            headers=auth_headers,
            json={
                "case_id": case_id,
                "template_id": template_id,
                "type": "complaint",
                "title": "张三诉李四民事起诉状",
                "case_facts": "原告张三与被告李四于2024年签订借款合同，被告未按期还款。",
            },
        )
    assert gen_resp.status_code == 201
    doc = gen_resp.json()
    doc_id = doc["id"]
    assert doc["status"] == "generated"
    assert doc["type"] == "complaint"

    # 4) Get the document
    get_resp = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "张三诉李四民事起诉状"

    # 5) Update the document
    update_resp = await client.put(
        f"/api/v1/documents/{doc_id}",
        headers=auth_headers,
        json={"status": "draft"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "draft"

    # 6) Quality check with mocked engine
    mock_qc_result = {
        "passed": True,
        "issues": [],
        "checks": {"citation_check": True, "format_check": True},
        "quality_score": 92,
        "summary": "文书质量良好",
    }
    with patch(
        "app.services.docgen.engine.DocumentGenerationEngine.quality_check",
        new_callable=AsyncMock,
        return_value=mock_qc_result,
    ):
        qc_resp = await client.post(
            f"/api/v1/documents/{doc_id}/quality-check",
            headers=auth_headers,
        )
    assert qc_resp.status_code == 200
    qc_data = qc_resp.json()
    assert qc_data["document_id"] == doc_id
    assert qc_data["quality_check"]["passed"] is True
    assert qc_data["quality_check"]["quality_score"] == 92

    # 7) List documents for the case
    list_resp = await client.get(
        f"/api/v1/documents?case_id={case_id}",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    assert any(d["id"] == doc_id for d in list_resp.json())


# ---------------------------------------------------------------------------
# 3. Full contract workflow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_contract_upload_review_export_workflow(client, auth_headers):
    """Upload contract -> parse (mocked) -> review (mocked) -> export."""
    # 1) Create a case to associate contract with
    case_resp = await client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={
            "title": "合同纠纷案件",
            "case_type": "civil",
            "description": "房屋租赁合同纠纷",
        },
    )
    assert case_resp.status_code == 201
    case_id = case_resp.json()["id"]

    # 2) Upload a contract (mock file upload)
    contract_content = "甲方：ABC公司\n乙方：XYZ公司\n\n第一条 租赁标的...".encode("utf-8")
    mock_parse_result = {
        "text": "甲方：ABC公司\n乙方：XYZ公司\n\n第一条 租赁标的：位于北京市朝阳区的办公场所...",
        "clauses": [
            {"type": "标的", "text": "租赁标的：位于北京市朝阳区的办公场所", "position": 0},
            {"type": "租金", "text": "月租金为人民币5万元", "position": 1},
        ],
    }
    with patch(
        "app.services.contract.parser.parse_contract_document",
        new_callable=AsyncMock,
        return_value=mock_parse_result,
    ), patch(
        "app.services.llm_client.create_llm_client_from_settings",
    ):
        upload_resp = await client.post(
            "/api/v1/contracts/upload",
            headers=auth_headers,
            data={"title": "房屋租赁合同", "case_id": str(case_id)},
            files={"file": ("contract.txt", contract_content, "text/plain")},
        )
    assert upload_resp.status_code == 201
    contract = upload_resp.json()
    contract_id = contract["id"]
    assert contract["title"] == "房屋租赁合同"
    assert contract["has_file"] is True

    # 3) Review the contract with mocked engine
    mock_review_result = {
        "report": "## 合同审查报告\n\n### 风险分析\n\n1. 租金条款缺失违约金约定...",
        "risk_items": [
            {"dimension": "completeness", "level": "medium", "clause": "租金条款", "issue": "缺少违约金约定", "suggestion": "建议补充违约金条款"},
        ],
        "risk_score": 65,
    }
    with patch(
        "app.api.routers.contracts.review_contract",
        new_callable=AsyncMock,
        return_value=mock_review_result,
    ):
        review_resp = await client.post(
            f"/api/v1/contracts/{contract_id}/review",
            headers=auth_headers,
        )
    assert review_resp.status_code == 200
    reviewed = review_resp.json()
    assert reviewed["status"] == "completed"
    assert reviewed["risk_score"] == 65
    assert reviewed["review_report"] is not None

    # 4) Export the review report
    export_resp = await client.post(
        f"/api/v1/contracts/{contract_id}/export",
        headers=auth_headers,
        json={"format": "markdown"},
    )
    assert export_resp.status_code == 200

    # 5) List contracts filtered by case
    list_resp = await client.get(
        f"/api/v1/contracts?case_id={case_id}",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(c["id"] == contract_id for c in items)

    # 6) Delete the contract
    del_resp = await client.delete(
        f"/api/v1/contracts/{contract_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. External API lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_external_api_lifecycle(client, auth_headers):
    """Create -> toggle -> test -> delete an external API config."""
    with patch("app.api.routers.external_apis.register_dynamic_adapter"), \
         patch("app.api.routers.external_apis.unregister_dynamic_adapter"):
        # 1) Create an external API
        create_resp = await client.post(
            "/api/v1/external-apis",
            headers=auth_headers,
            json={
                "name": "测试法律API",
                "description": "用于集成测试的法律数据库API",
                "base_url": "https://legal-api.example.com",
                "auth_type": "bearer",
                "auth_token": "test-secret-token-12345",
                "search_law_path": "/v1/search/law",
                "search_law_method": "POST",
                "search_case_path": "/v1/search/case",
                "search_case_method": "POST",
                "is_enabled": True,
                "category": "法律数据库",
                "response_mapping": json.dumps({
                    "law": {"id": "id", "title": "title", "content": "text"},
                    "case": {"id": "id", "title": "title", "content": "summary"},
                }),
            },
        )
        assert create_resp.status_code == 201
        api_data = create_resp.json()
        api_id = api_data["id"]
        assert api_data["name"] == "测试法律API"
        assert api_data["is_enabled"] is True
        assert "test-" not in api_data["auth_token_masked"]  # token must be masked

        # 2) Toggle the API (disable it)
        toggle_resp = await client.post(
            f"/api/v1/external-apis/{api_id}/toggle",
            headers=auth_headers,
        )
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["is_enabled"] is False

        # 3) Toggle again (re-enable)
        toggle_resp2 = await client.post(
            f"/api/v1/external-apis/{api_id}/toggle",
            headers=auth_headers,
        )
        assert toggle_resp2.status_code == 200
        assert toggle_resp2.json()["is_enabled"] is True

        # 4) Test the API connection (mocked health check)
        mock_adapter = MagicMock()
        mock_adapter.health_check = AsyncMock(return_value=True)
        mock_adapter.aclose = AsyncMock()
        with patch(
            "app.services.data_sources.dynamic_adapter.DynamicExternalApiAdapter",
            return_value=mock_adapter,
        ):
            test_resp = await client.post(
                "/api/v1/external-apis/test",
                headers=auth_headers,
                json={"api_id": api_id},
            )
        assert test_resp.status_code == 200
        test_data = test_resp.json()
        assert test_data["success"] is True
        assert "延迟" in test_data["message"]

        # 5) Update the API
        update_resp = await client.put(
            f"/api/v1/external-apis/{api_id}",
            headers=auth_headers,
            json={"name": "已更新API", "description": "更新后的描述"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "已更新API"

        # 6) Verify it appears in list
        list_resp = await client.get("/api/v1/external-apis", headers=auth_headers)
        assert list_resp.status_code == 200
        assert any(a["id"] == api_id for a in list_resp.json())

        # 7) Delete the API
        del_resp = await client.delete(
            f"/api/v1/external-apis/{api_id}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 200

        # 8) Confirm deletion
        list_resp2 = await client.get("/api/v1/external-apis", headers=auth_headers)
        assert not any(a["id"] == api_id for a in list_resp2.json())


# ---------------------------------------------------------------------------
# 5. Vector config workflow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_config_workflow(client, auth_headers):
    """List defaults -> update config -> verify -> batch update -> reset."""
    # 1) List configs (should auto-create defaults)
    list_resp = await client.get(
        "/api/v1/app-config",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    configs = list_resp.json()
    assert len(configs) > 0
    assert "x-total-count" in list_resp.headers

    # Verify default vector config keys exist
    config_keys = [c["config_key"] for c in configs]
    assert "vector_db_host" in config_keys
    assert "vector_db_port" in config_keys
    assert "embedding_model" in config_keys

    # Find the vector_db_host config
    host_config = next(c for c in configs if c["config_key"] == "vector_db_host")
    host_config_id = host_config["id"]
    assert host_config["config_value"] == "localhost"

    # 2) Update a single config value
    with patch("app.api.routers.app_config._reset_vector_service"):
        update_resp = await client.put(
            f"/api/v1/app-config/{host_config_id}",
            headers=auth_headers,
            json={
                "config_key": "vector_db_host",
                "config_value": "chromadb.internal",
            },
        )
    assert update_resp.status_code == 200
    assert update_resp.json()["config_value"] == "chromadb.internal"

    # 3) Verify the update persisted
    list_resp2 = await client.get(
        "/api/v1/app-config?category=vector_db",
        headers=auth_headers,
    )
    assert list_resp2.status_code == 200
    vector_configs = list_resp2.json()
    host_cfg = next(c for c in vector_configs if c["config_key"] == "vector_db_host")
    assert host_cfg["config_value"] == "chromadb.internal"

    # 4) Batch update multiple configs
    with patch("app.api.routers.app_config._reset_vector_service"):
        batch_resp = await client.post(
            "/api/v1/app-config/batch-update",
            headers=auth_headers,
            json=[
                {"config_key": "vector_db_host", "config_value": "new-host.example.com"},
                {"config_key": "vector_db_port", "config_value": "9000"},
            ],
        )
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    updated_keys = {item["config_key"]: item["config_value"] for item in batch_data}
    assert updated_keys["vector_db_host"] == "new-host.example.com"
    assert updated_keys["vector_db_port"] == "9000"

    # 5) Reset vector connection
    with patch("app.api.routers.app_config._reset_vector_service"):
        reset_resp = await client.post(
            "/api/v1/app-config/reset-vector-connection",
            headers=auth_headers,
        )
    assert reset_resp.status_code == 200
    assert "重置" in reset_resp.json()["message"]


# ---------------------------------------------------------------------------
# 6. Cross-feature integration: case -> research -> document
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_case_research_document_pipeline(client, auth_headers):
    """Create a case -> research a legal question -> generate a document using research."""
    # 1) Create a case
    case_resp = await client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={
            "title": "劳动争议仲裁案件",
            "case_type": "labor",
            "description": "员工因违法解除劳动合同申请仲裁，要求经济补偿金。",
        },
    )
    assert case_resp.status_code == 201
    case_id = case_resp.json()["id"]

    # 2) Create research linked to the case
    mock_research = {
        "report": "# 劳动合同解除的法律依据\n\n根据《劳动合同法》第47条，经济补偿按劳动者在本单位工作的年限计算...",
        "sources_used": ["vector_db"],
    }
    with patch(
        "app.services.research.engine.LegalResearchEngine.research",
        new_callable=AsyncMock,
        return_value=mock_research,
    ):
        research_resp = await client.post(
            "/api/v1/research",
            headers=auth_headers,
            json={"query": "违法解除劳动合同的经济补偿标准", "case_id": case_id},
        )
    assert research_resp.status_code == 200
    research_id = research_resp.json()["id"]

    # 3) Create a template for labor dispute document
    tmpl_resp = await client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=_template_payload(
            name="劳动仲裁申请书模板-集成测试",
            type="labor_arbitration",
            description="劳动仲裁申请书标准模板",
            ai_prompt="根据案件事实和研究结果生成劳动仲裁申请书",
        ),
    )
    assert tmpl_resp.status_code == 201
    template_id = tmpl_resp.json()["id"]

    # 4) Generate a document using the research report
    mock_gen = {
        "content": "劳动仲裁申请书\n\n申请人：...\n被申请人：...\n\n申请事项：请求裁决被申请人支付经济补偿金...",
        "title": "劳动仲裁申请书",
        "metadata": {"research_used": True},
    }
    with patch(
        "app.services.docgen.engine.DocumentGenerationEngine.generate",
        new_callable=AsyncMock,
        return_value=mock_gen,
    ):
        doc_resp = await client.post(
            "/api/v1/documents/generate",
            headers=auth_headers,
            json={
                "case_id": case_id,
                "template_id": template_id,
                "type": "labor_arbitration",
                "title": "劳动仲裁申请书",
                "case_facts": "员工因违法解除劳动合同申请仲裁",
                "research_report_ids": [research_id],
            },
        )
    assert doc_resp.status_code == 201
    doc_id = doc_resp.json()["id"]

    # 5) Verify the case has documents
    case_detail_resp = await client.get(
        f"/api/v1/cases/{case_id}",
        headers=auth_headers,
    )
    assert case_detail_resp.status_code == 200
    assert case_detail_resp.json()["document_count"] >= 1

    # 6) Verify research appears in list
    research_list = await client.get("/api/v1/research", headers=auth_headers)
    assert research_list.status_code == 200
    assert any(r["id"] == research_id for r in research_list.json())

    # 7) Verify document appears in list filtered by case
    doc_list = await client.get(
        f"/api/v1/documents?case_id={case_id}",
        headers=auth_headers,
    )
    assert doc_list.status_code == 200
    assert any(d["id"] == doc_id for d in doc_list.json())
