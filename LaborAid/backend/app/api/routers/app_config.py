"""应用配置路由 — 向量数据库路径、系统参数等"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.services.system_user import get_system_user
from app.models.user import User
from app.models.app_config import AppConfig
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()


class ConfigItemCreate(BaseModel):
    config_key: str
    config_value: str = ""
    description: str = ""
    category: str = "general"


class ConfigItemUpdate(BaseModel):
    config_key: str
    config_value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class ConfigItemOut(BaseModel):
    id: int
    config_key: str
    config_value: str
    description: str
    category: str
    created_at: datetime
    updated_at: datetime


# 向量数据库默认配置
VECTOR_DB_DEFAULTS = [
    {"config_key": "vector_db_host", "config_value": "localhost", "description": "ChromaDB 主机地址", "category": "vector_db"},
    {"config_key": "vector_db_port", "config_value": "8001", "description": "ChromaDB 端口", "category": "vector_db"},
    {"config_key": "vector_db_cases_path", "config_value": "", "description": "本地案例向量库路径（留空使用默认）", "category": "vector_db"},
    {"config_key": "vector_db_statutes_path", "config_value": "", "description": "本地法条向量库路径（留空使用默认）", "category": "vector_db"},
    {"config_key": "vector_db_knowledge_path", "config_value": "", "description": "个人知识库向量路径（留空使用默认）", "category": "vector_db"},
    {"config_key": "embedding_model", "config_value": "all-MiniLM-L6-v2", "description": "向量嵌入模型", "category": "vector_db"},
    {"config_key": "embedding_base_url", "config_value": "", "description": "嵌入模型API地址（留空使用本地）", "category": "vector_db"},
    {"config_key": "max_upload_size_mb", "config_value": "50", "description": "最大上传文件大小(MB)", "category": "general"},
    {"config_key": "default_llm_temperature", "config_value": "0.7", "description": "LLM默认温度参数", "category": "general"},
]


@router.get("", response_model=list[ConfigItemOut])
async def list_configs(
    category: str = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    limit = min(max(limit, 1), 100)
    system = await get_system_user(db)
    await _ensure_defaults(db, system)
    base = AppConfig.owner_id == system.id
    count_q = select(func.count(AppConfig.id)).where(base)
    if category:
        count_q = count_q.where(AppConfig.category == category)
    total = (await db.execute(count_q)).scalar() or 0

    query = select(AppConfig).where(base)
    if category:
        query = query.where(AppConfig.category == category)
    query = query.order_by(AppConfig.category, AppConfig.config_key).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()
    items = [
        {
            "id": r.id,
            "config_key": r.config_key,
            "config_value": r.config_value,
            "description": r.description,
            "category": r.category,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
    return JSONResponse(content=items, headers={"X-Total-Count": str(total)})


@router.put("/{config_id}", response_model=ConfigItemOut)
async def update_config(
    config_id: int,
    data: ConfigItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    system = await get_system_user(db)
    result = await db.execute(
        select(AppConfig).where(
            AppConfig.id == config_id,
            AppConfig.owner_id == system.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "配置不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)

    # 如果修改了向量DB配置，触发重新连接
    if row.category == "vector_db" and row.config_key.startswith("vector_db_"):
        _reset_vector_service()

    return row


@router.post("/batch-update", response_model=list[ConfigItemOut])
async def batch_update(
    items: list[ConfigItemUpdate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    system = await get_system_user(db)
    await _ensure_defaults(db, system)
    results = []
    needs_vector_reset = False
    for item in items:
        if item.config_value is None:
            continue
        result = await db.execute(
            select(AppConfig).where(
                AppConfig.owner_id == system.id,
                AppConfig.config_key == item.config_key,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.config_value = item.config_value
            if item.description is not None:
                row.description = item.description
            if item.category is not None:
                row.category = item.category
            results.append(row)
            if row.category == "vector_db":
                needs_vector_reset = True
    await db.commit()
    for r in results:
        await db.refresh(r)

    if needs_vector_reset:
        _reset_vector_service()
    return results


@router.post("/reset-vector-connection")
async def reset_vector_connection(
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    try:
        _reset_vector_service()
        return {"message": "向量数据库连接已重置"}
    except Exception as e:
        logger.error("Reset vector connection failed: %s", e)
        raise HTTPException(500, "重置向量数据库连接失败，请稍后重试")


def _reset_vector_service():
    try:
        from app.services.vector.store import _vector_service
        import app.services.vector.store as vs
        if _vector_service:
            vs._vector_service = None
    except Exception as e:
        logger.warning("Failed to reset vector service: %s", e)


async def _ensure_defaults(db: AsyncSession, user: User):
    result = await db.execute(
        select(AppConfig.config_key).where(AppConfig.owner_id == user.id)
    )
    existing_keys = {row[0] for row in result.all()}
    new_items = []
    for default in VECTOR_DB_DEFAULTS:
        if default["config_key"] not in existing_keys:
            new_items.append(AppConfig(
                owner_id=user.id,
                **default,
            ))
    if new_items:
        db.add_all(new_items)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            # Concurrent request may have inserted these keys already;
            # silently swallow the duplicate-key error.
