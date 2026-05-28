"""Knowledge base management routes.

Supports CRUD, file upload, duplicate detection, batch delete, and
full-text search.
"""

import asyncio
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin, validate_upload, sanitize_filename
from app.core.cache import knowledge_stats_cache, invalidate_on_create, invalidate_on_update, invalidate_on_delete
from app.config import get_settings
from app.models.user import User
from app.models.knowledge import KnowledgeItem
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate, KnowledgeOut
from app.schemas.knowledge_crawl import (
    CrawlRunRequest,
    CrawlRunResponse,
    CrawlSeedsResponse,
    CrawlLawResultOut,
    CrawlSeedOut,
    CrawlSourceOut,
    CrawlScheduleStatus,
    CrawlScheduleUpdate,
)
from app.services.knowledge.crawler import LawCrawlService
from app.services.knowledge.crawler.scheduler import (
    get_schedule_status,
    set_schedule_enabled,
    run_scheduled_crawl,
)
from app.services.evidence.ocr import extract_text
from app.services.llm_resolver import resolve_vision_llm

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _platform_filter():
    """Platform knowledge visible to all authenticated users (read-only for non-admins)."""
    return KnowledgeItem.is_platform.is_(True)


def _assert_can_read(row: KnowledgeItem, current_user: User) -> None:
    if row.is_platform:
        return
    if row.owner_id == current_user.id:
        return
    if current_user.team_id and row.team_id == current_user.team_id:
        return
    raise HTTPException(403, "无权访问")


def _platform_write_filter():
    return KnowledgeItem.is_platform.is_(True)


# ── List ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[KnowledgeOut])
async def list_knowledge(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        base_where = _platform_filter()
        # Count query
        count_q = select(func.count(KnowledgeItem.id)).where(base_where)
        if tag:
            count_q = count_q.where(KnowledgeItem.tags.contains([tag]))
        total = (await db.execute(count_q)).scalar() or 0

        query = select(KnowledgeItem).where(base_where)
        if tag:
            query = query.where(KnowledgeItem.tags.contains([tag]))
        query = query.order_by(KnowledgeItem.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()

        # Truncate content in list view
        response_data = []
        for item in items:
            out = KnowledgeOut.model_validate(item)
            if out.content and len(out.content) > 300:
                out.content = out.content[:300] + "..."
            response_data.append(out.model_dump(mode="json"))

        return JSONResponse(
            content=response_data,
            headers={"X-Total-Count": str(total)},
        )
    except Exception as e:
        logger.error("List knowledge failed: %s", e)
        raise HTTPException(500, "查询知识库列表失败")


# ── Create (with duplicate detection) ────────────────────────────────────────

@router.post("", response_model=KnowledgeOut, status_code=201)
async def create_knowledge(
    data: KnowledgeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    if not data.title or not data.title.strip():
        raise HTTPException(400, "标题不能为空")
    if not data.content or not data.content.strip():
        raise HTTPException(400, "内容不能为空")

    try:
        # --- Duplicate detection ---
        # Check for an existing item with the same title AND owner
        existing = await db.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.title == data.title.strip(),
                _platform_write_filter(),
            )
        )
        dup = existing.scalar_one_or_none()
        if dup:
            # Update the existing item instead of creating a duplicate
            dup.content = data.content.strip()
            dup.source = data.source or dup.source
            if data.tags is not None:
                dup.tags = data.tags
            await db.commit()
            await db.refresh(dup)
            logger.info(
                "Updated duplicate knowledge item id=%d title=%r",
                dup.id, dup.title,
            )
            return dup

        row = KnowledgeItem(
            title=data.title.strip(),
            content=data.content.strip(),
            source=data.source,
            tags=data.tags,
            is_platform=True,
            owner_id=current_user.id,
            team_id=None,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

        # Auto-ingest into vector store (best-effort, ignore failures)
        try:
            await _ingest_knowledge_vector(db, row)
        except Exception as e:
            logger.warning("Auto vector ingest failed for knowledge %d: %s", row.id, e)

        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Create knowledge failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "创建知识条目失败")
    finally:
        invalidate_on_create("knowledge", "platform")

@router.get("/stats")
async def knowledge_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Check cache first (60s TTL)
        cache_key = "knowledge_stats:platform"
        cached = knowledge_stats_cache.get(cache_key)
        if cached is not None:
            return cached

        base_where = _platform_filter()
        total = await db.execute(
            select(func.count(KnowledgeItem.id)).where(base_where)
        )
        result = await db.execute(
            select(KnowledgeItem.tags).where(base_where)
        )
        all_tags: set[str] = set()
        for row in result.scalars().all():
            if row:
                all_tags.update(row)
        stats = {"total": total.scalar() or 0, "tags": sorted(all_tags)}
        knowledge_stats_cache.set(cache_key, stats)
        return stats
    except Exception as e:
        logger.error("Knowledge stats failed: %s", e)
        raise HTTPException(500, "查询知识库统计失败")


# ── Full-text search ────────────────────────────────────────────────────────

@router.get("/search/results", response_model=list[KnowledgeOut])
async def search_knowledge(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full-text search across knowledge item title and content."""
    try:
        pattern = f"%{q}%"
        base_where = _platform_filter()
        # Count query
        count_q = select(func.count(KnowledgeItem.id)).where(
            base_where,
            or_(
                KnowledgeItem.title.ilike(pattern),
                KnowledgeItem.content.ilike(pattern),
            ),
        )
        total = (await db.execute(count_q)).scalar() or 0

        query = (
            select(KnowledgeItem)
            .where(
                base_where,
                or_(
                    KnowledgeItem.title.ilike(pattern),
                    KnowledgeItem.content.ilike(pattern),
                ),
            )
            .order_by(KnowledgeItem.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        items = result.scalars().all()

        # Truncate content in search results
        response_data = []
        for item in items:
            out = KnowledgeOut.model_validate(item)
            if out.content and len(out.content) > 300:
                out.content = out.content[:300] + "..."
            response_data.append(out.model_dump(mode="json"))

        return JSONResponse(
            content=response_data,
            headers={"X-Total-Count": str(total)},
        )
    except Exception as e:
        logger.error("Search knowledge failed: %s", e)
        raise HTTPException(500, "搜索知识库失败")


# ── Official law crawl (admin) ───────────────────────────────────────────────

@router.get("/crawl/seeds", response_model=CrawlSeedsResponse)
async def list_crawl_seeds(
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    raw = LawCrawlService.seeds_as_dict()
    return CrawlSeedsResponse(
        description=raw.get("description"),
        sources=[CrawlSourceOut(**s) for s in raw.get("sources", [])],
        seeds=[CrawlSeedOut(**s) for s in raw.get("seeds", [])],
    )


@router.get("/crawl/status", response_model=CrawlScheduleStatus)
async def crawl_schedule_status(
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return CrawlScheduleStatus(**get_schedule_status())


@router.put("/crawl/schedule", response_model=CrawlScheduleStatus)
async def update_crawl_schedule(
    body: CrawlScheduleUpdate,
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return CrawlScheduleStatus(**set_schedule_enabled(body.enabled))


@router.post("/crawl/run-scheduled", response_model=CrawlScheduleStatus)
async def trigger_scheduled_crawl(
    current_user: User = Depends(get_current_user),
):
    """立即执行一次完整定时同步（核心种子 + 专题发现）。"""
    require_admin(current_user)
    status = await run_scheduled_crawl(trigger="manual")
    return CrawlScheduleStatus(**status)


@router.post("/crawl/run", response_model=CrawlRunResponse)
async def run_law_crawl(
    body: CrawlRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从官方法规数据源抓取并写入平台知识库。"""
    require_admin(current_user)
    try:
        svc = LawCrawlService()
        result = await svc.run(
            db,
            current_user,
            seed_ids=body.seed_ids,
            keywords=body.keywords,
            source_ids=body.source_ids,
            include_statutes=body.include_statutes,
            include_topic_discovery=body.include_topic_discovery,
            dry_run=body.dry_run,
        )
        return CrawlRunResponse(
            total=len(result.items),
            success=result.success,
            failed=result.failed,
            skipped=result.skipped,
            items=[
                CrawlLawResultOut(
                    seed_id=i.seed_id,
                    keyword=i.keyword,
                    title=i.title,
                    source_id=i.source_id,
                    bbbs=i.bbbs,
                    status=i.status,
                    knowledge_items=i.knowledge_items,
                    statute_vectors=i.statute_vectors,
                    message=i.message,
                )
                for i in result.items
            ],
        )
    except Exception as e:
        logger.error("Law crawl failed: %s", e)
        raise HTTPException(500, f"官方法规同步失败: {e}")


# ── Upload helpers ───────────────────────────────────────────────────────────

@router.post("/upload-text")
async def upload_text_to_knowledge(
    data: KnowledgeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload plain text content as knowledge item."""
    return await create_knowledge(data, db, current_user)


@router.post("/upload-file", response_model=KnowledgeOut)
async def upload_file_to_knowledge(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a file to the knowledge base with auto text extraction."""
    require_admin(current_user)
    try:
        content = await validate_upload(file)

        settings = get_settings()
        tmp_dir = settings.upload_path / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename or ".bin").suffix
        tmp_path = tmp_dir / f"{uuid.uuid4().hex[:12]}{ext}"

        try:
            await asyncio.to_thread(tmp_path.write_bytes, content)
            vision = await resolve_vision_llm(db, current_user)
            text = await extract_text(tmp_path, vision_llm=vision)
        finally:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)

        if not text or text.startswith("["):
            raise HTTPException(400, f"文件文字提取失败: {text}")

        chunks = _split_text(text, max_chars=2000)
        items: list[KnowledgeItem] = []
        safe_filename = sanitize_filename(file.filename or "upload")
        for i, chunk in enumerate(chunks):
            title = Path(safe_filename).stem
            if len(chunks) > 1:
                title = f"{title} (第{i+1}部分)"
            row = KnowledgeItem(
                title=title,
                content=chunk,
                source=safe_filename,
                tags=["文件上传"],
                is_platform=True,
                owner_id=current_user.id,
                team_id=None,
            )
            db.add(row)
            await db.flush()
            await db.refresh(row)
            items.append(row)

            # Auto vectorize (best-effort)
            try:
                await _ingest_knowledge_vector(db, row)
            except Exception as e:
                logger.warning("Auto vector ingest failed for uploaded knowledge %d: %s", row.id, e)

        await db.commit()
        await db.refresh(items[0])
        return items[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload file to knowledge failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "上传知识库文件失败")


def _split_text(text: str, max_chars: int = 2000) -> list[str]:
    """Split long text into chunks by paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = p
        else:
            current = current + "\n\n" + p if current else p
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]


# ── Get single item ──────────────────────────────────────────────────────────

@router.get("/{item_id}", response_model=KnowledgeOut)
async def get_knowledge(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "知识条目不存在")
        _assert_can_read(row, current_user)
        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get knowledge failed: %s", e)
        raise HTTPException(500, "查询知识条目失败")


# ── Update ───────────────────────────────────────────────────────────────────

@router.put("/{item_id}", response_model=KnowledgeOut)
async def update_knowledge(
    item_id: int,
    data: KnowledgeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    try:
        result = await db.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.id == item_id,
                _platform_write_filter(),
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "知识条目不存在或无权编辑")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await db.commit()
        await db.refresh(row)
        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update knowledge failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "更新知识条目失败")
    finally:
        invalidate_on_update("knowledge", item_id)

@router.delete("/{item_id}")
async def delete_knowledge(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    try:
        result = await db.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.id == item_id,
                _platform_write_filter(),
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "知识条目不存在或无权删除")

        # Clean up vector store
        if row.embedding_id:
            try:
                from app.services.vector.store import get_vector_service
                svc = get_vector_service()
                await svc.delete_knowledge([row.embedding_id])
            except Exception as e:
                logger.warning("Vector delete failed for knowledge %d: %s", item_id, e)

        await db.delete(row)
        await db.commit()
        return {"message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete knowledge failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "删除知识条目失败")
    finally:
        invalidate_on_delete("knowledge", item_id)

@router.post("/batch-delete")
async def batch_delete_knowledge(
    ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete multiple knowledge items by their IDs."""
    require_admin(current_user)
    if not ids:
        raise HTTPException(400, "IDs列表不能为空")
    if len(ids) > 100:
        raise HTTPException(400, "单次最多删除100条")

    try:
        result = await db.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.id.in_(ids),
                _platform_write_filter(),
            )
        )
        rows = result.scalars().all()
        if not rows:
            raise HTTPException(404, "未找到可删除的知识条目")

        # Collect embedding IDs for vector cleanup
        embedding_ids = [r.embedding_id for r in rows if r.embedding_id]
        if embedding_ids:
            try:
                from app.services.vector.store import get_vector_service
                svc = get_vector_service()
                await svc.delete_knowledge(embedding_ids)
            except Exception as e:
                logger.warning("Batch vector delete failed: %s", e)

        for row in rows:
            await db.delete(row)
        await db.commit()

        return {
            "message": f"已删除{len(rows)}条知识条目",
            "deleted_count": len(rows),
            "not_found_count": len(ids) - len(rows),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch delete knowledge failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "批量删除知识条目失败")


# ── Vector ingest helper ────────────────────────────────────────────────────

@router.post("/seed-bundle")
async def seed_knowledge_bundle(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导入平台预置知识条目（维权指引、实务要点等）。"""
    require_admin(current_user)
    try:
        from app.services.seed_platform_knowledge import seed_platform_knowledge_async

        return await seed_platform_knowledge_async(db)
    except Exception as e:
        logger.error("Seed knowledge bundle failed: %s", e)
        raise HTTPException(500, "导入预置知识失败")


async def _ingest_knowledge_vector(db: AsyncSession, row: KnowledgeItem) -> None:
    """Best-effort vector ingestion for a single knowledge item."""
    try:
        from app.services.vector.store import get_vector_service
        svc = get_vector_service()
        emb_id = f"knowledge_{row.id}"
        count = await svc.add_knowledge([{
            "id": emb_id,
            "title": row.title,
            "content": row.content[:5000],
            "metadata": {"source": row.source or "", "type": "knowledge", "tags": ",".join(row.tags or [])},
        }])
        if count:
            row.embedding_id = emb_id
            await db.commit()
            await db.refresh(row)
    except Exception as e:
        logger.warning("Auto vector ingest failed for knowledge %d: %s", row.id, e)
