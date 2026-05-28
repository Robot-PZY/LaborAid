"""LLM配置管理路由"""

import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.services.system_user import get_system_user
from app.models.user import User
from app.services.llm_client import create_llm_client
from app.schemas.llm_settings import (
    LLMSettingsCreate,
    LLMSettingsUpdate,
    LLMSettingsOut,
    ConnectivityTestRequest,
    ConnectivityTestResult,
    ActiveLLMOut,
)
from app.services.llm_resolver import resolve_user_llm, resolve_vision_llm

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_CONFIG_NAME = "劳权智助 默认"

# ── 预设大模型模板 ──────────────────────────────────────────────────
LLM_PRESETS = [
    {"key": "deepseek", "name": "DeepSeek V4 Pro", "category": "国内", "base_url": "https://api.deepseek.com", "model_name": "deepseek-v4-pro", "max_tokens": 8192, "locked": False},
    {"key": "deepseek_flash", "name": "DeepSeek V4 Flash", "category": "国内", "base_url": "https://api.deepseek.com", "model_name": "deepseek-v4-flash", "max_tokens": 8192, "locked": False},
    {"key": "deepseek_legacy", "name": "DeepSeek Chat（旧版，2026/07 弃用）", "category": "国内", "base_url": "https://api.deepseek.com", "model_name": "deepseek-chat", "max_tokens": 8192, "locked": False},
    {"key": "qwen", "name": "阿里 通义千问", "category": "国内", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model_name": "qwen-max", "max_tokens": 8192, "locked": False},
    {"key": "qwen_vl_ocr", "name": "通义千问 OCR（文字识别）", "category": "国内", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model_name": "qwen-vl-ocr-latest", "max_tokens": 4096, "locked": False},
    {"key": "qwen_vl", "name": "通义千问 VL（图像理解）", "category": "国内", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model_name": "qwen-vl-max", "max_tokens": 8192, "locked": False},
    {"key": "zhipu_free", "name": "智谱 GLM Flash", "category": "国内", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model_name": "glm-4-flash", "max_tokens": 4096, "locked": False},
    {"key": "zhipu_v", "name": "智谱 GLM-4V（OCR）", "category": "国内", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model_name": "glm-4v-plus", "max_tokens": 4096, "locked": False},
    {"key": "moonshot", "name": "月之暗面 Kimi", "category": "国内", "base_url": "https://api.moonshot.cn/v1", "model_name": "moonshot-v1-128k", "max_tokens": 8192, "locked": False},
    {"key": "ernie", "name": "百度 文心一言", "category": "国内", "base_url": "https://qianfan.baidubce.com/v2", "model_name": "ernie-4.0-8k", "max_tokens": 4096, "locked": False},
    {"key": "openai", "name": "OpenAI GPT-4o", "category": "国际", "base_url": "https://api.openai.com/v1", "model_name": "gpt-4o", "max_tokens": 4096, "locked": False},
    {"key": "claude", "name": "Anthropic Claude", "category": "国际", "base_url": "https://api.anthropic.com", "model_name": "claude-sonnet-4-20250514", "max_tokens": 4096, "locked": False},
    {"key": "gemini", "name": "Google Gemini", "category": "国际", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model_name": "gemini-2.5-pro", "max_tokens": 8192, "locked": False},
]


def _mask_api_key(key: str) -> str:
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def _row_to_out(row) -> dict:
    from app.services.llm_profiles import profile_role

    out = LLMSettingsOut(
        id=row.id,
        name=row.name,
        base_url=row.base_url,
        api_key_masked=_mask_api_key(row.api_key),
        model_name=row.model_name,
        max_tokens=row.max_tokens,
        is_default=row.is_default,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
    payload = out.model_dump(mode="json")
    payload["profile_role"] = profile_role(row.name, row.model_name, is_default=row.is_default)
    return payload


@router.get("", response_model=list[LLMSettingsOut])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    from app.models.llm_settings import LLMSettings as Model
    system = await get_system_user(db)
    await ensure_system_llm_defaults(db)
    result = await db.execute(
        select(Model).where(Model.owner_id == system.id).order_by(Model.is_default.desc(), Model.created_at)
    )
    items = [_row_to_out(r) for r in result.scalars().all()]
    return JSONResponse(content=items, headers={"X-Total-Count": str(len(items))})


@router.post("", response_model=LLMSettingsOut, status_code=201)
async def create_settings(
    data: LLMSettingsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    from app.models.llm_settings import LLMSettings as Model
    system = await get_system_user(db)
    if data.is_default:
        await db.execute(
            update(Model).where(Model.owner_id == system.id, Model.is_default == True).values(is_default=False)
        )
    row = Model(
        owner_id=system.id,
        name=data.name,
        base_url=data.base_url,
        api_key=data.api_key,
        model_name=data.model_name,
        max_tokens=data.max_tokens,
        is_default=data.is_default,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)


@router.put("/{setting_id}", response_model=LLMSettingsOut)
async def update_settings(
    setting_id: int,
    data: LLMSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    from app.models.llm_settings import LLMSettings as Model
    system = await get_system_user(db)
    result = await db.execute(
        select(Model).where(Model.id == setting_id, Model.owner_id == system.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "配置不存在")
    if data.is_default:
        await db.execute(
            update(Model).where(Model.owner_id == system.id, Model.is_default == True).values(is_default=False)
        )
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)


@router.delete("/{setting_id}")
async def delete_settings(
    setting_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    from app.models.llm_settings import LLMSettings as Model
    system = await get_system_user(db)
    result = await db.execute(
        select(Model).where(Model.id == setting_id, Model.owner_id == system.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "配置不存在")
    await db.delete(row)
    await db.commit()
    return {"message": "已删除"}


@router.post("/test-connectivity", response_model=ConnectivityTestResult)
async def test_connectivity(
    data: ConnectivityTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    api_key = data.api_key
    base_url = data.base_url

    if not api_key and data.setting_id:
        from app.models.llm_settings import LLMSettings as Model
        system = await get_system_user(db)
        result = await db.execute(
            select(Model).where(Model.id == data.setting_id, Model.owner_id == system.id)
        )
        stored = result.scalar_one_or_none()
        if stored:
            api_key = stored.api_key
            if not base_url:
                base_url = stored.base_url

    if not api_key:
        return ConnectivityTestResult(
            success=False,
            message="缺少 API Key，请输入或选择已保存的配置",
            model=data.model_name,
        )

    try:
        client = create_llm_client(base_url, api_key)
        start = time.time()
        response = await client.messages.create(
            model=data.model_name,
            max_tokens=32,
            messages=[{"role": "user", "content": "你好，请回复'连接成功'"}],
        )
        latency = int((time.time() - start) * 1000)
        text = response.content[0].text if response.content else ""
        return ConnectivityTestResult(
            success=True,
            message=f"连接成功，模型回复: {text[:50]}",
            model=data.model_name,
            latency_ms=latency,
        )
    except Exception as e:
        logger.warning("LLM connectivity test failed: %s", e)
        msg = "连接失败"
        if "timeout" in str(e).lower():
            msg = "连接超时，请检查网络或API地址"
        elif "401" in str(e) or "auth" in str(e).lower():
            msg = "API Key 无效，请检查密钥是否正确"
        elif "connection" in str(e).lower():
            msg = "无法连接到服务器，请检查API地址"
        return ConnectivityTestResult(
            success=False,
            message=msg,
            model=data.model_name,
        )


@router.get("/presets")
async def get_presets():
    """获取预设大模型模板列表。"""
    return LLM_PRESETS


@router.get("/active", response_model=ActiveLLMOut)
async def get_active_llm(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the LLM config that agent calls will use for this user."""
    llm = await resolve_user_llm(db, current_user)
    return ActiveLLMOut(
        config_id=llm.config_id,
        config_name=llm.config_name,
        model_name=llm.model,
        max_tokens=llm.max_tokens,
        base_url=llm.base_url,
        source=llm.source,
        has_api_key=bool(llm.api_key),
    )


@router.get("/runtime-summary")
async def get_llm_runtime_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前实际生效的文本主模型与视觉 OCR 模型（供管理端展示）。"""
    require_admin(current_user)
    text_llm = await resolve_user_llm(db, current_user)
    vision_llm = await resolve_vision_llm(db, current_user)
    from app.services.llm_profiles import is_vision_profile

    vision_ok = bool(vision_llm.api_key) and (
        vision_llm.client is not None
        and is_vision_profile(vision_llm.config_name, vision_llm.model)
    )
    return {
        "text": ActiveLLMOut(
            config_id=text_llm.config_id,
            config_name=text_llm.config_name,
            model_name=text_llm.model,
            max_tokens=text_llm.max_tokens,
            base_url=text_llm.base_url,
            source=text_llm.source,
            has_api_key=bool(text_llm.api_key),
        ),
        "vision": ActiveLLMOut(
            config_id=vision_llm.config_id,
            config_name=vision_llm.config_name,
            model_name=vision_llm.model or "—",
            max_tokens=vision_llm.max_tokens,
            base_url=vision_llm.base_url,
            source=vision_llm.source,
            has_api_key=bool(vision_llm.api_key),
        ),
        "vision_ready": vision_ok,
    }


# 1×1 PNG (red pixel) for OCR connectivity smoke test
_VISION_TEST_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@router.post("/test-vision-connectivity", response_model=ConnectivityTestResult)
async def test_vision_connectivity(
    data: ConnectivityTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """使用测试图片验证视觉/OCR 模型（非纯文本探活）。"""
    require_admin(current_user)
    import base64

    from app.services.evidence.pdf_vision import ocr_image_bytes

    api_key = data.api_key
    base_url = data.base_url
    if not api_key and data.setting_id:
        from app.models.llm_settings import LLMSettings as Model

        system = await get_system_user(db)
        result = await db.execute(
            select(Model).where(Model.id == data.setting_id, Model.owner_id == system.id)
        )
        stored = result.scalar_one_or_none()
        if stored:
            api_key = stored.api_key
            base_url = base_url or stored.base_url

    if not api_key:
        return ConnectivityTestResult(
            success=False,
            message="缺少 API Key",
            model=data.model_name,
        )

    try:
        client = create_llm_client(base_url, api_key)
        start = time.time()
        img = base64.b64decode(_VISION_TEST_PNG_B64)
        text = await ocr_image_bytes(
            img,
            client,
            data.model_name,
            media_type="image/png",
            prompt="请识别图片中的文字，若无文字请回复「无文字」。",
        )
        latency = int((time.time() - start) * 1000)
        if text.startswith("[") and ("失败" in text or "不可用" in text):
            return ConnectivityTestResult(
                success=False,
                message=text.strip("[]"),
                model=data.model_name,
                latency_ms=latency,
            )
        return ConnectivityTestResult(
            success=True,
            message=f"视觉/OCR 探活成功（模型响应: {text[:80]}）",
            model=data.model_name,
            latency_ms=latency,
        )
    except Exception as e:
        logger.warning("Vision connectivity test failed: %s", e)
        return ConnectivityTestResult(
            success=False,
            message=f"视觉模型测试失败: {str(e)[:200]}",
            model=data.model_name,
        )


@router.get("/active-vision", response_model=ActiveLLMOut)
async def get_active_vision_llm(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the vision/OCR LLM config used for image evidence extraction."""
    llm = await resolve_vision_llm(db, current_user)
    from app.services.llm_profiles import is_vision_profile

    return ActiveLLMOut(
        config_id=llm.config_id,
        config_name=llm.config_name,
        model_name=llm.model or "未配置",
        max_tokens=llm.max_tokens,
        base_url=llm.base_url,
        source=llm.source,
        has_api_key=bool(llm.api_key) and is_vision_profile(llm.config_name, llm.model),
    )


def _is_vision_config(name: str, model_name: str) -> bool:
    from app.services.llm_profiles import is_vision_profile

    return is_vision_profile(name, model_name)


VISION_CONFIG_NAME = "通义千问 OCR（文字识别）"


async def ensure_system_llm_defaults(db: AsyncSession):
    """Seed global LLM profiles from .env for the system user (admin-managed)."""
    from app.models.llm_settings import LLMSettings as Model
    from app.config import get_settings

    system = await get_system_user(db)
    settings = get_settings()

    result = await db.execute(select(Model).where(Model.owner_id == system.id))
    rows = result.scalars().all()
    has_default = any(r.is_default for r in rows)
    has_vision = any(_is_vision_config(r.name, r.model_name) for r in rows)

    added = False
    if not has_default and settings.LLM_API_KEY:
        db.add(
            Model(
                owner_id=system.id,
                name=DEFAULT_CONFIG_NAME,
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
                model_name=settings.LLM_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                is_default=True,
            )
        )
        added = True

    if not has_vision and settings.VISION_LLM_API_KEY:
        db.add(
            Model(
                owner_id=system.id,
                name=VISION_CONFIG_NAME,
                base_url=settings.VISION_LLM_BASE_URL,
                api_key=settings.VISION_LLM_API_KEY,
                model_name=settings.VISION_LLM_MODEL,
                max_tokens=settings.VISION_LLM_MAX_TOKENS,
                is_default=False,
            )
        )
        added = True

    if added:
        await db.commit()


# Backward compatibility for any legacy imports
async def ensure_default_config(db: AsyncSession, user: User):  # noqa: ARG001
    await ensure_system_llm_defaults(db)


async def ensure_vision_config(db: AsyncSession, user: User):  # noqa: ARG001
    await ensure_system_llm_defaults(db)
