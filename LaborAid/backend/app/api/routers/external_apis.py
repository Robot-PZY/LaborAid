"""外部API数据源配置路由 — 用户自由定义任意接口"""

import time
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.services.system_user import get_system_user
from app.core.cache import presets_cache
from app.models.user import User
from app.models.external_api import ExternalApiConfig
from app.schemas.external_api import (
    ExternalApiCreate,
    ExternalApiUpdate,
    ExternalApiOut,
    ExternalApiTestResult,
    ExternalApiPreset,
)
from app.services.data_sources.dynamic_adapter import (
    register_dynamic_adapter,
    unregister_dynamic_adapter,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# 预设外部API模板
EXTERNAL_API_PRESETS = [
    {
        "key": "beida_fabao",
        "name": "北大法宝",
        "category": "法律数据库",
        "description": "中国法律法规检索权威平台",
        "base_url": "https://www.pkulaw.com/api",
        "auth_type": "api_key",
        "search_law_path": "/search/law",
        "search_law_method": "GET",
        "search_case_path": "/search/case",
        "search_case_method": "GET",
        "get_provision_path": "/provision/{doc_id}",
        "get_provision_method": "GET",
        "health_check_path": "/health",
        "response_mapping": json.dumps({
            "law": {"id": "id", "title": "title", "content": "full_text", "provision_ref": "provision_ref"},
            "case": {"id": "id", "title": "name", "content": "summary", "case_number": "case_no", "court": "court_name", "date": "judgment_date"},
        }),
        "request_template": "{}",
    },
    {
        "key": "yuandian",
        "name": "元典",
        "category": "法律数据库",
        "description": "法律智能检索与分析平台",
        "base_url": "https://api.yuandian.com",
        "auth_type": "bearer",
        "search_law_path": "/v1/search/law",
        "search_law_method": "POST",
        "search_case_path": "/v1/search/case",
        "search_case_method": "POST",
        "get_provision_path": "/v1/provision/{doc_id}",
        "get_provision_method": "GET",
        "health_check_path": "/v1/health",
        "response_mapping": json.dumps({
            "law": {"id": "id", "title": "title", "content": "content", "provision_ref": "article"},
            "case": {"id": "id", "title": "title", "content": "summary", "case_number": "caseNo", "court": "court", "date": "judgmentDate"},
        }),
        "request_template": "{}",
    },
    {
        "key": "zhihe",
        "name": "智合",
        "category": "法律数据库",
        "description": "法律科技数据平台",
        "base_url": "https://api.zhihe.com",
        "auth_type": "bearer",
        "search_law_path": "/api/v1/laws/search",
        "search_law_method": "GET",
        "search_case_path": "/api/v1/cases/search",
        "search_case_method": "GET",
        "get_provision_path": "/api/v1/laws/{doc_id}",
        "get_provision_method": "GET",
        "health_check_path": "/api/v1/ping",
        "response_mapping": json.dumps({
            "law": {"id": "id", "title": "title", "content": "text", "provision_ref": "article_number"},
            "case": {"id": "id", "title": "title", "content": "abstract", "case_number": "case_number", "court": "court_name", "date": "date"},
        }),
        "request_template": "{}",
    },
    {
        "key": "tavily",
        "name": "Tavily 网络搜索",
        "category": "搜索引擎",
        "description": "AI驱动的网络搜索API",
        "base_url": "https://api.tavily.com",
        "auth_type": "bearer",
        "search_law_path": "/search",
        "search_law_method": "POST",
        "search_case_path": "/search",
        "search_case_method": "POST",
        "get_provision_path": "",
        "get_provision_method": "GET",
        "health_check_path": "",
        "response_mapping": json.dumps({
            "law": {"id": "url", "title": "title", "content": "content"},
            "case": {"id": "url", "title": "title", "content": "content"},
        }),
        "request_template": json.dumps({"search_depth": "basic", "include_answer": True, "max_results": 5}),
    },
    {
        "key": "exa",
        "name": "Exa 智能搜索",
        "category": "搜索引擎",
        "description": "语义化网络搜索引擎",
        "base_url": "https://api.exa.ai",
        "auth_type": "bearer",
        "search_law_path": "/search",
        "search_law_method": "POST",
        "search_case_path": "/search",
        "search_case_method": "POST",
        "get_provision_path": "",
        "get_provision_method": "GET",
        "health_check_path": "",
        "response_mapping": json.dumps({
            "law": {"id": "id", "title": "title", "content": "text"},
            "case": {"id": "id", "title": "title", "content": "text"},
        }),
        "request_template": json.dumps({"type": "neural", "num_results": 5}),
    },
    {
        "key": "custom_rest",
        "name": "自定义 REST API",
        "category": "通用",
        "description": "接入任意RESTful API，完全自定义端点和参数",
        "base_url": "",
        "auth_type": "none",
        "search_law_path": "",
        "search_law_method": "GET",
        "search_case_path": "",
        "search_case_method": "GET",
        "get_provision_path": "",
        "get_provision_method": "GET",
        "health_check_path": "",
        "response_mapping": json.dumps({
            "law": {"id": "id", "title": "title", "content": "content"},
            "case": {"id": "id", "title": "title", "content": "content", "case_number": "case_no", "court": "court", "date": "date"},
        }),
        "request_template": "{}",
    },
]


def _mask_secret(val: str) -> str:
    if not val or len(val) <= 8:
        return "*" * max(len(val), 4)
    return val[:4] + "*" * (len(val) - 8) + val[-4:]


def _row_to_out(row: ExternalApiConfig) -> ExternalApiOut:
    return ExternalApiOut(
        id=row.id,
        name=row.name,
        description=row.description,
        base_url=row.base_url,
        auth_type=row.auth_type,
        auth_token_masked=_mask_secret(row.auth_token),
        auth_header_name=row.auth_header_name,
        auth_username=row.auth_username,
        auth_password_masked=_mask_secret(row.auth_password),
        custom_headers=row.custom_headers,
        search_law_path=row.search_law_path,
        search_law_method=row.search_law_method,
        search_case_path=row.search_case_path,
        search_case_method=row.search_case_method,
        get_provision_path=row.get_provision_path,
        get_provision_method=row.get_provision_method,
        health_check_path=row.health_check_path,
        response_mapping=row.response_mapping,
        request_template=row.request_template,
        is_enabled=row.is_enabled,
        category=row.category,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[ExternalApiOut])
async def list_apis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    system = await get_system_user(db)
    try:
        result = await db.execute(
            select(ExternalApiConfig)
            .where(ExternalApiConfig.owner_id == system.id)
            .order_by(ExternalApiConfig.created_at.desc())
        )
        items = [_row_to_out(r).model_dump(mode="json") for r in result.scalars().all()]
        return JSONResponse(content=items, headers={"X-Total-Count": str(len(items))})
    except Exception as e:
        logger.error("List external APIs failed: %s", e)
        raise HTTPException(500, "查询外部API列表失败")


@router.post("", response_model=ExternalApiOut, status_code=201)
async def create_api(
    data: ExternalApiCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    system = await get_system_user(db)
    # Validate JSON fields
    for json_field in ("custom_headers", "response_mapping", "request_template"):
        val = getattr(data, json_field, None)
        if val:
            try:
                json.loads(val)
            except json.JSONDecodeError:
                raise HTTPException(400, f"{json_field} 不是有效的JSON格式")
    try:
        row = ExternalApiConfig(
            owner_id=system.id,
            **data.model_dump(),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

        if row.is_enabled:
            try:
                register_dynamic_adapter(row)
            except Exception as e:
                logger.warning("Failed to register adapter: %s", e)

        return _row_to_out(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Create external API failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "创建外部API配置失败")


@router.put("/{api_id}", response_model=ExternalApiOut)
async def update_api(
    api_id: int,
    data: ExternalApiUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    system = await get_system_user(db)
    # Validate JSON fields if provided
    for json_field in ("custom_headers", "response_mapping", "request_template"):
        val = getattr(data, json_field, None)
        if val is not None:
            try:
                json.loads(val)
            except json.JSONDecodeError:
                raise HTTPException(400, f"{json_field} 不是有效的JSON格式")
    try:
        result = await db.execute(
            select(ExternalApiConfig).where(
                ExternalApiConfig.id == api_id,
                ExternalApiConfig.owner_id == system.id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "配置不存在")

        # 先取消注册旧适配器
        unregister_dynamic_adapter(row.id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await db.commit()
        await db.refresh(row)

        # 重新注册
        if row.is_enabled:
            try:
                register_dynamic_adapter(row)
            except Exception as e:
                logger.warning("Failed to re-register adapter: %s", e)

        return _row_to_out(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update external API failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "更新外部API配置失败")


@router.delete("/{api_id}")
async def delete_api(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    system = await get_system_user(db)
    try:
        result = await db.execute(
            select(ExternalApiConfig).where(
                ExternalApiConfig.id == api_id,
                ExternalApiConfig.owner_id == system.id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "配置不存在")

        unregister_dynamic_adapter(row.id)
        await db.delete(row)
        await db.commit()
        return {"message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete external API failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "删除外部API配置失败")


@router.post("/{api_id}/toggle", response_model=ExternalApiOut)
async def toggle_api(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    system = await get_system_user(db)
    result = await db.execute(
        select(ExternalApiConfig).where(
            ExternalApiConfig.id == api_id,
            ExternalApiConfig.owner_id == system.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "配置不存在")

    row.is_enabled = not row.is_enabled
    await db.commit()
    await db.refresh(row)

    if row.is_enabled:
        try:
            register_dynamic_adapter(row)
        except Exception as e:
            logger.warning("Failed to register adapter: %s", e)
    else:
        unregister_dynamic_adapter(row.id)

    return _row_to_out(row)


class ExternalApiTestRequest(BaseModel):
    api_id: int


@router.post("/test", response_model=ExternalApiTestResult)
async def test_api(
    data: ExternalApiTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    system = await get_system_user(db)
    result = await db.execute(
        select(ExternalApiConfig).where(
            ExternalApiConfig.id == data.api_id,
            ExternalApiConfig.owner_id == system.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "配置不存在")

    try:
        from app.services.data_sources.dynamic_adapter import DynamicExternalApiAdapter
        # Create a temporary adapter just for testing — don't pollute the registry
        adapter = DynamicExternalApiAdapter(row)

        start = time.time()
        ok = await adapter.health_check()
        latency = int((time.time() - start) * 1000)

        # Clean up the temporary HTTP client
        try:
            await adapter.aclose()
        except Exception:
            pass

        if ok:
            return ExternalApiTestResult(
                success=True,
                message=f"连接成功，延迟 {latency}ms",
                latency_ms=latency,
            )
        else:
            return ExternalApiTestResult(
                success=False,
                message="连接失败，请检查URL和认证配置",
                latency_ms=latency,
            )
    except Exception as e:
        logger.error("External API test failed: %s", e)
        return ExternalApiTestResult(
            success=False,
            message="测试失败，请检查URL和认证配置",
        )


@router.get("/presets", response_model=list[ExternalApiPreset])
async def get_presets():
    cached = presets_cache.get("external_api_presets")
    if cached is not None:
        return cached
    presets_cache.set("external_api_presets", EXTERNAL_API_PRESETS)
    return EXTERNAL_API_PRESETS
